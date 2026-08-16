from src.database.connection import engine
from sqlalchemy import text
from src.utils.logger import setup_logger
from src.utils.exceptions import DatabaseException

logger = setup_logger(__name__)


def agent_consolidateur(state: dict) -> dict:
    """
    Agrège les scores Ragas par modèle et produit un rapport de synthèse.

    Note d'échelle : les 4 métriques Ragas (faithfulness, answer_relevancy,
    context_precision, context_recall) et le score_global sont notés entre
    0.0 et 1.0 — PAS sur 5 comme l'ancienne évaluation heuristique du Sprint 3.
    """
    logger.info(f"[CONSOLIDATEUR] Génération du rapport de synthèse...")

    erreurs = state.get("erreurs", [])

    # Agrégation par modèle
    synthese_modeles = {}

    for item in state["scores"]:
        modele = item["modele"]
        scores = item["scores"]

        if modele not in synthese_modeles:
            synthese_modeles[modele] = {
                "modele": modele,
                "nb_executions": 0,
                "latence_totale": 0.0,
                "scores_par_critere": {
                    "faithfulness": [],
                    "answer_relevancy": [],
                    "context_precision": [],
                    "context_recall": [],
                    "score_global": [],
                },
                "scenarios_testes": [],
            }

        synthese_modeles[modele]["nb_executions"] += 1
        synthese_modeles[modele]["latence_totale"] += item["latence"]
        synthese_modeles[modele]["scenarios_testes"].append(item["scenario_nom"])

        for critere in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            detail = scores.get(critere)
            # Chaque critère Ragas est un dict {"note": float|None, "justification": str}
            if detail and detail.get("note") is not None:
                synthese_modeles[modele]["scores_par_critere"][critere].append(detail["note"])

        # score_global est un float direct (ou None), pas un dict imbriqué
        if scores.get("score_global") is not None:
            synthese_modeles[modele]["scores_par_critere"]["score_global"].append(scores["score_global"])

    # Calcul des moyennes
    rapport = {}
    for modele, data in synthese_modeles.items():
        moyennes = {}
        for critere, notes in data["scores_par_critere"].items():
            if notes:
                moyennes[critere] = round(sum(notes) / len(notes), 3)

        rapport[modele] = {
            "modele": modele,
            "nb_executions": data["nb_executions"],
            "latence_moyenne": round(data["latence_totale"] / data["nb_executions"], 2),
            "moyennes": moyennes,
            "scenarios_testes": data["scenarios_testes"],
        }

    # Classement par score global (échelle 0-1)
    classement = sorted(
        rapport.values(),
        key=lambda x: x["moyennes"].get("score_global", 0),
        reverse=True
    )

    # Affichage du rapport
    separator = "=" * 60
    logger.info(f"\n{separator}")
    logger.info(f"RAPPORT DE BENCHMARK — {len(classement)} modèle(s) testé(s)")
    logger.info(f"(métriques Ragas, échelle 0.0 à 1.0)")
    logger.info(f"{separator}")

    for rang, modele_data in enumerate(classement, 1):
        logger.info(f"\n#{rang} {modele_data['modele']}")
        logger.info(f"   Exécutions         : {modele_data['nb_executions']}")
        logger.info(f"   Latence moy.       : {modele_data['latence_moyenne']}s")
        logger.info(f"   Score global       : {modele_data['moyennes'].get('score_global', 'N/A')}/1.0")
        logger.info(f"   Faithfulness       : {modele_data['moyennes'].get('faithfulness', 'N/A')}/1.0")
        logger.info(f"   Answer relevancy   : {modele_data['moyennes'].get('answer_relevancy', 'N/A')}/1.0")
        logger.info(f"   Context precision  : {modele_data['moyennes'].get('context_precision', 'N/A')}/1.0")
        logger.info(f"   Context recall     : {modele_data['moyennes'].get('context_recall', 'N/A')}/1.0")
        logger.info(f"   Scénarios          : {', '.join(modele_data['scenarios_testes'])}")

    logger.info(f"\n{separator}")
    if classement:
        meilleur = classement[0]
        logger.info(f"RECOMMANDATION : {meilleur['modele']} est le modèle le plus performant")
        logger.info(f"avec un score global moyen de {meilleur['moyennes'].get('score_global', 0)}/1.0")
        logger.info(f"et une latence moyenne de {meilleur['latence_moyenne']}s")
    logger.info(f"{separator}\n")

    return {
        **state,
        "rapport": {
            "classement": classement,
            "nb_modeles": len(classement),
            "nb_scenarios": len(state["scenarios"]),
        },
        "erreurs": erreurs,
    }