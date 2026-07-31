from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "facebook/nllb-200-distilled-600M"

_tokenizer = None
_model = None

CODES_NLLB = {
    "fr": "fra_Latn",
    "en": "eng_Latn",
    "ar": "arb_Arab",       # arabe standard
    "tn": "aeb_Arab",       # arabe tunisien (Derja)
}

MOTS_TUNISIENS = ["برشا", "توا", "آش", "فما", "كيفاش", "شنوا", "باهي", "زعمة", "ياسر"]


def detecter_arabe_tunisien(texte: str) -> bool:
    """Détecte la présence de mots caractéristiques du dialecte tunisien."""
    return any(mot in texte for mot in MOTS_TUNISIENS)


def _charger_modele():
    global _tokenizer, _model
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    return _tokenizer, _model


def traduire_depuis_francais(texte: str, code_langue_cible: str) -> str:
    """Traduit un texte français vers la langue cible (fr, en, ar, tn)."""
    if code_langue_cible == "fr" or code_langue_cible not in CODES_NLLB:
        return texte

    tokenizer, model = _charger_modele()
    code_cible_nllb = CODES_NLLB[code_langue_cible]

    paragraphes = texte.split("\n")
    resultats = []

    for p in paragraphes:
        if not p.strip():
            resultats.append(p)
            continue
        tokenizer.src_lang = "fra_Latn"
        inputs = tokenizer(p, return_tensors="pt", truncation=True, max_length=512)
        forced_bos = tokenizer.convert_tokens_to_ids(code_cible_nllb)
        traduction = model.generate(**inputs, forced_bos_token_id=forced_bos, max_length=512)
        texte_traduit = tokenizer.decode(traduction[0], skip_special_tokens=True)
        resultats.append(texte_traduit)

    return "\n".join(resultats)