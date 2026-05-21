import json
from pathlib import Path

from src.config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from src.extractor import load_all_documents
from src.chunker import create_chunks
from src.embedder import Embedder
from src.vector_store import VectorStore


def save_chunks_to_jsonl(chunks, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def main():
    print("Step 1: Loading documents...")
    documents = load_all_documents(RAW_DATA_DIR)
    print(f"Documents extracted: {len(documents)}")

    print("Step 2: Creating chunks...")
    chunks = create_chunks(documents)
    print(f"Chunks created: {len(chunks)}")

    if not chunks:
        print("No chunks found. Please check your data/raw folder.")
        return

    print("Step 3: Saving chunks to data/processed/chunks.jsonl...")
    save_chunks_to_jsonl(chunks, PROCESSED_DATA_DIR / "chunks.jsonl")

    print("Step 4: Creating embeddings...")
    embedder = Embedder()
    texts = [chunk["content"] for chunk in chunks]
    embeddings = embedder.embed_batch(texts)

    print("Step 5: Storing data in PostgreSQL pgvector...")
    store = VectorStore()
    store.create_table()
    store.insert_chunks(chunks, embeddings)
    store.close()

    print("Done. Your documents are stored in the vector database.")


if __name__ == "__main__":
    main()