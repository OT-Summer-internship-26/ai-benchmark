# Référentiel de critères d'évaluation — Benchmark IA Ooredoo

## Critères qualitatifs (notés de 1 à 5 par un LLM juge ou évaluation manuelle)

1. **Pertinence** : la réponse répond-elle correctement à la question posée ?
2. **Fidélité au contexte (RAG)** : la réponse reste-t-elle basée sur les documents fournis, sans invention ?
3. **Clarté et structure** : la réponse est-elle bien organisée et compréhensible ?
4. **Respect de la langue** : la réponse est-elle dans la même langue que la question, quel que soit le contexte source ?

## Critères quantitatifs (mesurés automatiquement)

5. **Latence** : temps de réponse en secondes, mesuré entre l'envoi de la requête et la réception de la réponse
6. **Coût** : coût estimé par requête, calculé selon le tarif du modèle (`cout_par_1k_tokens` × nombre de tokens utilisés)

## Méthodologie de notation prévue

Les critères qualitatifs seront évalués via DeepEval/Ragas (Sprint 4), avec un LLM juge qui attribue une note de 1 à 5 selon des critères définis, ainsi qu'un commentaire justificatif stocké dans la table `scores`.