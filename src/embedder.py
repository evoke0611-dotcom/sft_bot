from typing import List
from openai import OpenAI

from src.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL


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

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []

        for text in texts:
            response = self.client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=text
            )
            embeddings.append(response.data[0].embedding)

        return embeddings