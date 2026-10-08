"""
Crée un logo emblème Ooredoo temporaire (cercle rouge avec point).
À remplacer par la vraie image fournie par l'utilisateur.
"""
from PIL import Image, ImageDraw
from pathlib import Path

def create_emblem_placeholder():
    """Crée un simple logo emblème: cercle rouge + petit cercle."""
    print("🎨 Création du logo emblème Ooredoo (placeholder)...")
    
    # Créer une image RGBA transparente
    size = 200
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Couleur rouge Ooredoo
    red = (237, 28, 36, 255)
    
    # Grand cercle (anneau)
    # Cercle extérieur
    outer_circle = (20, 20, 140, 140)
    draw.ellipse(outer_circle, fill=red)
    
    # Cercle intérieur (pour créer l'anneau)
    inner_circle = (45, 45, 115, 115)
    draw.ellipse(inner_circle, fill=(0, 0, 0, 0))
    
    # Petit cercle (point en haut à droite)
    small_circle = (145, 15, 185, 55)
    draw.ellipse(small_circle, fill=red)
    
    # Sauvegarder
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    output_path = assets_dir / "ooredoo_emblem.png"
    
    img.save(output_path, "PNG")
    print(f"✅ Placeholder sauvegardé: {output_path}")
    print(f"   Taille: {size}x{size}px")
    print(f"\n⚠️  IMPORTANT: Remplacez ce fichier par le vrai logo Ooredoo!")
    
    return img

if __name__ == "__main__":
    create_emblem_placeholder()
