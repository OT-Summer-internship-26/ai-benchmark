#!/usr/bin/env python3
"""Analyze the JSON truncation issue."""

import sys

# Raw response 1 (context_precision)
raw1 = '''
<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Evaluator
   - **Output Format:** Strict JSON only: `{"note": <float 0-1>, "justification": "<phrase courte>"}`
   - **Task:** Evaluate the PRECISION of the provided context for answering the question.
   - **Context (Chunks):** Job description for Backend Developer: Python 3 years exp, cloud infrastructure, REST APIs. Must have: Git, Docker, AWS/GCP, database design, CI/CD pipelines, team collaboration. Nice to have: Kubernetes, microservices, design patterns, code review experience.
   - **Question:** What skills are required for this Backend Developer position?
   - **Evaluation Criteria:** Do the chunks contain relevant information to answer the question? Note 1.0 = all relevant, 0.0 = none relevant.

2.  **Evaluate Context vs. Question:**
   - The question asks for the required skills for a Backend Developer position.
   - The context explicitly lists skills under "Must have" (Git, Docker, AWS/GCP, database design, CI/CD pipelines, team collaboration) and "Nice to have" (Kubernetes, microservices, design patterns, code review experience), plus general requirements (Python 3 years exp, cloud infrastructure, REST APIs).
   - This directly and completely answers the question.
   - All information in the context is highly relevant to the question.

3.  **Determine Score:**
   - Since the context perfectly matches the question and contains exactly the required information, the precision/relevance score should be 1.0.

4.  **Formulate Justification:**
   - Needs to be a short phrase in French (as the prompt is in French).
   - Example: "Le contexte liste explicitement toutes les compétences requises et souhaitées pour le poste."
   - Keep it concise.

5.  **Construct JSON Output:**
   - `{"note": 1.0, "justification": "Le contexte liste explicitement toutes les compétences requises et souhaitées pour le poste."}`
   - Check format: Valid JSON, no extra text, matches requested structure.

   All steps verified. Output matches requirements.✅
</think>

{"note": 1.0, "justification": "Le contexte liste explicit'
'''

# Raw response 2 (context_recall)
raw2 = '''
<think>
Here's a thinking process:

1.  **Analyze User Input:**
   - **Role:** Evaluator
   - **Output Format:** Strict JSON only: `{"note": <float 0-1>, "justification": "<phrase courte>"}`
   - **Task:** Evaluate the RECALL of the provided context relative to the expected output.
   - **Context Chunks:** Job description for Backend Developer: Python 3 years exp, cloud infrastructure, REST APIs. Must have: Git, Docker, AWS/GCP, database design, CI/CD pipelines, team collaboration. Nice to have: Kubernetes, microservices, design patterns, code review experience.
   - **Expected Output:** Minimum 3 years Python experience, cloud (AWS/GCP), Docker, REST APIs. Additional: design patterns, microservices, Kubernetes.
   - **Question:** Does the context contain ALL the necessary information to generate the expected output?
   - **Scale:** 1.0 = complete info, 0.0 = missing info.

2.  **Compare Context vs. Expected Output:**
   - *Expected:* "Minimum 3 years Python experience" -> *Context:* "Python 3 years exp" (Match)
   - *Expected:* "cloud (AWS/GCP)" -> *Context:* "cloud infrastructure", "AWS/GCP" (Match)
   - *Expected:* "Docker" -> *Context:* "Docker" (Match)
   - *Expected:* "REST APIs" -> *Context:* "REST APIs" (Match)
   - *Expected:* "Additional: design patterns, microservices, Kubernetes." -> *Context:* "Nice to have: Kubernetes, microservices, design patterns" (Match)
   - All elements in the expected output are explicitly present in the context chunks.

3.  **Determine Score:**
   - Since all information required for the expected output is present in the context, the recall is perfect.
   - Score: 1.0

4.  **Draft Justification (short phrase in French, as requested/implied by prompt language):**
   - "Toutes les informations requises sont présentes dans le contexte."
   - Or: "Le contexte contient l\'intégralité des éléments demandés."
   - Keep it concise.

5.  **Format Output:**
   - Must be strictly JSON:'
'''

print("📝 ANALYZING JSON TRUNCATION BUG\n")

print("="*80)
print("RESPONSE 1: context_precision")
print("="*80)
print(f"\nTotal length: {len(raw1)} chars")
print(f"Ends with: {repr(raw1[-100:])}")
print(f"\n❌ TRUNCATED: Response ends mid-JSON at: \"Le contexte liste explicit'")
print(f"   The justification string is incomplete!")

print("\n" + "="*80)
print("RESPONSE 2: context_recall")
print("="*80)
print(f"\nTotal length: {len(raw2)} chars")
print(f"Ends with: {repr(raw2[-100:])}")
print(f"\n❌ TRUNCATED: Response ends mid-sentence at: 'Must be strictly JSON:'")
print(f"   The entire JSON object is missing!")

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

print("""
✅ IDENTIFIED BUG:
   The Qwen model's <think> reasoning block is VERY long (600-1000+ tokens).
   With max_tokens=500 in the API call, the response gets cut off before the JSON is complete.

   Flow:
   1. Model generates <think>...</think> block (600+ tokens)
   2. Reaches max_tokens=500 limit mid-generation
   3. Response truncates before JSON is output
   4. Current regex strips <think>...</think> but leaves truncated text
   5. JSON extraction fails because no complete JSON object exists

⚠️  WHAT'S HAPPENING IN CURRENT CODE:
   1. Raw response ends with: `{"note": 1.0, "justification": "Le contexte liste explicit'`
   2. Regex `r'<think>.*?</think>'` doesn't match (no </think> tag!)
   3. Remaining text is: `{"note": 1.0, "justification": "Le contexte liste explicit'`
   4. Regex for JSON extraction: `r'\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}'`
      - This finds: `{"note": 1.0, "justification": "Le contexte liste explicit'`
      - But this has an UNTERMINATED STRING (no closing quote)
      - json.loads() fails: "Unterminated string escape"

🔧 PROPOSED FIX:
   Increase max_tokens for context_precision/recall evaluations.
   These metrics need longer thinking output than faithfulness/answer_relevancy.
""")

print("\n" + "="*80)
print("VALIDATION: Check for incomplete JSON strings")
print("="*80)

incomplete_json_1 = '{"note": 1.0, "justification": "Le contexte liste explicit\''
incomplete_json_2 = "Must be strictly JSON:"

print(f"\nAttempt to parse response 1 ending: {repr(incomplete_json_1)}")
import json
try:
    json.loads(incomplete_json_1)
    print("  ✅ Valid JSON")
except json.JSONDecodeError as e:
    print(f"  ❌ JSON ERROR: {e}")

print(f"\nAttempt to parse response 2 ending: {repr(incomplete_json_2)}")
try:
    json.loads(incomplete_json_2)
    print("  ✅ Valid JSON")
except json.JSONDecodeError as e:
    print(f"  ❌ JSON ERROR: {e}")
