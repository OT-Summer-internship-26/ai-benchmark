from types import SimpleNamespace

from src.models_clients.ollama_client import generate_response


def test_generate_response_uses_target_language_prompt_for_english(monkeypatch):
    captured = {}

    def fake_post(url, json):
        captured["payload"] = json
        return SimpleNamespace(json=lambda: {"message": {"content": "The policy allows remote work."}})

    monkeypatch.setattr("src.models_clients.ollama_client.requests.post", fake_post)
    monkeypatch.setattr("src.models_clients.ollama_client.detect", lambda _: "en")
    monkeypatch.setattr(
        "src.models_clients.ollama_client.traduire_depuis_francais",
        lambda text, code: text,
    )

    result = generate_response("What is the policy?", ["Context about remote work"], model_name="test-model")

    assert result == "The policy allows remote work."
    prompt = captured["payload"]["messages"][0]["content"]
    assert "English" in prompt or "english" in prompt
    assert "FRANÇAIS" not in prompt
