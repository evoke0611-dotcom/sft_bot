from typing import List
from openai import OpenAI

from src.config import EMBEDDING_DIM, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL


class Embedder:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        embeddings = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            response = self.client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=batch
            )
            embeddings.extend(item.embedding for item in response.data)

        return embeddings

    def validate_dimension(self, embedding: List[float]):
        actual_dim = len(embedding)
        if actual_dim != EMBEDDING_DIM:
            raise ValueError(
                f"OpenAI embedding dimension is {actual_dim}, but EMBEDDING_DIM is {EMBEDDING_DIM}. "
                "Update EMBEDDING_DIM in .env/config before loading vectors."
            )
