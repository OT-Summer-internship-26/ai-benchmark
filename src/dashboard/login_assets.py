"""
Utilitaires pour charger les assets de la page de login.
Logos chargés en base64 avec cache pour performance.
"""
import base64
from pathlib import Path
from functools import lru_cache

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"

# Fallback: logo Ooredoo temporaire (sera remplacé par les vrais assets)
# Ce placeholder sera utilisé jusqu'à ce que les vraies images soient générées
PLACEHOLDER_LOGO = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@lru_cache(maxsize=2)
def load_logo_base64(filename: str) -> str:
    """
    Charge un logo en base64 avec cache.
    
    Args:
        filename: Nom du fichier dans assets/ (ex: "ooredoo_wordmark_white.png")
    
    Returns:
        String base64 de l'image
    """
    logo_path = ASSETS_DIR / filename
    
    if not logo_path.exists():
        # Fallback: utiliser LOGO_B64 de src.dashboard.logo si disponible
        try:
            from src.dashboard.logo import LOGO_B64
            return LOGO_B64
        except ImportError:
            return PLACEHOLDER_LOGO
    
    with open(logo_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    
    return encoded


def get_wordmark_white_base64() -> str:
    """
    Retourne le wordmark blanc (fond transparent) en base64.
    Fallback: utilise LOGO_B64 temporairement.
    """
    return load_logo_base64("ooredoo_wordmark_white.png")


def get_emblem_base64() -> str:
    """
    Retourne l'emblème Ooredoo (rouge, fond transparent) en base64.
    Fallback: utilise LOGO_B64 temporairement.
    """
    return load_logo_base64("ooredoo_emblem.png")
