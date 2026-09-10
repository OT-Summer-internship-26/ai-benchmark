#!/usr/bin/env python3
"""Capture raw judge responses to debug JSON parsing issue."""

import sys
sys.path.insert(0, '.')

import os
import warnings
import httpx
import certifi
import json
import re

warnings.filterwarnings('ignore')

# Setup SSL
os.environ['SSL_CERT_FILE'] = certifi.where()

_original_httpx_client_init = httpx.Client.__init__

def _patched_httpx_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_httpx_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_httpx_client_init

from groq import Groq
from src.config.settings import GROQ_API_KEY

print("📝 Capturing raw judge responses for context_precision/recall\n")

client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))

# Mock context and data (simulating what happens with Qwen2.5 exec 4)
chunks = [
    "Job description for Backend Developer: Python 3 years exp, cloud infrastructure, REST APIs",
    "Must have: Git, Docker, AWS/GCP, database design, CI/CD pipelines, team collaboration",
    "Nice to have: Kubernetes, microservices, design patterns, code review experience"
]

question = "What skills are required for this Backend Developer position?"

expected_output = "Minimum 3 years Python experience, cloud (AWS/GCP), Docker, REST APIs. Additional: design patterns, microservices, Kubernetes."

print("=" * 80)
print("TEST 1: context_precision (chunks, question)")
print("=" * 80)

prompt_sys = (
    "Tu es un évaluateur. Tu réponds UNIQUEMENT en JSON valide, sans texte autour, "
    'au format: {"note": <float 0-1>, "justification": "<phrase courte>"}'
)

prompt_user = f"""Évalue la PRÉCISION du contexte fourni pour répondre à la question.

CHUNKS DE CONTEXTE:
{chr(10).join(chunks)}

QUESTION:
{question}

Évalue: Les chunks fournis contiennent-ils des informations pertinentes pour répondre?
Note 1.0 = tous pertinents, 0.0 = aucun pertinent"""

print("\nSending request...")
try:
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": prompt_sys},
            {"role": "user", "content": prompt_user}
        ],
        max_tokens=500,
        temperature=0,
        seed=42
    )
    
    raw_response = response.choices[0].message.content
    
    print("\n📝 RAW RESPONSE (context_precision):")
    print("-" * 80)
    print(repr(raw_response))
    print("-" * 80)
    print(f"\nLength: {len(raw_response)} chars")
    print(f"First 200 chars: {raw_response[:200]}")
    print(f"\n✅ Response captured\n")
    
except Exception as e:
    print(f"❌ Failed: {e}\n")

print("=" * 80)
print("TEST 2: context_recall (chunks, expected_output)")
print("=" * 80)

prompt_user_2 = f"""Évalue le RAPPEL du contexte fourni par rapport à la sortie attendue.

CHUNKS DE CONTEXTE:
{chr(10).join(chunks)}

SORTIE ATTENDUE (ce qu'on voudrait générer):
{expected_output}

Évalue: Le contexte contient-il TOUTES les infos nécessaires pour générer la sortie attendue?
Note 1.0 = infos complètes, 0.0 = infos manquantes"""

print("\nSending request...")
try:
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": prompt_sys},
            {"role": "user", "content": prompt_user_2}
        ],
        max_tokens=500,
        temperature=0,
        seed=42
    )
    
    raw_response = response.choices[0].message.content
    
    print("\n📝 RAW RESPONSE (context_recall):")
    print("-" * 80)
    print(repr(raw_response))
    print("-" * 80)
    print(f"\nLength: {len(raw_response)} chars")
    print(f"First 200 chars: {raw_response[:200]}")
    print(f"\n✅ Response captured\n")
    
except Exception as e:
    print(f"❌ Failed: {e}\n")

print("=" * 80)
print("ANALYSIS")
print("=" * 80)
