from src.database.connection import SessionLocal
from src.database.models import Scenario

def seed_scenarios():
    db = SessionLocal()

    scenarios = [
        # === Direction RH & Communication ===
        Scenario(
            departement="RH & Communication",
            metier="Recruteur / Talent Acquisition Specialist",
            nom_cas_usage="Rédaction de fiche de poste",
            prompt="Rédige une fiche de poste pour un Développeur Backend Python, 3 ans d'expérience minimum, poste basé à Tunis, CDI, pour une entreprise de télécommunications.",
            sortie_attendue="Fiche structurée avec titre, missions (5-6 points), profil recherché, compétences techniques, avantages.",
            critere_succes="Structure complète, ton professionnel, pas d'information inventée non cohérente, 200-400 mots."
        ),
        Scenario(
            departement="RH & Communication",
            metier="Recruteur / Talent Acquisition Specialist",
            nom_cas_usage="Tri et présélection des CV",
            prompt="Voici un CV : [texte du CV]. Résume les compétences clés et l'expérience du candidat, et indique s'il correspond à un poste de Développeur Python 3 ans d'expérience.",
            sortie_attendue="Résumé structuré : compétences, expérience, correspondance au poste (oui/non/partiel avec justification).",
            critere_succes="Extraction fidèle au CV fourni, pas d'invention d'informations absentes du texte."
        ),
        Scenario(
            departement="RH & Communication",
            metier="Recruteur / Talent Acquisition Specialist",
            nom_cas_usage="Préparation grille d'évaluation entretien",
            prompt="Génère 8 questions d'entretien (4 techniques, 4 comportementales) pour un poste de Développeur Python 3 ans d'expérience, en te basant sur un écart identifié : le candidat n'a pas d'expérience en tests unitaires.",
            sortie_attendue="Liste de 8 questions classées par catégorie, avec une question ciblant spécifiquement l'écart mentionné.",
            critere_succes="Questions pertinentes et non génériques, au moins une question liée à l'écart précisé."
        ),
        Scenario(
            departement="RH & Communication",
            metier="Chargé de Communication Interne",
            nom_cas_usage="Rédaction de communiqué interne",
            prompt="Rédige un communiqué interne annonçant un changement d'horaires de travail (nouveaux horaires : 8h30-17h30), sur un ton empathique et rassurant, à destination de tous les employés.",
            sortie_attendue="Communiqué structuré avec objet, contexte du changement, nouvelles modalités, contact pour questions.",
            critere_succes="Ton empathique respecté, informations claires, longueur adaptée (150-250 mots)."
        ),
        Scenario(
            departement="RH & Communication",
            metier="Chargé de Communication Interne",
            nom_cas_usage="Chatbot support RH (RAG)",
            prompt="Un employé demande : 'Combien de jours de congé annuel ai-je droit, et comment faire ma demande ?' Réponds en te basant uniquement sur le règlement interne fourni en contexte.",
            sortie_attendue="Réponse précise citant le nombre de jours et la procédure, basée sur le document source fourni.",
            critere_succes="Réponse fidèle au document source (pas d'invention), ton clair et direct."
        ),

        # === Direction Marketing & Digital ===
        Scenario(
            departement="Marketing & Digital",
            metier="Responsable de Campagnes Digitales",
            nom_cas_usage="Génération de copies publicitaires",
            prompt="Génère 5 variantes de message SMS (max 160 caractères chacun) pour une promotion 4G+ à l'occasion du Ramadan, ciblant un public jeune urbain.",
            sortie_attendue="5 messages courts, distincts, respectant la limite de caractères, ton dynamique adapté à la cible.",
            critere_succes="Respect strict de la limite de 160 caractères, messages non redondants entre eux."
        ),
        Scenario(
            departement="Marketing & Digital",
            metier="Concepteur-Rédacteur / Brand Content Manager",
            nom_cas_usage="Rédaction d'article de blog / FAQ",
            prompt="Rédige un article de blog de 400 mots expliquant les avantages de la 5G pour les entreprises, optimisé SEO autour du mot-clé 'connectivité 5G entreprise'.",
            sortie_attendue="Article structuré avec titre accrocheur, introduction, 3 sections, conclusion, mot-clé intégré naturellement.",
            critere_succes="Longueur respectée (~400 mots), mot-clé présent au moins 3 fois de façon naturelle, pas de bourrage de mots-clés."
        ),

        # === Direction IT & Architecture ===
        Scenario(
            departement="IT & Architecture",
            metier="Développeur Logiciel / Ingénieur d'Études",
            nom_cas_usage="Génération de code",
            prompt="Écris une fonction Python qui valide qu'une adresse email est correctement formatée, avec gestion des cas limites, accompagnée d'un test unitaire.",
            sortie_attendue="Code Python fonctionnel avec la fonction de validation et au moins 3 tests unitaires (cas valide, invalide, limite).",
            critere_succes="Code exécutable sans erreur, gère les cas limites (email vide, sans @, sans domaine)."
        ),
        Scenario(
            departement="IT & Architecture",
            metier="Développeur Logiciel / Ingénieur d'Études",
            nom_cas_usage="Modernisation de code legacy",
            prompt="Voici un script COBOL simple qui calcule une facture : [extrait de code]. Traduis-le en Python moderne en conservant la même logique métier.",
            sortie_attendue="Code Python équivalent fonctionnellement, avec commentaires expliquant la correspondance avec l'original.",
            critere_succes="Logique métier préservée, code Python idiomatique, pas de perte de fonctionnalité."
        ),
        Scenario(
            departement="IT & Architecture",
            metier="Développeur Logiciel / Ingénieur d'Études",
            nom_cas_usage="Génération de documentation technique",
            prompt="Voici une fonction Python : [code de la fonction]. Génère une documentation technique claire (docstring + explication) pour cette fonction, à destination d'autres développeurs.",
            sortie_attendue="Docstring complet (paramètres, retour, exceptions) + paragraphe explicatif du fonctionnement.",
            critere_succes="Documentation fidèle au code fourni, format docstring standard (ex: Google style ou NumPy style)."
        ),

        # === Direction Réseau / Support Technique (NOC) ===
        Scenario(
            departement="Réseau / Support Technique (NOC)",
            metier="Technicien Support Clientèle Entreprises (B2B)",
            nom_cas_usage="Résolution d'incidents complexes",
            prompt="Un client B2B signale une panne de liaison louée depuis 2h. Voici l'historique de 3 incidents similaires : [texte des tickets]. Suggère les 3 étapes de résolution prioritaires.",
            sortie_attendue="Liste de 3 étapes classées par priorité, justifiées par les cas similaires fournis.",
            critere_succes="Étapes cohérentes avec l'historique fourni, priorisation logique et justifiée."
        ),

        # === Productivité Personnelle (Métiers Transversaux) ===
        Scenario(
            departement="Productivité Personnelle",
            metier="Chef de Projet / Manager",
            nom_cas_usage="Rédaction de compte-rendu de réunion",
            prompt="Voici la transcription brute d'une réunion de suivi de projet : [texte transcript]. Rédige un compte-rendu structuré avec décisions prises et actions assignées.",
            sortie_attendue="Compte-rendu avec sections : participants, décisions, actions (avec responsable et délai si mentionné).",
            critere_succes="Toutes les décisions et actions mentionnées dans la transcription sont reprises, rien d'inventé."
        ),
        Scenario(
            departement="Productivité Personnelle",
            metier="Consultant Interne / Analyste de Direction",
            nom_cas_usage="Veille concurrentielle et synthèse de rapport",
            prompt="Voici un extrait de rapport d'activité d'un opérateur concurrent : [texte du rapport]. Extrais les 3 KPIs financiers clés et les tendances de marché mentionnées.",
            sortie_attendue="Liste des KPIs avec leurs valeurs, et un résumé des tendances en 3-4 phrases.",
            critere_succes="KPIs extraits fidèlement au texte source, pas de chiffres inventés."
        ),
        Scenario(
            departement="Productivité Personnelle",
            metier="Consultant Interne / Analyste de Direction",
            nom_cas_usage="Gestion de boîte mail saturée",
            prompt="Voici une liste de 5 emails reçus : [textes des emails]. Classe-les par priorité (urgent/normal/faible) et propose une réponse courte pour l'email le plus urgent.",
            sortie_attendue="Classement des 5 emails avec justification courte, + brouillon de réponse pour le plus urgent.",
            critere_succes="Classement cohérent avec le contenu réel des emails, réponse proposée pertinente et professionnelle."
        ),

        # === Agents IA et Automatisation (Processus Opérationnels) ===
        Scenario(
            departement="Agents IA et Automatisation",
            metier="Conseiller Service Client (Call Center)",
            nom_cas_usage="Chatbot service client (RAG)",
            prompt="Un client demande : 'Comment activer mon forfait 4G+ depuis l'application My Ooredoo ?' Réponds en te basant sur la FAQ fournie en contexte.",
            sortie_attendue="Réponse étape par étape basée sur la FAQ, ton clair et orienté self-service.",
            critere_succes="Réponse fidèle à la FAQ source, pas d'étapes inventées non présentes dans le document."
        ),
        Scenario(
            departement="Agents IA et Automatisation",
            metier="Conseiller Service Client (Call Center)",
            nom_cas_usage="Analyse de sentiment sur appel client",
            prompt="Voici la transcription d'un appel client : [texte transcript]. Détermine le sentiment global (positif/neutre/négatif) et identifie le principal point d'irritation mentionné, s'il y en a un.",
            sortie_attendue="Sentiment classé + point d'irritation identifié avec citation courte du transcript à l'appui.",
            critere_succes="Classification cohérente avec le ton du transcript, point d'irritation réellement présent dans le texte."
        ),
    ]

    db.add_all(scenarios)
    db.commit()
    db.close()
    print(f"{len(scenarios)} scénarios insérés avec succès.")

if __name__ == "__main__":
    seed_scenarios()