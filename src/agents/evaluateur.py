from src.database.connection import engine
from sqlalchemy import text
from src.evaluation.deepeval_runner import evaluer_execution_ragas


def _evaluer_reponse(reponse: str, chunks_rag: list[str], prompt: str) -> dict:
    """
    Évaluation heuristique (Sprint 3) — conservée dans le code pour comparaison
    et pour le rapport de stage, mais N'EST PLUS l'évaluation par défaut depuis
    le Sprint 4 (remplacée par evaluer_execution_ragas, voir agent_evaluateur).
    """
    scores = {}

    # 1. COMPLÉTUDE (1-5)
    nb_mots = len(reponse.split())
    if nb_mots < 30:
        scores["completude"] = 1
    elif nb_mots < 80:
        scores["completude"] = 2
    elif nb_mots < 150:
        scores["completude"] = 3
    elif nb_mots < 300:
        scores["completude"] = 4
    else:
        scores["completude"] = 5

    # 2. STRUCTURE (1-5)
    a_puces = any(c in reponse for c in ["*", "-", "•", "1.", "2.", "3."])
    a_titres = any(c in reponse for c in ["**", "##", "###"])
    a_paragraphes = reponse.count("\n") >= 3
    structure_score = 1
    if a_puces:
        structure_score += 2
    if a_titres:
        structure_score += 1
    if a_paragraphes:
        structure_score += 1
    scores["structure"] = min(structure_score, 5)

    # 3. FIDÉLITÉ AU CONTEXTE RAG (1-5)
    contexte_complet = " ".join(chunks_rag).lower()
    reponse_lower = reponse.lower()
    mots_contexte = set(contexte_complet.split())
    mots_reponse = set(reponse_lower.split())
    mots_communs = mots_contexte.intersection(mots_reponse)
    mots_significatifs = [m for m in mots_communs if len(m) > 4]
    ratio = min(len(mots_significatifs) / 20, 1.0)
    scores["fidelite_rag"] = max(1, round(ratio * 5))

    # 4. HONNÊTETÉ (1-5)
    formules_honnetes = [
        "n'est pas dans le contexte", "pas d'information",
        "je ne trouve pas", "le contexte ne",
        "not in the context", "لا توجد معلومات",
    ]
    formules_hallucination = [
        "je suppose", "probablement",
        "il est possible que", "I think", "I believe",
    ]
    honnetete = 3
    if any(f in reponse.lower() for f in formules_honnetes):
        honnetete = 5
    if any(f in reponse.lower() for f in formules_hallucination):
        honnetete = 2
    scores["honnetete"] = honnetete

    # Score global
    scores["score_global"] = round(
        (scores["completude"] + scores["structure"] +
         scores["fidelite_rag"] + scores["honnetete"]) / 4, 2
    )

    return scores


def agent_evaluateur(state: dict) -> dict:
    """
    Évalue chaque exécution avec les métriques Ragas (Sprint 4) et enregistre
    les scores en base. L'évaluation heuristique (_evaluer_reponse, Sprint 3)
    reste disponible dans ce fichier mais n'est plus utilisée par défaut.
    """
    print(f"\n[EVALUATEUR] Évaluation de {len(state['executions'])} exécutions (Ragas)...")

    scores_list = []
    erreurs = state.get("erreurs", [])

    # Index sur le scénario complet (pas juste chunks/prompt) pour accéder
    # aussi à sortie_attendue, nécessaire pour context_recall.
    index_scenarios = {s["id"]: s for s in state["scenarios"]}

    with engine.connect() as conn:
        for execution in state["executions"]:
            scenario_id = execution["scenario_id"]
            scenario = index_scenarios.get(scenario_id, {})
            chunks_rag = scenario.get("chunks_rag", [])
            prompt = scenario.get("prompt", "")
            sortie_attendue = scenario.get("sortie_attendue")

            print(f"\n  → [{execution['scenario_nom']}] | {execution['modele']}")

            resultat = evaluer_execution_ragas(
                reponse=execution["reponse"],
                question=prompt,
                contexte_chunks=chunks_rag,
                sortie_attendue=sortie_attendue,
            )

            print(f"     Faithfulness      : {resultat['faithfulness']['note']}")
            print(f"     Answer relevancy  : {resultat['answer_relevancy']['note']}")
            print(f"     Context precision : {resultat['context_precision']['note']}")
            print(f"     Context recall    : {resultat['context_recall']['note']}")
            print(f"     Score global      : {resultat['score_global']}")

            execution_id = execution["execution_id"]
            try:
                criteres_a_inserer = {
                    "faithfulness": resultat["faithfulness"],
                    "answer_relevancy": resultat["answer_relevancy"],
                    "context_precision": resultat["context_precision"],
                    "context_recall": resultat["context_recall"],
                }

                nb_inseres = 0
                for critere, detail in criteres_a_inserer.items():
                    if detail["note"] is None:
                        # Métrique non calculable (ex: pas de sortie_attendue
                        # pour context_recall, ou erreur du juge) -> on ne
                        # pollue pas la base avec une note fictive.
                        continue
                    conn.execute(
                        text("""
                            INSERT INTO scores (execution_id, critere, note, commentaire)
                            VALUES (:exec_id, :critere, :note, :commentaire)
                        """),
                        {
                            "exec_id": execution_id,
                            "critere": critere,
                            "note": float(detail["note"]),
                            "commentaire": detail["justification"][:500],  # sécurité longueur
                        }
                    )
                    nb_inseres += 1

                if resultat["score_global"] is not None:
                    conn.execute(
                        text("""
                            INSERT INTO scores (execution_id, critere, note, commentaire)
                            VALUES (:exec_id, :critere, :note, :commentaire)
                        """),
                        {
                            "exec_id": execution_id,
                            "critere": "score_global",
                            "note": float(resultat["score_global"]),
                            "commentaire": "Moyenne des 4 métriques Ragas disponibles",
                        }
                    )
                    nb_inseres += 1

                conn.commit()
                print(f"     ✓ {nb_inseres} scores enregistrés (execution_id={execution_id})")
            except Exception as e:
                erreurs.append(f"Erreur insertion score: {str(e)}")
                print(f"     ✗ Erreur: {str(e)}")

            scores_list.append({**execution, "scores": resultat})

    print(f"\n[EVALUATEUR] {len(scores_list)} évaluations terminées.")

    return {
        **state,
        "scores": scores_list,
        "erreurs": erreurs,
    }