"""
Azure OpenAI embedding service.
Generates text embeddings using text-embedding-3-large for vector search.
"""

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

        async def _embed():
            response = self.client.embeddings.create(
                input=text[:8191],  # Max input length
                model=self.settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                dimensions=self.settings.EMBEDDING_DIMENSIONS,
            )
            return response.data[0].embedding

        embedding = await retry_async(
            _embed,
            max_retries=self.settings.MAX_RETRIES,
            operation_name="Generate embedding",
        )

        self._cache[cache_key] = embedding
        return embedding

    async def generate_embeddings_batch(
        self, texts: list[str], batch_size: Optional[int] = None
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batches.
        Azure OpenAI supports up to 16 texts per API call.
        """
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


# ─── Mock Implementation ────────────────────────────────────────────────────

class MockEmbeddingService(EmbeddingService):
    """Mock embedding service using random vectors for local development."""

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-random embedding based on text hash."""
        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use hash for deterministic results
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        embedding = rng.randn(self.settings.EMBEDDING_DIMENSIONS).tolist()

        # Normalize to unit vector
        norm = sum(x**2 for x in embedding) ** 0.5
        embedding = [x / norm for x in embedding]

        self._cache[cache_key] = embedding
        logger.debug(f"[MOCK] Generated {self.settings.EMBEDDING_DIMENSIONS}d embedding")
        return embedding

    async def generate_embeddings_batch(
        self, texts: list[str], batch_size: Optional[int] = None
    ) -> list[list[float]]:
        """Generate mock embeddings for a batch."""
        logger.info(f"[MOCK] Generating embeddings for {len(texts)} texts")
        results = []
        for text in texts:
            emb = await self.generate_embedding(text)
            results.append(emb)
        return results


def get_embedding_service() -> EmbeddingService:
    """Factory for embedding service."""
    settings = get_settings()
    if settings.MOCK_MODE:
        return MockEmbeddingService()
    return EmbeddingService()
