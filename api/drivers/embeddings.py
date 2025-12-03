from typing import Any, Dict, List
import logging
import os

logger = logging.getLogger(__name__)

from .base import BaseDriver, DriverResponse


class EmbeddingsDriver(BaseDriver):
    type = "embeddings"

    def execute(self, node: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        node_id = node.get("id", "unknown")
        data = node.get("data") or {}
        label = data.get("label", "Embeddings")

        logger.info(f"[Embeddings] Node: {label} ({node_id})")

        # Get configuration
        provider = data.get("provider", "openai").lower()
        model = data.get("model", "")
        api_key = data.get("api_key", "").strip()
        dimensions = data.get("dimensions")

        # Get input text
        input_val = context.get("input", "")
        text = str(input_val)

        if not text:
            return DriverResponse({
                "status": "error",
                "error": "No text provided for embedding generation",
            })

        logger.debug(f"[Embeddings] Provider: {provider}, Model: {model}")
        logger.debug(f"[Embeddings] Text length: {len(text)} characters")

        try:
            if provider == "openai":
                return self._openai_embeddings(text, model, api_key, dimensions)
            elif provider == "cohere":
                return self._cohere_embeddings(text, model, api_key)
            elif provider == "huggingface":
                return self._huggingface_embeddings(text, model, api_key)
            else:
                return DriverResponse({
                    "status": "error",
                    "error": f"Unsupported embeddings provider: {provider}",
                })
        except Exception as e:
            logger.error(f"[Embeddings] Error: {str(e)}")
            return DriverResponse({
                "status": "error",
                "error": f"Embeddings generation failed: {str(e)}",
            })

    def _openai_embeddings(self, text: str, model: str, api_key: str, dimensions: int = None) -> DriverResponse:
        """Generate embeddings using OpenAI."""
        try:
            import openai
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "OpenAI library not installed. Run: pip install openai",
            })

        # Use API key from config or environment
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return DriverResponse({
                "status": "error",
                "error": "OpenAI API key not provided",
            })

        # Default model
        if not model:
            model = "text-embedding-3-small"

        client = openai.OpenAI(api_key=api_key)

        # Build request params
        params = {
            "input": text,
            "model": model,
        }

        # Add dimensions for v3 models
        if dimensions and "text-embedding-3" in model:
            params["dimensions"] = int(dimensions)

        logger.info(f"[Embeddings] Calling OpenAI with model: {model}")
        response = client.embeddings.create(**params)

        embedding = response.data[0].embedding

        return DriverResponse({
            "status": "ok",
            "output": {
                "embeddings": embedding,
                "dimensions": len(embedding),
                "model": model,
                "provider": "openai",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            }
        })

    def _cohere_embeddings(self, text: str, model: str, api_key: str) -> DriverResponse:
        """Generate embeddings using Cohere."""
        try:
            import cohere
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "Cohere library not installed. Run: pip install cohere",
            })

        # Use API key from config or environment
        if not api_key:
            api_key = os.getenv("COHERE_API_KEY")

        if not api_key:
            return DriverResponse({
                "status": "error",
                "error": "Cohere API key not provided",
            })

        # Default model
        if not model:
            model = "embed-english-v3.0"

        client = cohere.Client(api_key)

        logger.info(f"[Embeddings] Calling Cohere with model: {model}")
        response = client.embed(
            texts=[text],
            model=model,
            input_type="search_document"  # or "search_query" depending on use case
        )

        embedding = response.embeddings[0]

        return DriverResponse({
            "status": "ok",
            "output": {
                "embeddings": embedding,
                "dimensions": len(embedding),
                "model": model,
                "provider": "cohere",
            }
        })

    def _huggingface_embeddings(self, text: str, model: str, api_key: str = None) -> DriverResponse:
        """Generate embeddings using HuggingFace (local or API)."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return DriverResponse({
                "status": "error",
                "error": "sentence-transformers library not installed. Run: pip install sentence-transformers",
            })

        # Default model
        if not model:
            model = "all-MiniLM-L6-v2"

        logger.info(f"[Embeddings] Loading HuggingFace model: {model}")

        try:
            model_obj = SentenceTransformer(model)
            embedding = model_obj.encode(text).tolist()

            return DriverResponse({
                "status": "ok",
                "output": {
                    "embeddings": embedding,
                    "dimensions": len(embedding),
                    "model": model,
                    "provider": "huggingface",
                }
            })
        except Exception as e:
            return DriverResponse({
                "status": "error",
                "error": f"HuggingFace embeddings failed: {str(e)}",
            })
