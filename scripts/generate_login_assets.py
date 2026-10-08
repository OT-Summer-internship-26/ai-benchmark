"""
Script de génération des assets pour la page de login.
Crée les logos transparents à partir des images fournies.

Usage: python scripts/generate_login_assets.py
"""
import os
from pathlib import Path
from PIL import Image
import numpy as np

def make_red_transparent(input_path: str, output_path: str, tolerance: int = 40):
    """
    Rend le fond rouge transparent en gardant les lettres blanches.
    
    Args:
        input_path: Chemin vers l'image source (wordmark rouge)
        output_path: Chemin de sortie (PNG transparent)
        tolerance: Tolérance de couleur pour détecter le rouge (#ED1C24)
    """
    print(f"📝 Traitement de {input_path}...")
    
    # Ouvrir l'image en RGBA
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)
    
    # Couleur cible: #ED1C24 (rouge Ooredoo)
    target_red = np.array([237, 28, 36])
    
    # Calculer la distance de chaque pixel au rouge cible
    red = data[:, :, 0].astype(float)
    green = data[:, :, 1].astype(float)
    blue = data[:, :, 2].astype(float)
    
    # Distance euclidienne au rouge
    distance = np.sqrt(
        (red - target_red[0])**2 + 
        (green - target_red[1])**2 + 
        (blue - target_red[2])**2
    )
    
    # Masque: pixels proches du rouge deviennent transparents
    # Plus la distance est faible, plus l'alpha est proche de 0
    alpha = np.where(distance < tolerance, 0, 255).astype(np.uint8)
    
    # Anti-aliasing sur les bords: transition douce
    transition_zone = (distance >= tolerance) & (distance < tolerance * 2)
    alpha[transition_zone] = ((distance[transition_zone] - tolerance) / tolerance * 255).astype(np.uint8)
    
    # Appliquer le canal alpha
    data[:, :, 3] = alpha
    
    # Créer l'image résultante
    result = Image.fromarray(data, mode="RGBA")
    
    # Recadrer aux limites du contenu (supprimer les bords transparents)
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
    
    # Sauvegarder
    result.save(output_path, "PNG")
    print(f"✅ Sauvegardé: {output_path} ({result.size[0]}x{result.size[1]}px)")


def make_white_transparent(input_path: str, output_path: str, tolerance: int = 30):
    """
    Rend le fond blanc transparent en gardant l'emblème rouge.
    
    Args:
        input_path: Chemin vers l'image source (emblème sur fond blanc)
        output_path: Chemin de sortie (PNG transparent)
        tolerance: Tolérance pour détecter le blanc
    """
    print(f"📝 Traitement de {input_path}...")
    
    # Ouvrir l'image en RGBA
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img)
    
    # Calculer la distance au blanc pur
    red = data[:, :, 0].astype(float)
    green = data[:, :, 1].astype(float)
    blue = data[:, :, 2].astype(float)
    
    # Pixels proches du blanc (R≈G≈B≈255)
    avg_color = (red + green + blue) / 3
    is_white = (avg_color > 255 - tolerance) & (red > 255 - tolerance)
    
    # Masque: blanc devient transparent
    alpha = np.where(is_white, 0, 255).astype(np.uint8)
    
    # Anti-aliasing
    transition = (avg_color > 255 - tolerance * 2) & (avg_color <= 255 - tolerance)
    alpha[transition] = ((255 - avg_color[transition]) / tolerance * 255).astype(np.uint8)
    
    # Appliquer le canal alpha
    data[:, :, 3] = alpha
    
    # Créer l'image résultante
    result = Image.fromarray(data, mode="RGBA")
    
    # Recadrer
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
    
    # Sauvegarder
    result.save(output_path, "PNG")
    print(f"✅ Sauvegardé: {output_path} ({result.size[0]}x{result.size[1]}px)")


def main():
    """Génère les assets pour la page de login."""
    # Créer le dossier assets s'il n'existe pas
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    print("🚀 Génération des assets de login...\n")
    
    # WORDMARK: lettres blanches, fond rouge transparent
    wordmark_input = assets_dir / "ooredoo_wordmark_source.png"
    wordmark_output = assets_dir / "ooredoo_wordmark_white.png"
    
    if wordmark_input.exists():
        make_red_transparent(str(wordmark_input), str(wordmark_output), tolerance=50)
    else:
        print(f"⚠️  Fichier source manquant: {wordmark_input}")
        print("   Veuillez placer l'image du wordmark (lettres blanches sur fond rouge)")
    
    print()
    
    # EMBLÈME: logo rouge, fond blanc transparent
    emblem_input = assets_dir / "ooredoo_emblem_source.png"
    emblem_output = assets_dir / "ooredoo_emblem.png"
    
    if emblem_input.exists():
        make_white_transparent(str(emblem_input), str(emblem_output), tolerance=40)
    else:
        print(f"⚠️  Fichier source manquant: {emblem_input}")
        print("   Veuillez placer l'image de l'emblème (rouge sur fond blanc)")
    
    print("\n✅ Génération terminée!")
    print("\n📋 Fichiers attendus:")
    print(f"   Input:  {wordmark_input}")
    print(f"   Output: {wordmark_output}")
    print(f"   Input:  {emblem_input}")
    print(f"   Output: {emblem_output}")


if __name__ == "__main__":
    main()
