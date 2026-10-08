"""
Script pour traiter les images de login avec transparence.
1. Rendre le fond blanc de ooredoo_emblem.png transparent
2. Rendre le fond rouge de ooredoo_wordmark_white.png transparent
"""
from PIL import Image
import numpy as np
from pathlib import Path

def make_white_transparent(image_path):
    """
    Rend tous les pixels blancs (ou proches) transparents.
    Conserve les pixels colorés (rouge, etc.)
    """
    print(f"\n📝 Traitement: {image_path}")
    
    # Ouvrir l'image en RGBA
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img)
    
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}px")
    
    # Séparer les canaux
    red = data[:, :, 0].astype(float)
    green = data[:, :, 1].astype(float)
    blue = data[:, :, 2].astype(float)
    
    # Détection du blanc: R≈G≈B et tous proches de 255
    # On considère "blanc" si les 3 canaux sont > 240
    is_white = (red > 240) & (green > 240) & (blue > 240)
    
    # Créer le canal alpha
    alpha = np.where(is_white, 0, 255).astype(np.uint8)
    
    # Anti-aliasing sur les bords: transition douce entre 240 et 220
    transition_zone = ((red > 220) & (red <= 240)) | \
                      ((green > 220) & (green <= 240)) | \
                      ((blue > 220) & (blue <= 240))
    
    # Calculer l'alpha progressif pour la zone de transition
    avg_color = (red + green + blue) / 3
    alpha[transition_zone] = np.clip((255 - avg_color[transition_zone]) * 12, 0, 255).astype(np.uint8)
    
    # Appliquer le canal alpha
    data[:, :, 3] = alpha
    
    # Créer la nouvelle image
    result = Image.fromarray(data, mode="RGBA")
    
    # Recadrer pour enlever les bords transparents
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
        print(f"   Recadré à: {result.size[0]}x{result.size[1]}px")
    
    # Sauvegarder
    result.save(image_path, "PNG")
    
    # Compter les pixels transparents
    final_data = np.array(result)
    transparent_pixels = np.sum(final_data[:, :, 3] == 0)
    total_pixels = final_data.shape[0] * final_data.shape[1]
    
    print(f"   ✅ Sauvegardé: {transparent_pixels}/{total_pixels} pixels transparents")
    return result


def make_red_transparent(image_path):
    """
    Rend tous les pixels rouges (fond Ooredoo #ED1C24) transparents.
    Conserve uniquement les lettres blanches.
    """
    print(f"\n📝 Traitement: {image_path}")
    
    # Ouvrir l'image en RGBA
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img)
    
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}px")
    
    # Séparer les canaux
    red = data[:, :, 0].astype(float)
    green = data[:, :, 1].astype(float)
    blue = data[:, :, 2].astype(float)
    
    # Couleur cible: rouge Ooredoo #ED1C24 = RGB(237, 28, 36)
    target_red = 237
    target_green = 28
    target_blue = 36
    
    # Calculer la distance euclidienne à la couleur rouge cible
    distance = np.sqrt(
        (red - target_red)**2 + 
        (green - target_green)**2 + 
        (blue - target_blue)**2
    )
    
    # Tolérance: pixels proches du rouge (distance < 60) deviennent transparents
    tolerance = 60
    is_red = distance < tolerance
    
    # Créer le canal alpha
    alpha = np.where(is_red, 0, 255).astype(np.uint8)
    
    # Anti-aliasing: transition douce entre tolerance et tolerance*2
    transition_zone = (distance >= tolerance) & (distance < tolerance * 2)
    alpha[transition_zone] = ((distance[transition_zone] - tolerance) / tolerance * 255).astype(np.uint8)
    
    # Pour les lettres blanches, s'assurer qu'elles sont opaques
    is_white = (red > 200) & (green > 200) & (blue > 200)
    alpha[is_white] = 255
    
    # Appliquer le canal alpha
    data[:, :, 3] = alpha
    
    # Renforcer le blanc des lettres (les rendre blanc pur)
    data[is_white, 0] = 255  # R
    data[is_white, 1] = 255  # G
    data[is_white, 2] = 255  # B
    
    # Créer la nouvelle image
    result = Image.fromarray(data, mode="RGBA")
    
    # Recadrer pour enlever les bords transparents
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
        print(f"   Recadré à: {result.size[0]}x{result.size[1]}px")
    
    # Sauvegarder
    result.save(image_path, "PNG")
    
    # Statistiques
    final_data = np.array(result)
    transparent_pixels = np.sum(final_data[:, :, 3] == 0)
    opaque_pixels = np.sum(final_data[:, :, 3] == 255)
    total_pixels = final_data.shape[0] * final_data.shape[1]
    
    print(f"   ✅ Sauvegardé: {transparent_pixels} transparents, {opaque_pixels} opaques / {total_pixels} total")
    return result


def main():
    """Traite les deux images de login."""
    print("🚀 Traitement des images de login avec transparence\n")
    print("=" * 60)
    
    assets_dir = Path("assets")
    
    # Image 1: Emblème Ooredoo (rendre blanc transparent)
    emblem_path = assets_dir / "ooredoo_emblem.png"
    if emblem_path.exists():
        print("\n📌 IMAGE 1: Emblème Ooredoo (fond blanc → transparent)")
        make_white_transparent(emblem_path)
    else:
        print(f"\n⚠️  Fichier non trouvé: {emblem_path}")
    
    # Image 2: Wordmark blanc (rendre rouge transparent)
    wordmark_path = assets_dir / "ooredoo_wordmark_white.png"
    if wordmark_path.exists():
        print("\n📌 IMAGE 2: Wordmark blanc (fond rouge → transparent)")
        make_red_transparent(wordmark_path)
    else:
        print(f"\n⚠️  Fichier non trouvé: {wordmark_path}")
        print(f"   Info: Ce fichier sera créé quand vous placerez le wordmark source")
    
    print("\n" + "=" * 60)
    print("✅ Traitement terminé!\n")
    print("Prochaines étapes:")
    print("1. Relancer l'application: streamlit run src/dashboard/app.py")
    print("2. Vérifier les logos sur http://localhost:8502")
    print("3. Les logos doivent avoir des fonds transparents")


if __name__ == "__main__":
    main()
