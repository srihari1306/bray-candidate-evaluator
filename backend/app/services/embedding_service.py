
import asyncio
import hashlib
import json
import numpy as np
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.retry import retry_async

logger = get_logger("embeddings")


class EmbeddingService:
    """Generate embeddings using Azure OpenAI."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._cache: dict[str, list[float]] = {}

    @property
    def client(self):
        """Lazy-initialize the Azure OpenAI client."""
        if self._client is None:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                api_version=self.settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            )
        return self._client

    def _cache_key(self, text: str) -> str:
        """Generate a cache key for a text string."""
        return hashlib.md5(text.encode()).hexdigest()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if (not self.settings.AZURE_OPENAI_API_KEY or 
            "your-" in self.settings.AZURE_OPENAI_API_KEY or 
            not self.settings.AZURE_OPENAI_ENDPOINT or 
            "your-" in self.settings.AZURE_OPENAI_ENDPOINT):
            logger.warning("Using mock embedding generator")
            return [0.0] * self.settings.EMBEDDING_DIMENSIONS

        async def _embed():
            response = self.client.embeddings.create(
                input=text[:8191],  # Max input length
                model=self.settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                dimensions=self.settings.EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding

        try:
            embedding = await retry_async(
                _embed,
                max_retries=self.settings.MAX_RETRIES,
                operation_name="Generate embedding",
            )
            self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.warning(f"Embedding API call failed: {e}. Falling back to mock embedding.")
            return [0.0] * self.settings.EMBEDDING_DIMENSIONS

    async def generate_embeddings_batch(
        self, texts: list[str], batch_size: Optional[int] = None
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batches.
        Azure OpenAI supports up to 16 texts per API call.
        """
        if (not self.settings.AZURE_OPENAI_API_KEY or 
            "your-" in self.settings.AZURE_OPENAI_API_KEY or 
            not self.settings.AZURE_OPENAI_ENDPOINT or 
            "your-" in self.settings.AZURE_OPENAI_ENDPOINT):
            logger.warning(f"Using mock embedding generator for batch of {len(texts)} texts")
            return [[0.0] * self.settings.EMBEDDING_DIMENSIONS for _ in texts]

        batch_size = batch_size or self.settings.EMBEDDING_BATCH_SIZE
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Check cache first
            cached = []
            uncached_indices = []
            uncached_texts = []

            for j, text in enumerate(batch):
                cache_key = self._cache_key(text)
                if cache_key in self._cache:
                    cached.append((j, self._cache[cache_key]))
                else:
                    uncached_indices.append(j)
                    uncached_texts.append(text[:8191])

            # Generate uncached embeddings
            if uncached_texts:
                async def _embed_batch():
                    response = self.client.embeddings.create(
                        input=uncached_texts,
                        model=self.settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                        dimensions=self.settings.EMBEDDING_DIMENSIONS,
                    )
                    return [d.embedding for d in response.data]

                new_embeddings = await retry_async(
                    _embed_batch,
                    max_retries=self.settings.MAX_RETRIES,
                    operation_name=f"Batch embedding ({len(uncached_texts)} texts)",
                )

                # Cache new embeddings
                for text, emb in zip(uncached_texts, new_embeddings):
                    self._cache[self._cache_key(text)] = emb

                # Merge cached and new
                result = [None] * len(batch)
                for j, emb in cached:
                    result[j] = emb
                for idx, j in enumerate(uncached_indices):
                    result[j] = new_embeddings[idx]

                all_embeddings.extend(result)
            else:
                all_embeddings.extend([emb for _, emb in sorted(cached)])

            logger.info(f"Embedded batch {i // batch_size + 1}, total: {len(all_embeddings)}")

        return all_embeddings

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")


def get_embedding_service() -> EmbeddingService:

    return EmbeddingService()
