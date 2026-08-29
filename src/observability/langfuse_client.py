"""
Module d'intégration Langfuse pour le monitoring et l'observabilité des appels LLM.

Ce module fournit un wrapper optionnel et non-bloquant pour tracer les appels LLM
via Langfuse (https://langfuse.com). Si les variables d'environnement Langfuse ne
sont pas définies ou si les appels échouent, le pipeline continue normalement.

Configuration requise (.env) :
  LANGFUSE_PUBLIC_KEY    : Clé publique Langfuse (obtenir sur https://cloud.langfuse.com)
  LANGFUSE_SECRET_KEY    : Clé secrète Langfuse
  LANGFUSE_HOST          : URL de l'instance Langfuse (défaut: https://cloud.langfuse.com)

Usage dans les clients LLM :
  from src.observability.langfuse_client import trace_llm_call

  with trace_llm_call(
      name="ollama_generation",
      model="llama3.1:8b",
      input_prompt=prompt,
      metadata={"scenario_id": 123}
  ) as trace:
      response = call_llm(prompt)
      trace.set_output(response)
      trace.set_usage(prompt_tokens=150, completion_tokens=200, total_cost=0.001)
"""

import os
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Variable globale pour stocker le client Langfuse (lazy initialization)
_langfuse_client = None
_langfuse_enabled = False
_initialization_attempted = False


def _initialize_langfuse():
    """
    Initialise le client Langfuse de manière paresseuse.
    
    Retourne True si l'initialisation réussit, False sinon.
    Cette fonction est appelée automatiquement lors du premier trace.
    """
    global _langfuse_client, _langfuse_enabled, _initialization_attempted

    if _initialization_attempted:
        return _langfuse_enabled

    _initialization_attempted = True

    # Vérifier les variables d'environnement
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        logger.info(
            "[Langfuse] Variables d'environnement non définies "
            "(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY). "
            "Monitoring Langfuse désactivé — le pipeline continuera normalement."
        )
        _langfuse_enabled = False
        return False

    try:
        from langfuse import Langfuse
        
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        
        _langfuse_enabled = True
        logger.info(f"[Langfuse] Client initialisé avec succès (host={host})")
        return True

    except ImportError:
        logger.warning(
            "[Langfuse] Le package langfuse n'est pas installé. "
            "Installez-le avec: pip install langfuse"
        )
        _langfuse_enabled = False
        return False

    except Exception as e:
        logger.warning(
            f"[Langfuse] Échec de l'initialisation : {str(e)}. "
            "Le monitoring est désactivé, le pipeline continuera normalement."
        )
        _langfuse_enabled = False
        return False


class LLMTrace:
    """
    Classe helper pour simplifier le traçage des appels LLM avec Langfuse.
    
    Cette classe encapsule un objet Langfuse generation/span et fournit
    des méthodes simples pour enregistrer l'output, les tokens et le coût.
    """
    
    def __init__(self, langfuse_generation=None):
        self.generation = langfuse_generation
        self.start_time = time.time()
        self.metadata = {}
    
    def set_output(self, output: str):
        """Enregistre l'output du LLM."""
        if self.generation:
            try:
                self.generation.update(output=output)
            except Exception as e:
                logger.debug(f"[Langfuse] Erreur set_output: {e}")
    
    def set_usage(
        self,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        total_cost: Optional[float] = None,
    ):
        """
        Enregistre les statistiques d'usage (tokens et coût).
        
        Args:
            prompt_tokens: Nombre de tokens dans le prompt
            completion_tokens: Nombre de tokens dans la réponse
            total_tokens: Total de tokens (optionnel si prompt + completion fournis)
            total_cost: Coût estimé en USD
        """
        if not self.generation:
            return
        
        try:
            usage_data = {}
            
            if prompt_tokens is not None:
                usage_data["input"] = prompt_tokens
            
            if completion_tokens is not None:
                usage_data["output"] = completion_tokens
            
            if total_tokens is not None:
                usage_data["total"] = total_tokens
            elif prompt_tokens is not None and completion_tokens is not None:
                usage_data["total"] = prompt_tokens + completion_tokens
            
            if usage_data:
                self.generation.update(usage=usage_data)
            
            if total_cost is not None:
                self.generation.update(total_cost=total_cost)
                
        except Exception as e:
            logger.debug(f"[Langfuse] Erreur set_usage: {e}")
    
    def set_metadata(self, **kwargs):
        """Enregistre des métadonnées additionnelles."""
        if self.generation:
            try:
                self.metadata.update(kwargs)
                self.generation.update(metadata=self.metadata)
            except Exception as e:
                logger.debug(f"[Langfuse] Erreur set_metadata: {e}")
    
    def finalize(self):
        """
        Finalise le trace (calcule la latence, flush les données).
        Appelé automatiquement par le context manager.
        """
        if self.generation:
            try:
                latency_ms = (time.time() - self.start_time) * 1000
                self.generation.update(latency=latency_ms)
            except Exception as e:
                logger.debug(f"[Langfuse] Erreur finalize: {e}")


@contextmanager
def trace_llm_call(
    name: str,
    model: str,
    input_prompt: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_name: Optional[str] = None,
):
    """
    Context manager pour tracer un appel LLM avec Langfuse.
    
    Args:
        name: Nom de la génération (ex: "ollama_generation", "gemini_api_call")
        model: Nom du modèle utilisé (ex: "llama3.1:8b", "gemini-3.1-flash-lite")
        input_prompt: Le prompt envoyé au LLM
        metadata: Métadonnées optionnelles (ex: scenario_id, execution_id)
        trace_name: Nom du trace parent (défaut: "llm_generation")
    
    Yields:
        LLMTrace: Objet helper pour enregistrer l'output et les métriques
    
    Example:
        with trace_llm_call(
            name="ollama_llama3",
            model="llama3.1:8b",
            input_prompt=prompt,
            metadata={"scenario_id": 42}
        ) as trace:
            response = ollama_api_call(prompt)
            trace.set_output(response)
            trace.set_usage(prompt_tokens=150, completion_tokens=200, total_cost=0.001)
    """
    # Initialiser Langfuse si ce n'est pas déjà fait
    if not _initialization_attempted:
        _initialize_langfuse()
    
    # Si Langfuse n'est pas activé, retourner un trace dummy
    if not _langfuse_enabled:
        dummy_trace = LLMTrace(langfuse_generation=None)
        try:
            yield dummy_trace
        finally:
            pass  # Pas de cleanup nécessaire
        return
    
    # Créer le trace Langfuse
    generation = None
    try:
        trace = _langfuse_client.trace(name=trace_name or "llm_generation")
        
        generation = trace.generation(
            name=name,
            model=model,
            input=input_prompt,
            metadata=metadata or {},
        )
        
        trace_obj = LLMTrace(langfuse_generation=generation)
        
        yield trace_obj
        
    except Exception as e:
        # En cas d'erreur Langfuse, on log mais on ne fait pas planter le pipeline
        logger.debug(f"[Langfuse] Erreur lors du traçage : {e}")
        # Yield un trace dummy pour que le code appelant continue
        yield LLMTrace(langfuse_generation=None)
    
    finally:
        # Finaliser le trace
        try:
            if generation:
                trace_obj.finalize()
                _langfuse_client.flush()  # Envoyer les données à Langfuse
        except Exception as e:
            logger.debug(f"[Langfuse] Erreur lors de la finalisation : {e}")


def flush_langfuse():
    """
    Force l'envoi de toutes les données en attente vers Langfuse.
    
    À appeler en fin de pipeline ou avant l'arrêt de l'application
    pour s'assurer que toutes les traces sont envoyées.
    """
    if _langfuse_enabled and _langfuse_client:
        try:
            _langfuse_client.flush()
            logger.debug("[Langfuse] Flush effectué avec succès")
        except Exception as e:
            logger.debug(f"[Langfuse] Erreur lors du flush : {e}")
