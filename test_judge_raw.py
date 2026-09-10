#!/usr/bin/env python3
"""Test the new judge model (qwen/qwen3.8-27b) with raw response capture."""

import sys
import json
sys.path.insert(0, 'src')

from groq import Groq
import httpx
import warnings
import os
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

# Initialize Groq client like in metrics.py
client = Groq(api_key=os.getenv('GROQ_API_KEY'), http_client=httpx.Client(verify=False))

# Test context_precision evaluation
question = 'What are the key requirements for a Backend Python Developer position?'
chunks = [
    'Backend Python developers should have 3+ years experience with Django and FastAPI frameworks.',
    'The position requires strong knowledge of database design and SQL optimization.',  
    'Candidates must be familiar with cloud deployment and containerization tools.',
    'This article discusses frontend JavaScript frameworks and React components.'  # Irrelevant chunk
]

# Create the same prompt as used in evaluer_context_precision
prompt_system = '''Tu es un expert en évaluation de systèmes RAG. Ta tâche est d'évaluer la précision du contexte récupéré.

Pour chaque chunk de contexte fourni, détermine s'il est pertinent pour répondre à la question posée.

Réponds UNIQUEMENT avec un objet JSON contenant :
- "relevant_chunks": liste des indices (commençant à 0) des chunks pertinents
- "score": ratio de chunks pertinents (nombre de chunks pertinents / nombre total de chunks)
- "justification": explication brève de ton évaluation

Exemple de format attendu :
{"relevant_chunks": [0, 2], "score": 0.67, "justification": "Les chunks 0 et 2 sont pertinents car ils traitent directement de la question posée, contrairement au chunk 1 qui est hors sujet."}'''

prompt_user = f'''Question : {question}

Chunks de contexte récupérés :
{chr(10).join(f"Chunk {i}: {chunk}" for i, chunk in enumerate(chunks))}

Évalue la pertinence de chaque chunk pour répondre à la question.'''

print('=== TESTING qwen/qwen3.8-27b RAW RESPONSE ===')
print(f'Question: {question}')
print(f'Number of chunks: {len(chunks)}')
print()

try:
    response = client.chat.completions.create(
        model='qwen/qwen3.8-27b',
        messages=[
            {'role': 'system', 'content': prompt_system},
            {'role': 'user', 'content': prompt_user},
        ],
        max_tokens=800,
        temperature=0,
        seed=42,
    )
    
    raw_content = response.choices[0].message.content.strip()
    print('Raw response:')
    print(repr(raw_content))
    print()
    print('Formatted response:')
    print(raw_content)
    print()
    
    # Try to parse as JSON
    try:
        parsed = json.loads(raw_content)
        print('Parsed JSON:')
        print(f'- Score: {parsed.get("score")}')
        print(f'- Relevant chunks: {parsed.get("relevant_chunks")}')
        print(f'- Justification: {parsed.get("justification")}')
        
        # Check quality of judgment
        print()
        print('Quality assessment:')
        print(f'- Expected relevant chunks: [0, 1, 2] (first 3 about Python dev)')
        print(f'- Expected irrelevant: [3] (about frontend JavaScript)')
        print(f'- Actual relevant chunks: {parsed.get("relevant_chunks")}')
        
        if set(parsed.get("relevant_chunks", [])) == {0, 1, 2}:
            print('✅ Perfect judgment - correctly identified relevant chunks!')
        elif 3 not in parsed.get("relevant_chunks", []):
            print('✅ Good judgment - at least excluded irrelevant chunk')
        else:
            print('❌ Poor judgment - included irrelevant chunk')
            
    except json.JSONDecodeError as e:
        print(f'JSON parsing failed: {e}')
        
except Exception as e:
    print(f'Error: {e}')