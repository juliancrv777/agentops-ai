import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


class EmbeddingProvider(Protocol):
    name: str
    model: str

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...


class DeterministicEmbeddingProvider:
    name = "deterministic"
    model = "feature-hash-v1"

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())

        if not tokens:
            vector[0] = 1.0
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector

        return [value / norm for value in vector]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return [item.embedding for item in response.data]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower().strip()

    if provider == "deterministic":
        return DeterministicEmbeddingProvider(settings.embedding_dimensions)

    if provider == "openai":
        if not settings.openai_api_key or not settings.openai_embedding_model:
            raise RuntimeError(
                "OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL are required "
                "when EMBEDDING_PROVIDER=openai"
            )
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    raise RuntimeError(f"unsupported embedding provider: {provider}")
