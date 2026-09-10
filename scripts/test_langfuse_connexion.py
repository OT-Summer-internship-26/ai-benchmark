"""
Script de vérification de la connexion Langfuse.
Envoie un trace de test et confirme si les clés sont valides.

Usage:
    python scripts/test_langfuse_connexion.py
"""
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Rétrocompatibilité : on synchronise LANGFUSE_BASE_URL si seule LANGFUSE_HOST est définie
if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
    os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST")

print("=== Vérification des variables d'environnement ===")
print(f"LANGFUSE_PUBLIC_KEY présent : {bool(os.getenv('LANGFUSE_PUBLIC_KEY'))}")
print(f"LANGFUSE_SECRET_KEY présent : {bool(os.getenv('LANGFUSE_SECRET_KEY'))}")
print(f"LANGFUSE_BASE_URL : {os.getenv('LANGFUSE_BASE_URL', '(défaut: https://cloud.langfuse.com)')}")
print()

from src.observability.langfuse_client import trace_llm_call, flush_langfuse, _initialize_langfuse
from src.observability import langfuse_client as lf_module

# Force l'initialisation
_initialize_langfuse()

print(f"Langfuse activé après init : {lf_module._langfuse_enabled}")
print()

if not lf_module._langfuse_enabled:
    print("❌ Langfuse n'est PAS activé. Vérifiez vos variables d'environnement dans .env.")
else:
    print("✅ Client Langfuse initialisé avec succès. Envoi d'une trace de test...")

    with trace_llm_call(
        name="test_connexion",
        model="test-model",
        input_prompt="Ceci est un test de connexion Langfuse.",
        metadata={"source": "test_manuel"},
    ) as trace:
        trace.set_output("Réponse de test.")
        trace.set_usage(prompt_tokens=10, completion_tokens=5, total_cost=0.0)

    # Forcer le flush du client officiel si accessible
    if lf_module._langfuse_client:
        lf_module._langfuse_client.flush()
    
    flush_langfuse()
    
    # Pause nécessaire pour laisser le thread HTTP d'arrière-plan expédier les données
    print("Envoi en cours vers les serveurs Langfuse...")
    time.sleep(3)
    
    print("✅ Trace envoyée. Vérifiez sur https://cloud.langfuse.com → Tracing.")