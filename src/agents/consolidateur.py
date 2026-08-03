from src.database.connection import engine
from sqlalchemy import text


def agent_consolidateur(state: dict) -> dict:
    """
    Agrège les scores par modèle et produit un rapport de synthèse.
    """
    print(f"\n[CONSOLIDATEUR] Génération du rapport de synthèse...")

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
                    "completude": [],
                    "structure": [],
                    "fidelite_rag": [],
                    "honnetete": [],
                    "score_global": [],
                },
                "scenarios_testes": [],
            }

        synthese_modeles[modele]["nb_executions"] += 1
        synthese_modeles[modele]["latence_totale"] += item["latence"]
        synthese_modeles[modele]["scenarios_testes"].append(item["scenario_nom"])

        for critere, note in scores.items():
            if critere in synthese_modeles[modele]["scores_par_critere"]:
                synthese_modeles[modele]["scores_par_critere"][critere].append(note)

    # Calcul des moyennes
    rapport = {}
    for modele, data in synthese_modeles.items():
        moyennes = {}
        for critere, notes in data["scores_par_critere"].items():
            if notes:
                moyennes[critere] = round(sum(notes) / len(notes), 2)

        rapport[modele] = {
            "modele": modele,
            "nb_executions": data["nb_executions"],
            "latence_moyenne": round(data["latence_totale"] / data["nb_executions"], 2),
            "moyennes": moyennes,
            "scenarios_testes": data["scenarios_testes"],
        }

    # Classement par score global
    classement = sorted(
        rapport.values(),
        key=lambda x: x["moyennes"].get("score_global", 0),
        reverse=True
    )

    # Affichage du rapport
    print(f"\n{'='*60}")
    print(f"RAPPORT DE BENCHMARK — {len(classement)} modèle(s) testé(s)")
    print(f"{'='*60}")

    for rang, modele_data in enumerate(classement, 1):
        print(f"\n#{rang} {modele_data['modele']}")
        print(f"   Exécutions     : {modele_data['nb_executions']}")
        print(f"   Latence moy.   : {modele_data['latence_moyenne']}s")
        print(f"   Score global   : {modele_data['moyennes'].get('score_global', 'N/A')}/5")
        print(f"   Complétude     : {modele_data['moyennes'].get('completude', 'N/A')}/5")
        print(f"   Structure      : {modele_data['moyennes'].get('structure', 'N/A')}/5")
        print(f"   Fidélité RAG   : {modele_data['moyennes'].get('fidelite_rag', 'N/A')}/5")
        print(f"   Honnêteté      : {modele_data['moyennes'].get('honnetete', 'N/A')}/5")
        print(f"   Scénarios      : {', '.join(modele_data['scenarios_testes'])}")

    print(f"\n{'='*60}")
    if classement:
        meilleur = classement[0]
        print(f"RECOMMANDATION : {meilleur['modele']} est le modèle le plus performant")
        print(f"avec un score global moyen de {meilleur['moyennes'].get('score_global', 0)}/5")
        print(f"et une latence moyenne de {meilleur['latence_moyenne']}s")
    print(f"{'='*60}\n")

    return {
        **state,
        "rapport": {
            "classement": classement,
            "nb_modeles": len(classement),
            "nb_scenarios": len(state["scenarios"]),
        },
        "erreurs": erreurs,
    }