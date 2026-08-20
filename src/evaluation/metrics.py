"""
Réimplémentation des 4 métriques Ragas (faithfulness, answer relevancy,
context precision, context recall), calculées via un LLM-juge (Groq).

Pourquoi pas la librairie `ragas` directement ? Elle force une vieille version
de langchain-core, incompatible avec la version de langgraph utilisée dans ce
projet (testé : ça casse l'import de langgraph). On réimplémente donc la même
méthodologie "LLM-as-judge" avec des appels directs à Groq, en réutilisant le
même client que src/models_clients/groq_client.py.

Toutes les métriques retournent un score entre 0.0 et 1.0 (convention Ragas
standard), à la différence des critères heuristiques existants qui étaient
notés sur 1-5. À documenter comme changement d'échelle dans le rapport.

Self-consistency : chaque métrique appelle le juge REPETITIONS_JUGE fois et
prend la MÉDIANE des notes obtenues, pour lisser l'instabilité naturelle d'un
LLM-juge (observée en test : deux évaluations d'un même texte peuvent varier).

Choix du modèle-juge : llama-3.1-8b-instant plutôt que llama-3.3-70b-versatile
(utilisé pour la GÉNÉRATION des réponses dans groq_client.py). Motif découvert
en test : les deux modèles partagent le même quota Groq gratuit journalier
(100 000 tokens/jour) quand ils sont identiques — utiliser un modèle différent
pour le jugement sépare les deux quotas et évite qu'une évaluation intensive
ne bloque la génération (erreur 429 rate_limit_exceeded observée en pratique).
Compromis assumé : jugement un peu moins fin qu'avec un 70B, à documenter
dans les limites connues du rapport de stage.
"""

import json
import re
import statistics
import time
from groq import Groq
from src.config.settings import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

MODELE_JUGE = "qwen/qwen3.6-27b"  # gpt-oss-20b : quota TPD epuise, gemma2-9b-it decommissionne - qwen3.6-27b a un quota separe
REPETITIONS_JUGE = 1  # temporairement réduit de 2 à 1 pour limiter le volume d'appels pendant le rattrapage
def _appeler_juge_une_fois(prompt_systeme: str, prompt_utilisateur: str) -> float | None:
    """Un seul appel au juge, avec retry/backoff si l'API échoue.

    Tente jusqu'à 3 appels côté Groq avec backoff exponentiel (5s,15s,45s).
    Retourne la note float ou None si toutes les tentatives échouent.
    """
    backoffs = [5, 15, 45]
    last_exc = None
    for attempt, wait in enumerate(backoffs, start=1):
        try:
            response = client.chat.completions.create(
                model=MODELE_JUGE,
                messages=[
                    {"role": "system", "content": prompt_systeme},
                    {"role": "user", "content": prompt_utilisateur},
                ],
                max_tokens=1200,
                temperature=0,
                seed=42,
            )
            contenu = response.choices[0].message.content.strip()

            # Qwen3 et autres modèles "reasoning" entourent leur raisonnement de
            # balises <think>...</think> avant la réponse finale -> on les retire.
            contenu = re.sub(r"<think>.*?</think>", "", contenu, flags=re.DOTALL).strip()

            # Le juge répond parfois avec des ```json ... ``` autour du JSON -> on nettoie
            contenu_nettoye = re.sub(r"^```(?:json)?|```$", "", contenu, flags=re.MULTILINE).strip()

            resultat = json.loads(contenu_nettoye)            
            note = float(resultat.get("note", 0.0))
            time.sleep(1.5)  # throttle pour éviter le rate limit Groq sur les gros batches
            return max(0.0, min(1.0, note))        
        except Exception as e:
            last_exc = e
            print(f"[JUGE] tentative {attempt}/{len(backoffs)} échouée : {type(e).__name__} - {e}")
            # Si ce n'est pas la dernière tentative, attendre puis retry
            if attempt < len(backoffs):                
                try:
                    time.sleep(wait)
                except Exception:
                    pass
            else:
                # toutes les tentatives ont échoué -> on retourne None
                return None


def _appeler_juge(prompt_systeme: str, prompt_utilisateur: str) -> dict:
    """
    Appelle le juge REPETITIONS_JUGE fois (self-consistency) et retourne la
    médiane des notes obtenues, avec l'écart observé entre les tentatives
    comme indicateur de fiabilité du jugement pour ce cas précis.

    Si toutes les tentatives échouent (erreur API, JSON invalide, rate limit,
    etc.), retourne note=None pour ne jamais faire planter le pipeline complet.
    """
    notes = [
        _appeler_juge_une_fois(prompt_systeme, prompt_utilisateur)
        for _ in range(REPETITIONS_JUGE)
    ]
    notes_valides = [n for n in notes if n is not None]

    if not notes_valides:
        return {
            "note": None,
            "justification": f"Échec des {REPETITIONS_JUGE} tentatives d'évaluation par le juge.",
        }

    note_finale = round(statistics.median(notes_valides), 3)
    ecart = round(max(notes_valides) - min(notes_valides), 3) if len(notes_valides) > 1 else 0.0

    return {
        "note": note_finale,
        "justification": f"Médiane de {len(notes_valides)} évaluations (écart max observé : {ecart}).",
    }


def evaluer_faithfulness(reponse: str, contexte_chunks: list[str]) -> dict:
    """
    Fidélité (faithfulness) : la réponse ne contient-elle QUE des affirmations
    soutenues par le contexte RAG fourni, sans invention (hallucination) ?
    """
    contexte = "\n\n---\n\n".join(contexte_chunks)

    prompt_systeme = (
        "Tu es un évaluateur strict de fidélité factuelle. Tu réponds UNIQUEMENT "
        "en JSON valide, sans texte autour, au format : "
        '{"note": <float entre 0 et 1>, "justification": "<une phrase courte>"}'
    )
    prompt_utilisateur = f"""Voici un contexte de référence et une réponse générée par un modèle IA.

CONTEXTE DE RÉFÉRENCE :
{contexte}

RÉPONSE GÉNÉRÉE :
{reponse}

Ta tâche : identifie les affirmations factuelles dans la RÉPONSE GÉNÉRÉE, puis évalue
quelle proportion de ces affirmations est effectivement soutenue par le CONTEXTE DE
RÉFÉRENCE (peu importe la formulation, seul le sens compte).

- note = 1.0 : toutes les affirmations sont soutenues par le contexte
- note = 0.5 : environ la moitié des affirmations sont soutenues
- note = 0.0 : aucune affirmation n'est soutenue par le contexte (hallucination totale)

Réponds uniquement avec le JSON demandé."""

    return _appeler_juge(prompt_systeme, prompt_utilisateur)


def evaluer_answer_relevancy(reponse: str, question: str) -> dict:
    """
    Pertinence de la réponse (answer relevancy) : la réponse traite-t-elle
    directement la question posée, sans hors-sujet ni remplissage inutile ?
    """
    prompt_systeme = (
        "Tu es un évaluateur strict de pertinence. Tu réponds UNIQUEMENT en JSON "
        'valide, sans texte autour, au format : '
        '{"note": <float entre 0 et 1>, "justification": "<une phrase courte>"}'
    )
    prompt_utilisateur = f"""Voici une question posée à un assistant IA et sa réponse.

QUESTION :
{question}

RÉPONSE :
{reponse}

Ta tâche : évalue si la réponse traite directement et complètement la question posée,
sans digression ni contenu hors-sujet.

- note = 1.0 : la réponse est parfaitement pertinente et complète par rapport à la question
- note = 0.5 : la réponse est partiellement pertinente (répond en partie, ou avec du hors-sujet)
- note = 0.0 : la réponse ne traite pas la question posée

Réponds uniquement avec le JSON demandé."""

    return _appeler_juge(prompt_systeme, prompt_utilisateur)


def evaluer_context_precision(contexte_chunks: list[str], question: str) -> dict:
    """
    Précision du contexte (context precision) : les chunks récupérés par le RAG
    sont-ils réellement utiles pour répondre à la question (peu de bruit) ?
    """
    contexte = "\n\n---\n\n".join(
        f"[Chunk {i+1}]\n{chunk}" for i, chunk in enumerate(contexte_chunks)
    )

    prompt_systeme = (
        "Tu es un évaluateur strict de pertinence de contexte RAG. Tu réponds "
        'UNIQUEMENT en JSON valide, sans texte autour, au format : '
        '{"note": <float entre 0 et 1>, "justification": "<une phrase courte>"}'
    )
    prompt_utilisateur = f"""Voici une question et une liste de chunks de documents récupérés
par un système RAG pour y répondre.

QUESTION :
{question}

CHUNKS RÉCUPÉRÉS :
{contexte}

Ta tâche : évalue quelle proportion des chunks récupérés est réellement pertinente
pour répondre à la question (les chunks utiles doivent être en tête idéalement, mais
ici évalue simplement la proportion globale de chunks pertinents vs non pertinents).

- note = 1.0 : tous les chunks récupérés sont pertinents pour la question
- note = 0.5 : environ la moitié des chunks sont pertinents
- note = 0.0 : aucun chunk récupéré n'est pertinent (le RAG a mal recherché)

Réponds uniquement avec le JSON demandé."""

    return _appeler_juge(prompt_systeme, prompt_utilisateur)


def evaluer_context_recall(contexte_chunks: list[str], sortie_attendue: str) -> dict:
    """
    Rappel du contexte (context recall) : le contexte récupéré contient-il toutes
    les informations nécessaires pour produire la réponse de référence attendue ?

    Nécessite un `sortie_attendue` (champ déjà présent dans la table `scenarios`).
    Si ce champ est vide, la métrique n'est pas calculable -> note=None.
    """
    if not sortie_attendue or not sortie_attendue.strip():
        return {
            "note": None,
            "justification": "Pas de sortie_attendue définie pour ce scénario — métrique non calculable.",
        }

    contexte = "\n\n---\n\n".join(contexte_chunks)

    prompt_systeme = (
        "Tu es un évaluateur strict de couverture de contexte RAG. Tu réponds "
        'UNIQUEMENT en JSON valide, sans texte autour, au format : '
        '{"note": <float entre 0 et 1>, "justification": "<une phrase courte>"}'
    )
    prompt_utilisateur = f"""Voici une réponse de référence (attendue comme correcte) et le
contexte qui a été récupéré par un système RAG pour produire une réponse.

RÉPONSE DE RÉFÉRENCE (attendue) :
{sortie_attendue}

CONTEXTE RÉCUPÉRÉ :
{contexte}

Ta tâche : décompose la RÉPONSE DE RÉFÉRENCE en affirmations factuelles, puis évalue
quelle proportion de ces affirmations peut être retrouvée (justifiée) dans le CONTEXTE
RÉCUPÉRÉ. Cela mesure si le système RAG a récupéré tout ce qu'il fallait pour bien répondre.

- note = 1.0 : toutes les affirmations de la réponse de référence sont couvertes par le contexte
- note = 0.5 : environ la moitié sont couvertes
- note = 0.0 : rien n'est couvert (le contexte récupéré manque l'essentiel)

Réponds uniquement avec le JSON demandé."""

    return _appeler_juge(prompt_systeme, prompt_utilisateur)