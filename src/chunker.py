from typing import List, Dict, Any
from src.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Simple overlapping character-based chunking.
    """

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

        if start < 0:
            start = 0

        if start >= text_length:
            break

    return chunks


def create_chunks(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts extracted documents into chunks with metadata.
    """

    final_chunks = []

    for doc in documents:
        text = doc["text"]
        metadata = doc["metadata"]

        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = index
            chunk_metadata["total_chunks"] = len(chunks)

            final_chunks.append({
                "content": chunk,
                "metadata": chunk_metadata
            })

    return final_chunks