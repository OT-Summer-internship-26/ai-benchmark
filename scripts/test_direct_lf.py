import os
import time
import urllib3
import requests
from dotenv import load_dotenv

# 1. Désactiver les avertissements et forcer la désactivation SSL sur urllib3 / requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch global de la vérification SSL pour requests / OpenTelemetry
old_merge_env = requests.Session.merge_environment_settings

def no_ssl_merge(self, url, proxies, stream, verify, cert):
    settings = old_merge_env(self, url, proxies, stream, verify, cert)
    settings["verify"] = False
    return settings

requests.Session.merge_environment_settings = no_ssl_merge

# Forcer les variables d'environnement à ignorer les bundles SSL
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'

# 2. Charger le .env
load_dotenv()

if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
    os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_HOST")

print(f"Connexion avec : {os.getenv('LANGFUSE_PUBLIC_KEY')} sur {os.getenv('LANGFUSE_BASE_URL')}")

from langfuse import get_client

# 3. Initialiser le client Langfuse
langfuse = get_client()

print("Création de la trace de test...")
with langfuse.start_as_current_observation(name="test_connexion_directe", as_type="generation") as generation:
    generation.update(
        model="llama3.1:8b",
        input="Bonjour Langfuse, test contournement SSL.",
        output="Connexion réussie !",
        usage_details={"input": 10, "output": 15, "total": 25},
        metadata={"environnement": "local_vscode"}
    )

print("Envoi vers Langfuse (flush)...")
langfuse.flush()

time.sleep(3)
print("✅ Trace envoyée ! Rafraîchissez votre page Langfuse.")