# Assets pour la page de login

## Images requises

Placez les images suivantes dans ce dossier avant d'exécuter le script de génération:

### 1. `ooredoo_wordmark_source.png`
- **Description:** Wordmark Ooredoo (lettres blanches sur fond rouge #ED1C24)
- **Format:** PNG
- **Traitement:** Le fond rouge sera rendu transparent, les lettres blanches conservées
- **Sortie:** `ooredoo_wordmark_white.png`

### 2. `ooredoo_emblem_source.png`
- **Description:** Emblème Ooredoo (logo rouge sur fond blanc)
- **Format:** PNG
- **Traitement:** Le fond blanc sera rendu transparent, le rouge conservé
- **Sortie:** `ooredoo_emblem.png`

## Génération

Une fois les images sources placées dans ce dossier:

```bash
python scripts/generate_login_assets.py
```

## Résultat

Le script générera:
- `assets/ooredoo_wordmark_white.png` - Wordmark blanc transparent (panneau gauche)
- `assets/ooredoo_emblem.png` - Emblème rouge transparent (bulle décorative)

Ces fichiers seront ensuite chargés en base64 par `src/dashboard/login_assets.py`.
