import os
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

# 1. Neutralisation du blocage SSL Windows / Antivirus / Proxy
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
old_merge_env = requests.Session.merge_environment_settings

def no_ssl_merge(self, url, proxies, stream, verify, cert):
    settings = old_merge_env(self, url, proxies, stream, verify, cert)
    settings["verify"] = False
    return settings

requests.Session.merge_environment_settings = no_ssl_merge

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_langfuse_client = None
_langfuse_enabled = False
_initialization_attempted = False


def _initialize_langfuse():
    global _langfuse_client, _langfuse_enabled, _initialization_attempted

    if _initialization_attempted:
        return _langfuse_enabled

    _initialization_attempted = True

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        logger.info("[Langfuse] Variables non définies. Monitoring désactivé.")
        _langfuse_enabled = False
        return False

    # Synchroniser LANGFUSE_BASE_URL
    os.environ["LANGFUSE_BASE_URL"] = host

    try:
        from langfuse import get_client
        _langfuse_client = get_client()
        _langfuse_enabled = True
        logger.info(f"[Langfuse] Client initialisé (host={host})")
        return True

    except Exception as e:
        logger.warning(f"[Langfuse] Échec initialisation : {e}")
        _langfuse_enabled = False
        return False


class LLMTrace:
    def __init__(self, observation=None):
        self.observation = observation
        self.start_time = time.time()
        self.output = None
        self.usage = {}
        self.metadata = {}

    def set_output(self, output: str):
        self.output = output
        if self.observation:
            try:
                self.observation.update(output=output)
            except Exception:
                pass

    def set_usage(self, prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None, total_cost: Optional[float] = None, **kwargs):
        if prompt_tokens is not None:
            self.usage["input"] = prompt_tokens
        if completion_tokens is not None:
            self.usage["output"] = completion_tokens
        if total_cost is not None:
            self.metadata["cost_usd"] = total_cost

        if self.observation:
            try:
                self.observation.update(
                    usage_details={"input": self.usage.get("input", 0), "output": self.usage.get("output", 0)},
                    metadata=self.metadata
                )
            except Exception:
                pass

    def set_metadata(self, **kwargs):
        self.metadata.update(kwargs)
        if self.observation:
            try:
                self.observation.update(metadata=self.metadata)
            except Exception:
                pass

    def finalize(self):
        pass


@contextmanager
def trace_llm_call(name: str, model: str, input_prompt: str, metadata: Optional[Dict[str, Any]] = None, trace_name: Optional[str] = None):
    if not _initialization_attempted:
        _initialize_langfuse()

    if not _langfuse_enabled or not _langfuse_client:
        yield LLMTrace(None)
        return

    try:
        # Utilisation de l'observation contextuelle standard v3
        with _langfuse_client.start_as_current_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_prompt,
            metadata=metadata or {}
        ) as observation:
            trace_item = LLMTrace(observation)
            yield trace_item
    except Exception as e:
        logger.debug(f"[Langfuse] Erreur trace : {e}")
        yield LLMTrace(None)


def flush_langfuse():
    if _langfuse_enabled and _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception:
            pass