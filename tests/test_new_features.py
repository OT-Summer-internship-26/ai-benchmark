"""
Tests unitaires pour les nouvelles fonctionnalités:
- generate_response_with_usage() pour chaque provider
- evaluer_toxicity()
- evaluer_harmfulness()

Tous les tests utilisent des mocks et ne nécessitent pas de LLM en cours d'exécution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestOllamaClientWithUsage:
    """Tests pour generate_response_with_usage dans ollama_client."""
    
    @patch('src.models_clients.ollama_client.requests.post')
    @patch('src.models_clients.ollama_client.requests.get')
    def test_generate_response_with_usage_returns_tuple(self, mock_get, mock_post):
        """Test que generate_response_with_usage retourne (str, dict) avec usage stats."""
        from src.models_clients.ollama_client import generate_response_with_usage
        
        # Mock Ollama health check
        mock_get.return_value = Mock(status_code=200, json=lambda: {"models": [{"name": "llama3.1:8b"}]})
        
        # Mock Ollama response with token counts
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Test response"},
                "eval_count": 50,  # completion tokens
                "prompt_eval_count": 100,  # prompt tokens
            }
        )
        
        response, usage_stats = generate_response_with_usage(
            question="Test question",
            context_chunks=["Test context"],
            model_name="llama3.1:8b"
        )
        
        # Assertions
        assert isinstance(response, str)
        assert response == "Test response"
        assert isinstance(usage_stats, dict)
        assert usage_stats["prompt_tokens"] == 100
        assert usage_stats["completion_tokens"] == 50
        assert usage_stats["total_tokens"] == 150
        assert "latency" in usage_stats
        assert "estimated_cost" in usage_stats
        assert usage_stats["estimated_cost"] == (150 / 1000.0) * 0.0002  # Ollama cost formula
    
    @patch('src.models_clients.ollama_client.requests.post')
    @patch('src.models_clients.ollama_client.requests.get')
    def test_generate_response_backward_compatible(self, mock_get, mock_post):
        """Test que generate_response() (sans _with_usage) retourne toujours une string."""
        from src.models_clients.ollama_client import generate_response
        
        # Mock Ollama health check
        mock_get.return_value = Mock(status_code=200, json=lambda: {"models": [{"name": "llama3.1:8b"}]})
        
        # Mock Ollama response
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "message": {"content": "Test response"},
                "eval_count": 50,
                "prompt_eval_count": 100,
            }
        )
        
        response = generate_response(
            question="Test question",
            context_chunks=["Test context"],
            model_name="llama3.1:8b"
        )
        
        # Assertions - doit retourner une string, pas un tuple
        assert isinstance(response, str)
        assert response == "Test response"


class TestGeminiClientWithUsage:
    """Tests pour generate_response_with_usage dans gemini_client."""
    
    @patch('src.models_clients.gemini_client.client.models.generate_content')
    def test_generate_response_with_usage_returns_tuple(self, mock_generate):
        """Test que generate_response_with_usage retourne (str, dict) avec usage stats."""
        from src.models_clients.gemini_client import generate_response_with_usage
        
        # Mock Gemini response with usage_metadata
        mock_response = Mock()
        mock_response.text = "Gemini test response"
        mock_response.usage_metadata = Mock(
            prompt_token_count=200,
            candidates_token_count=100,
            total_token_count=300
        )
        mock_generate.return_value = mock_response
        
        response, usage_stats = generate_response_with_usage(
            question="Test question",
            context_chunks=["Test context"]
        )
        
        # Assertions
        assert isinstance(response, str)
        assert response == "Gemini test response"
        assert isinstance(usage_stats, dict)
        assert usage_stats["prompt_tokens"] == 200
        assert usage_stats["completion_tokens"] == 100
        assert usage_stats["total_tokens"] == 300
        assert "latency" in usage_stats
        assert "estimated_cost" in usage_stats
        # Gemini cost: $0.075/1M input + $0.30/1M output
        expected_cost = (200 / 1_000_000) * 0.075 + (100 / 1_000_000) * 0.30
        assert abs(usage_stats["estimated_cost"] - expected_cost) < 0.0001
    
    @patch('src.models_clients.gemini_client.client.models.generate_content')
    def test_generate_response_with_usage_fallback_no_metadata(self, mock_generate):
        """Test fallback quand Gemini ne retourne pas usage_metadata."""
        from src.models_clients.gemini_client import generate_response_with_usage
        
        # Mock Gemini response WITHOUT usage_metadata
        mock_response = Mock()
        mock_response.text = "Short response"
        mock_response.usage_metadata = None  # Pas de metadata
        mock_generate.return_value = mock_response
        
        response, usage_stats = generate_response_with_usage(
            question="Test",
            context_chunks=["Context"]
        )
        
        # Assertions - doit utiliser le fallback (len // 4)
        assert isinstance(response, str)
        assert isinstance(usage_stats, dict)
        assert usage_stats["completion_tokens"] == len("Short response") // 4
        assert usage_stats["total_tokens"] > 0


class TestGroqClientWithUsage:
    """Tests pour generate_response_with_usage dans groq_client."""
    
    @patch('src.models_clients.groq_client.client.chat.completions.create')
    def test_generate_response_with_usage_returns_tuple(self, mock_create):
        """Test que generate_response_with_usage retourne (str, dict) avec usage stats."""
        from src.models_clients.groq_client import generate_response_with_usage
        
        # Mock Groq response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Groq test response"))]
        mock_response.usage = Mock(
            prompt_tokens=150,
            completion_tokens=75,
            total_tokens=225
        )
        mock_create.return_value = mock_response
        
        response, usage_stats = generate_response_with_usage(
            question="Test question",
            context_chunks=["Test context"]
        )
        
        # Assertions
        assert isinstance(response, str)
        assert response == "Groq test response"
        assert isinstance(usage_stats, dict)
        assert usage_stats["prompt_tokens"] == 150
        assert usage_stats["completion_tokens"] == 75
        assert usage_stats["total_tokens"] == 225
        assert usage_stats["estimated_cost"] == 0.0  # Groq free tier


class TestToxicityMetric:
    """Tests pour evaluer_toxicity dans metrics.py."""
    
    @patch('src.evaluation.metrics._appeler_juge')
    def test_evaluer_toxicity_calls_judge(self, mock_juge):
        """Test que evaluer_toxicity appelle le juge avec le bon prompt."""
        from src.evaluation.metrics import evaluer_toxicity
        
        mock_juge.return_value = {"note": 0.1, "justification": "Réponse appropriée"}
        
        result = evaluer_toxicity("Cette réponse est polie et professionnelle.")
        
        # Assertions
        assert mock_juge.called
        call_args = mock_juge.call_args[0]
        prompt_systeme = call_args[0]
        prompt_utilisateur = call_args[1]
        
        # Vérifier que le prompt contient les mots-clés
        assert "toxicité" in prompt_utilisateur.lower()
        assert "offensant" in prompt_utilisateur.lower() or "discriminatoire" in prompt_utilisateur.lower()
        assert "0.0" in prompt_utilisateur and "1.0" in prompt_utilisateur  # Échelle
        
        assert result == {"note": 0.1, "justification": "Réponse appropriée"}
    
    @patch('src.evaluation.metrics._appeler_juge')
    def test_evaluer_toxicity_returns_dict_with_note_and_justification(self, mock_juge):
        """Test que evaluer_toxicity retourne un dict avec note et justification."""
        from src.evaluation.metrics import evaluer_toxicity
        
        mock_juge.return_value = {"note": 0.8, "justification": "Langage inapproprié détecté"}
        
        result = evaluer_toxicity("Texte potentiellement problématique")
        
        assert isinstance(result, dict)
        assert "note" in result
        assert "justification" in result
        assert isinstance(result["note"], float)
        assert isinstance(result["justification"], str)


class TestHarmfulnessMetric:
    """Tests pour evaluer_harmfulness dans metrics.py."""
    
    @patch('src.evaluation.metrics._appeler_juge')
    def test_evaluer_harmfulness_calls_judge(self, mock_juge):
        """Test que evaluer_harmfulness appelle le juge avec le bon prompt."""
        from src.evaluation.metrics import evaluer_harmfulness
        
        mock_juge.return_value = {"note": 0.0, "justification": "Réponse sûre"}
        
        result = evaluer_harmfulness("Suivez les bonnes pratiques de sécurité.")
        
        # Assertions
        assert mock_juge.called
        call_args = mock_juge.call_args[0]
        prompt_systeme = call_args[0]
        prompt_utilisateur = call_args[1]
        
        # Vérifier que le prompt contient les mots-clés
        assert "nocivité" in prompt_utilisateur.lower() or "harmfulness" in prompt_utilisateur.lower()
        assert "dangereux" in prompt_utilisateur.lower() or "préjudice" in prompt_utilisateur.lower()
        assert "0.0" in prompt_utilisateur and "1.0" in prompt_utilisateur  # Échelle
        
        assert result == {"note": 0.0, "justification": "Réponse sûre"}
    
    @patch('src.evaluation.metrics._appeler_juge')
    def test_evaluer_harmfulness_returns_dict(self, mock_juge):
        """Test que evaluer_harmfulness retourne un dict avec note et justification."""
        from src.evaluation.metrics import evaluer_harmfulness
        
        mock_juge.return_value = {"note": 0.9, "justification": "Conseil potentiellement dangereux"}
        
        result = evaluer_harmfulness("Conseil médical non vérifié")
        
        assert isinstance(result, dict)
        assert "note" in result
        assert "justification" in result
    
    @patch('src.evaluation.metrics._appeler_juge')
    def test_evaluer_harmfulness_distinguishes_from_toxicity(self, mock_juge):
        """Test que le prompt de harmfulness mentionne la distinction avec toxicity."""
        from src.evaluation.metrics import evaluer_harmfulness
        
        mock_juge.return_value = {"note": 0.5, "justification": "Test"}
        
        evaluer_harmfulness("Texte test")
        
        call_args = mock_juge.call_args[0]
        prompt_utilisateur = call_args[1]
        
        # Le prompt doit mentionner que nocivité ≠ toxicité
        assert "polie" in prompt_utilisateur.lower() or "poli" in prompt_utilisateur.lower()
        assert "toxique" in prompt_utilisateur.lower() or "toxicité" in prompt_utilisateur.lower()
