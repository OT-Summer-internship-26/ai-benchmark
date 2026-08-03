from src.database.connection import engine
from sqlalchemy import text


def _evaluer_reponse(reponse: str, chunks_rag: list[str], prompt: str) -> dict:
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
    """Évalue chaque exécution et enregistre les scores en base."""
    print(f"\n[EVALUATEUR] Évaluation de {len(state['executions'])} exécutions...")

    scores_list = []
    erreurs = state.get("erreurs", [])

    index_chunks = {s["id"]: s["chunks_rag"] for s in state["scenarios"]}
    index_prompt = {s["id"]: s["prompt"] for s in state["scenarios"]}

    with engine.connect() as conn:
        for execution in state["executions"]:
            scenario_id = execution["scenario_id"]
            chunks_rag = index_chunks.get(scenario_id, [])
            prompt = index_prompt.get(scenario_id, "")

            scores = _evaluer_reponse(execution["reponse"], chunks_rag, prompt)

            print(f"\n  → [{execution['scenario_nom']}] | {execution['modele']}")
            print(f"     Complétude : {scores['completude']}/5")
            print(f"     Structure  : {scores['structure']}/5")
            print(f"     Fidélité   : {scores['fidelite_rag']}/5")
            print(f"     Honnêteté  : {scores['honnetete']}/5")
            print(f"     Global     : {scores['score_global']}/5")

            # Récupère l'id de la dernière exécution correspondante
            result = conn.execute(
                text("""
                    SELECT id FROM executions
                    WHERE scenario_id = :sid
                    ORDER BY date_execution DESC
                    LIMIT 1
                """),
                {"sid": scenario_id}
            )
            exec_row = result.fetchone()

            if exec_row:
                execution_id = exec_row[0]
                try:
                    criteres = {
                        "completude": scores["completude"],
                        "structure": scores["structure"],
                        "fidelite_rag": scores["fidelite_rag"],
                        "honnetete": scores["honnetete"],
                        "score_global": scores["score_global"],
                    }
                    for critere, note in criteres.items():
                        conn.execute(
                            text("""
                                INSERT INTO scores (execution_id, critere, note, commentaire)
                                VALUES (:exec_id, :critere, :note, :commentaire)
                            """),
                            {
                                "exec_id": execution_id,
                                "critere": critere,
                                "note": float(note),
                                "commentaire": f"Évaluation automatique — {critere}",
                            }
                        )
                    conn.commit()
                    print(f"     ✓ {len(criteres)} scores enregistrés (execution_id={execution_id})")
                except Exception as e:
                    erreurs.append(f"Erreur insertion score: {str(e)}")
                    print(f"     ✗ Erreur: {str(e)}")

            scores_list.append({**execution, "scores": scores})

    print(f"\n[EVALUATEUR] {len(scores_list)} évaluations terminées.")

    return {
        **state,
        "scores": scores_list,
        "erreurs": erreurs,
    }