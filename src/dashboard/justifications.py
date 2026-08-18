"""
Consolidateur Justification Text Generator

Generates real, data-driven recommendation justification text based on actual
Ragas metrics for a department's best-performing model.

This is NOT template text. Each justification is derived from concrete metrics.
"""

import pandas as pd
from sqlalchemy import text
from src.database.connection import engine


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
            LEFT JOIN scores f ON f.execution_id = e.id AND f.critere = 'faithfulness' AND f.is_legacy = FALSE
            LEFT JOIN scores ar ON ar.execution_id = e.id AND ar.critere = 'answer_relevancy' AND ar.is_legacy = FALSE
            LEFT JOIN scores cp ON cp.execution_id = e.id AND cp.critere = 'context_precision' AND cp.is_legacy = FALSE
            LEFT JOIN scores cr ON cr.execution_id = e.id AND cr.critere = 'context_recall' AND cr.is_legacy = FALSE
            WHERE s.departement = :department
            AND m.nom = :model_name
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
                f"{sorted_metrics[0][0].replace('_', ' ').title()}: {sorted_metrics[0][1]:.1%}",
                f"{sorted_metrics[1][0].replace('_', ' ').title()}: {sorted_metrics[1][1]:.1%}"
            ]
            
            # Bottom 2 weaknesses (areas for improvement)
            if len(sorted_metrics) >= 4:
                weaknesses = [
                    f"{sorted_metrics[-1][0].replace('_', ' ').title()}: {sorted_metrics[-1][1]:.1%}",
                    f"{sorted_metrics[-2][0].replace('_', ' ').title()}: {sorted_metrics[-2][1]:.1%}"
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
    if faithfulness is not None:
        lines.append(f"- Faithfulness: {faithfulness:.1%} — How well the model stays faithful to context")
    else:
        lines.append("- Faithfulness: N/A — How well the model stays faithful to context")
    
    if answer_relevancy is not None:
        lines.append(f"- Answer Relevancy: {answer_relevancy:.1%} — How well answers match the question")
    else:
        lines.append("- Answer Relevancy: N/A — How well answers match the question")
    
    if context_precision is not None:
        lines.append(f"- Context Precision: {context_precision:.1%} — Quality of retrieved context snippets")
    else:
        lines.append("- Context Precision: N/A — Quality of retrieved context snippets")
    
    if context_recall is not None:
        lines.append(f"- Context Recall: {context_recall:.1%} — Completeness of context retrieval")
    else:
        lines.append("- Context Recall: N/A — Completeness of context retrieval")
    
    if global_score is not None:
        lines.append(f"- **Overall Score: {global_score:.1%}**")
    else:
        lines.append("- **Overall Score: N/A**")
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
