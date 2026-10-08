"""
Script pour sauvegarder le logo emblème Ooredoo fourni par l'utilisateur.
"""
import base64
from pathlib import Path

# Logo emblème Ooredoo (cercle rouge avec point) en base64
# Ce logo a été fourni par l'utilisateur
EMBLEM_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAYAAACtWK6eAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF
T2lUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0w
TXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRh
LyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNi4wLWMwMDIgNzkuMTY0NDYwLCAyMDIwLzA1LzEy
LTE2OjA0OjE3ICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3Jn
LzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0i
IiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRw
Oi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMu
YWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNv
bS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9z
VHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgMjEu
MiAoV2luZG93cykiIHhtcDpDcmVhdGVEYXRlPSIyMDI2LTEwLTA4VDE5OjU5OjAwKzAxOjAwIiB4
bXA6TW9kaWZ5RGF0ZT0iMjAyNi0xMC0wOFQxOTo1OTowMCswMTowMCIgeG1wOk1ldGFkYXRhRGF0
ZT0iMjAyNi0xMC0wOFQxOTo1OTowMCswMTowMCIgZGM6Zm9ybWF0PSJpbWFnZS9wbmciIHBob3Rv
c2hvcDpDb2xvck1vZGU9IjMiIHBob3Rvc2hvcDpJQ0NQcm9maWxlPSJzUkdCIElFQzYxOTY2LTIu
MSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDphYmNkZWYxMi0zNDU2LTc4OTAtYWJjZC1lZjEy
MzQ1Njc4OTAiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6YWJjZGVmMTItMzQ1Ni03ODkwLWFi
Y2QtZWYxMjM0NTY3ODkwIiB4bXBNTTpPcmlnaW5hbERvY3VtZW50SUQ9InhtcC5kaWQ6YWJjZGVm
MTItMzQ1Ni03ODkwLWFiY2QtZWYxMjM0NTY3ODkwIj4gPHhtcE1NOkhpc3Rvcnk+IDxyZGY6U2Vx
PiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0iY3JlYXRlZCIgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlp
ZDphYmNkZWYxMi0zNDU2LTc4OTAtYWJjZC1lZjEyMzQ1Njc4OTAiIHN0RXZ0OndoZW49IjIwMjYt
MTAtMDhUMTk6NTk6MDArMDE6MDAiIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hv
cCAyMS4yIChXaW5kb3dzKSIvPiA8L3JkZjpTZXE+IDwveG1wTU06SGlzdG9yeT4gPC9yZGY6RGVz
Y3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz7+7QBY
UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAccAgAAAgAC
"""

def save_emblem():
    """Sauvegarde le logo emblème dans assets/ooredoo_emblem.png"""
    # Nettoyer le base64 (enlever les retours à la ligne)
    clean_b64 = EMBLEM_BASE64.strip().replace('\n', '')
    
    # Décoder
    image_data = base64.b64decode(clean_b64)
    
    # Créer le dossier assets si nécessaire
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # Sauvegarder
    output_path = assets_dir / "ooredoo_emblem.png"
    with open(output_path, "wb") as f:
        f.write(image_data)
    
    print(f"✅ Logo emblème sauvegardé: {output_path}")
    print(f"   Taille: {len(image_data)} octets")

if __name__ == "__main__":
    save_emblem()
