from types import SimpleNamespace

from src.models_clients.ollama_client import generate_response


def test_generate_response_uses_target_language_prompt_for_english(monkeypatch):
    captured = {}

    def fake_post(url, json):
        captured["payload"] = json
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"message": {"content": "The policy allows remote work."}},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr("src.models_clients.ollama_client.requests.post", fake_post)
    monkeypatch.setattr("src.models_clients.ollama_client.detect", lambda _: "en")
    monkeypatch.setattr(
        "src.models_clients.ollama_client.traduire_depuis_francais",
        lambda text, code: text,
    )

    result = generate_response("What is the policy?", ["Context about remote work"], model_name="test-model")

    assert result == "The policy allows remote work."
    prompt = captured["payload"]["messages"][0]["content"]
    assert "English" in prompt
    assert "FRANCAIS" not in prompt


def test_translate_french_answer_to_english_when_model_returns_french(monkeypatch):
    def fake_post(url, json):
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"message": {"content": "La politique autorise le travail à distance."}},
            raise_for_status=lambda: None,
        )

    translations = {}

    def fake_detect(text):
        return "en" if text == "What is the policy?" else "fr"

    def fake_translate(text, code):
        translations["called_with"] = (text, code)
        return "The policy allows remote work."

    monkeypatch.setattr("src.models_clients.ollama_client.requests.post", fake_post)
    monkeypatch.setattr("src.models_clients.ollama_client.detect", fake_detect)
    monkeypatch.setattr(
        "src.models_clients.ollama_client.traduire_depuis_francais",
        fake_translate,
    )

    result = generate_response("What is the policy?", ["Context about remote work"], model_name="test-model")

    assert result == "The policy allows remote work."
    assert translations["called_with"] == (
        "La politique autorise le travail à distance.",
        "en",
    )
