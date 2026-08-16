"""
Custom exceptions for the benchmark pipeline.
"""


class BenchmarkException(Exception):
    """Base exception for benchmark-related errors."""
    pass


class DatabaseException(BenchmarkException):
    """Database operation failed."""
    pass


class RAGException(BenchmarkException):
    """RAG pipeline error."""
    pass


class LLMException(BenchmarkException):
    """LLM call error."""
    pass


class OllamaUnavailableException(LLMException):
    """Ollama service is not available."""
    pass


class ModelNotFoundError(LLMException):
    """Requested model not found."""
    pass


class EvaluationException(BenchmarkException):
    """Evaluation pipeline error."""
    pass


class ValidationException(BenchmarkException):
    """Input validation error."""
    pass


class AuthenticationException(BenchmarkException):
    """Authentication or authorization failed."""
    pass
