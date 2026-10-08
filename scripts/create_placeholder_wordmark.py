"""
Crée un wordmark Ooredoo blanc temporaire.
À remplacer par la vraie image fournie par l'utilisateur.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_wordmark_placeholder():
    """Crée un simple texte 'OOREDOO' blanc sur fond transparent."""
    print("🎨 Création du wordmark Ooredoo (placeholder)...")
    
    # Créer une image RGBA transparente
    width = 600
    height = 150
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Texte blanc
    white = (255, 255, 255, 255)
    
    # Dessiner "OOREDOO" avec des cercles pour simuler le style
    # (En attendant d'avoir la vraie fonte)
    try:
        # Essayer avec une fonte système
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        # Fallback sur la fonte par défaut
        font = ImageFont.load_default()
    
    # Texte centré
    text = "OOREDOO"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill=white, font=font)
    
    # Recadrer les bords transparents
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    # Sauvegarder
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    output_path = assets_dir / "ooredoo_wordmark_white.png"
    
    img.save(output_path, "PNG")
    print(f"✅ Placeholder sauvegardé: {output_path}")
    print(f"   Taille: {img.size[0]}x{img.size[1]}px")
    print(f"\n⚠️  IMPORTANT: Remplacez ce fichier par le vrai wordmark Ooredoo!")
    print(f"   (lettres blanches sur fond transparent)")
    
    return img

if __name__ == "__main__":
    create_wordmark_placeholder()
