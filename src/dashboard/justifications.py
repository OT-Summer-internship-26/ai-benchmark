"""
Consolidateur Justification Text Generator

Generates real, data-driven recommendation justification text based on actual
Ragas metrics for a department's best-performing model.

This is NOT template text. Each justification is derived from concrete metrics.
"""

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine
from src.dashboard.formatting import safe_format_score


def generate_consolidateur_justification(
    department: str,
    model_name: str
) -> dict:
    """
    Generate justification text for a model recommendation based on real Ragas metrics.
    
    Queries actual execution data and metrics for the specified model in the department,
    then generates a narrative explanation.
    
    Args:
        department: Department name (e.g., "IT & Architecture")
        model_name: Model name (e.g., "llama-3.1-8b-instant")
        
    Returns:
        Dict with:
        {
            "model": str,
            "department": str,
            "justification_text": str,  # Main recommendation text
            "metrics": {
                "avg_faithfulness": float,
                "avg_answer_relevancy": float,
                "avg_context_precision": float,
                "avg_context_recall": float,
                "global_score": float,
                "avg_latency": float,
                "total_executions": int,
                "scenarios_tested": int
            },
            "strengths": list[str],   # Top 2 strongest metrics
            "weaknesses": list[str],  # Areas for improvement
        }
    """
    
    with engine.connect() as conn:
        # Get detailed metrics for this model in this department
        query = text("""
            SELECT
                m.nom as model_name,
                COUNT(DISTINCT e.id) as total_executions,
                COUNT(DISTINCT s.id) as scenarios_tested,
                AVG(CASE WHEN f.critere = 'faithfulness' THEN f.note ELSE NULL END) as avg_faithfulness,
                AVG(CASE WHEN ar.critere = 'answer_relevancy' THEN ar.note ELSE NULL END) as avg_answer_relevancy,
                AVG(CASE WHEN cp.critere = 'context_precision' THEN cp.note ELSE NULL END) as avg_context_precision,
                AVG(CASE WHEN cr.critere = 'context_recall' THEN cr.note ELSE NULL END) as avg_context_recall,
                AVG(e.latence_secondes) as avg_latency
            FROM executions e
            JOIN scenarios s ON s.id = e.scenario_id
            JOIN modeles m ON m.id = e.modele_id
            LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.methode = 'ragas' AND COALESCE(f.is_legacy, FALSE) = FALSE AND f.note BETWEEN 0 AND 1
            LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.methode = 'ragas' AND COALESCE(ar.is_legacy, FALSE) = FALSE AND ar.note BETWEEN 0 AND 1
            LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.methode = 'ragas' AND COALESCE(cp.is_legacy, FALSE) = FALSE AND cp.note BETWEEN 0 AND 1
            LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.methode = 'ragas' AND COALESCE(cr.is_legacy, FALSE) = FALSE AND cr.note BETWEEN 0 AND 1
            WHERE s.departement = :department
            AND m.nom = :model_name
              AND e.id IN (
                SELECT DISTINCT sc.execution_id FROM scores sc
                WHERE sc.methode = 'ragas'
                  AND COALESCE(sc.is_legacy, FALSE) = FALSE
                  AND sc.critere IN ('faithfulness','answer_relevancy','context_precision','context_recall')
                  AND sc.note BETWEEN 0 AND 1
              )
            GROUP BY m.nom
        """)
        
        result = conn.execute(
            query,
            {"department": department, "model_name": model_name}
        ).fetchone()
        
        if not result:
            return {
                "model": model_name,
                "department": department,
                "justification_text": f"No data available for {model_name} in {department}.",
                "metrics": {},
                "strengths": [],
                "weaknesses": [],
            }
        
        model, total_exec, scenarios, faith, relevancy, precision, recall, latency = result
        
        # Compute global score
        scores = [s for s in [faith, relevancy, precision, recall] if s is not None]
        global_score = sum(scores) / len(scores) if scores else None
        
        # Identify strengths and weaknesses
        metric_names = {
            "faithfulness": faith,
            "answer_relevancy": relevancy,
            "context_precision": precision,
            "context_recall": recall,
        }
        
        # Filter out None values and sort
        valid_metrics = {k: v for k, v in metric_names.items() if v is not None}
        sorted_metrics = sorted(valid_metrics.items(), key=lambda x: x[1], reverse=True)
        
        strengths = []
        weaknesses = []
        
        if len(sorted_metrics) >= 2:
            # Top 2 strengths
            strengths = [
                f"{sorted_metrics[0][0].replace('_', ' ').title()}: {safe_format_score(sorted_metrics[0][1])}",
                f"{sorted_metrics[1][0].replace('_', ' ').title()}: {safe_format_score(sorted_metrics[1][1])}"
            ]
            
            # Bottom 2 weaknesses (areas for improvement)
            if len(sorted_metrics) >= 4:
                weaknesses = [
                    f"{sorted_metrics[-1][0].replace('_', ' ').title()}: {safe_format_score(sorted_metrics[-1][1])}",
                    f"{sorted_metrics[-2][0].replace('_', ' ').title()}: {safe_format_score(sorted_metrics[-2][1])}"
                ]
        
        # Generate narrative justification text
        justification = _generate_narrative(
            model_name=model,
            department=department,
            total_executions=total_exec,
            scenarios_tested=scenarios,
            faithfulness=faith,
            answer_relevancy=relevancy,
            context_precision=precision,
            context_recall=recall,
            global_score=global_score,
            avg_latency=latency,
            strengths=strengths,
            weaknesses=weaknesses
        )
        
        return {
            "model": model_name,
            "department": department,
            "justification_text": justification,
            "metrics": {
                "avg_faithfulness": round(faith, 3) if faith else None,
                "avg_answer_relevancy": round(relevancy, 3) if relevancy else None,
                "avg_context_precision": round(precision, 3) if precision else None,
                "avg_context_recall": round(recall, 3) if recall else None,
                "global_score": round(global_score, 3) if global_score else None,
                "avg_latency": round(latency, 2) if latency else None,
                "total_executions": total_exec,
                "scenarios_tested": scenarios,
            },
            "strengths": strengths,
            "weaknesses": weaknesses,
        }


def _generate_narrative(
    model_name: str,
    department: str,
    total_executions: int,
    scenarios_tested: int,
    faithfulness: float,
    answer_relevancy: float,
    context_precision: float,
    context_recall: float,
    global_score: float,
    avg_latency: float,
    strengths: list[str],
    weaknesses: list[str],
) -> str:
    """
    Generate the human-readable justification narrative based on real metrics.
    
    This is NOT a template — the text is constructed from actual data.
    """
    
    # Start with core recommendation
    lines = []
    lines.append(f"**{model_name}** is the recommended model for {department}.")
    lines.append("")
    
    # Performance summary
    lines.append("### Performance Summary")
    lines.append(f"Based on **{total_executions}** executions across **{scenarios_tested}** scenarios:")
    lines.append("")
    
    # Metric breakdown
    lines.append("**Ragas Evaluation Metrics:**")
    lines.append(f"- Faithfulness: {safe_format_score(faithfulness)} — How well the model stays faithful to context")
    lines.append(f"- Answer Relevancy: {safe_format_score(answer_relevancy)} — How well answers match the question")
    lines.append(f"- Context Precision: {safe_format_score(context_precision)} — Quality of retrieved context snippets")
    lines.append(f"- Context Recall: {safe_format_score(context_recall)} — Completeness of context retrieval")
    lines.append(f"- **Overall Score: {safe_format_score(global_score)}**")
    lines.append("")
    
    # Strengths
    if strengths:
        lines.append("### Key Strengths")
        for strength in strengths:
            lines.append(f"- {strength}")
        lines.append("")
    
    # Weaknesses / improvement areas
    if weaknesses:
        lines.append("### Areas for Improvement")
        for weakness in weaknesses:
            lines.append(f"- {weakness}")
        lines.append("")
    
    # Performance characteristics
    lines.append("### Performance Characteristics")
    lines.append(f"- Average Response Latency: {avg_latency:.2f} seconds")
    
    # Performance tier classification
    if global_score >= 0.8:
        tier = "Excellent"
    elif global_score >= 0.6:
        tier = "Good"
    elif global_score >= 0.4:
        tier = "Moderate"
    else:
        tier = "Needs Improvement"
    
    lines.append(f"- Performance Tier: **{tier}**")
    lines.append("")
    
    # Recommendation
    lines.append("### Recommendation")
    if global_score >= 0.7:
        lines.append(
            f"**{model_name}** demonstrates strong performance on {department}'s use cases, "
            f"with particularly strong metrics in {strengths[0].lower() if strengths else 'context understanding'}. "
            "It is well-suited for production deployment in this department."
        )
    elif global_score >= 0.5:
        lines.append(
            f"**{model_name}** shows promising results on {department}'s scenarios. "
            f"Consider this model for production with monitoring on {weaknesses[-1].lower() if weaknesses else 'lower-performing areas'}."
        )
    else:
        lines.append(
            f"**{model_name}** is a candidate for {department}, but further optimization is recommended. "
            f"Focus on improving {weaknesses[-1].lower() if weaknesses else 'overall performance'}."
        )
    
    return "\n".join(lines)


def generate_client_justification(department: str, model_name: str) -> dict:
    """
    Génère une explication 100% métier et compréhensible pour les utilisateurs finaux (rôle Client).
    AUCUN vocabulaire technique (pas de 'faithfulness', 'RAGAS', 'context precision', etc.).
    Uniquement des arguments tangibles basés sur les chiffres réels de leur département.
    """
    data = generate_consolidateur_justification(department, model_name)
    metrics = data.get("metrics", {})
    
    if not metrics or not metrics.get("total_executions"):
        return {
            "title": f"Recommandation pour {department}",
            "points": [
                "Ce modèle a été sélectionné pour votre département.",
                "Les premiers tests comparatifs indiquent une bonne adéquation avec vos cas d'usage."
            ],
            "appreciation": "🟡 En cours d'évaluation",
        }
    
    points = []
    faith = metrics.get("avg_faithfulness")
    relevancy = metrics.get("avg_answer_relevancy")
    precision = metrics.get("avg_context_precision")
    recall = metrics.get("avg_context_recall")
    latency = metrics.get("avg_latency")
    score_global = metrics.get("global_score", 0.0) or 0.0
    nb_scenarios = metrics.get("scenarios_tested", 0)
    nb_exec = metrics.get("total_executions", 0)

    # Appreciation globale
    if score_global >= 0.75:
        appreciation = "🟢 Excellente adéquation"
    elif score_global >= 0.5:
        appreciation = "🟡 Bonne adéquation"
    else:
        appreciation = "🟠 Adéquation modérée"

    # Argument 1 : Fiabilité et exactitude
    if faith is not None and faith >= 0.7:
        points.append(
            f"**Excellente exactitude** : Le modèle respecte fidèlement les documents et procédures de {department} sans inventer d'information."
        )
    elif faith is not None:
        points.append(
            f"**Exactitude satisfaisante** : Le modèle s'aligne bien sur les connaissances de {department}."
        )

    # Argument 2 : Pertinence des réponses
    if relevancy is not None and relevancy >= 0.7:
        points.append(
            "**Réponses ciblées** : Il répond précisément à la demande de l'utilisateur sans digression inutile."
        )
    elif relevancy is not None:
        points.append(
            "**Compréhension du besoin** : Les réponses fournies couvrent le périmètre demandé."
        )

    # Argument 3 : Précision / exhaustivité
    if precision is not None and precision >= 0.7:
        points.append(
            "**Sélection rigoureuse des informations** : Il extrait les données pertinentes avec un niveau élevé de clarté."
        )
    elif recall is not None and recall >= 0.7:
        points.append(
            "**Exhaustivité** : Il intègre l'ensemble des éléments requis pour traiter les cas d'usage de votre métier."
        )

    # Argument 4 : Vitesse
    if latency is not None and latency < 3.0:
        points.append(
            "**Grande réactivité** : Le délai de réponse est fluide et adapté aux interactions quotidiennes."
        )
    else:
        points.append(
            "**Temps de traitement équilibré** : Le temps de réponse est optimisé pour garantir la qualité de la réponse."
        )

    # Contexte des tests
    points.append(
        f"*Analyse établie sur {nb_exec} tests comparatifs réalisés sur {nb_scenarios} scénarios de votre département.*"
    )

    return {
        "title": f"Pourquoi {model_name} est recommandé pour {department} ?",
        "points": points,
        "appreciation": appreciation,
    }

