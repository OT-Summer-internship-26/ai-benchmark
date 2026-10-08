"""
Script pour corriger le fichier ooredoo_emblem.png qui contient 
une chaîne base64 au lieu de données binaires.
"""
import base64
from pathlib import Path

def fix_emblem_file():
    """Lit le fichier texte base64 et le convertit en vrai PNG binaire."""
    emblem_path = Path("assets/ooredoo_emblem.png")
    
    print(f"📝 Correction de {emblem_path}...")
    
    # Lire le contenu texte
    with open(emblem_path, 'r') as f:
        content = f.read()
    
    print(f"   Contenu lu: {len(content)} caractères")
    
    # Vérifier si c'est un data URL
    if content.startswith("data:image/png;base64,"):
        print("   ⚠️  Format data URL détecté, conversion en binaire...")
        # Extraire la partie base64
        base64_data = content.replace("data:image/png;base64,", "")
        
        # Décoder
        binary_data = base64.b64decode(base64_data)
        
        # Sauvegarder en binaire
        with open(emblem_path, 'wb') as f:
            f.write(binary_data)
        
        print(f"   ✅ Fichier corrigé: {len(binary_data)} octets")
        return True
    else:
        print("   ℹ️  Le fichier semble déjà être binaire")
        return False

if __name__ == "__main__":
    fix_emblem_file()
