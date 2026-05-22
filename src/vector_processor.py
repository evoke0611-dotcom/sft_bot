import argparse
import json
from pathlib import Path

import psycopg

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


def load_chunks_from_jsonl(input_path: Path):
    chunks = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    return chunks


def build_chunks(use_existing_chunks: bool):
    chunks_path = PROCESSED_DATA_DIR / "chunks.jsonl"

    if use_existing_chunks:
        print(f"Step 1: Loading existing chunks from {chunks_path}...")
        return load_chunks_from_jsonl(chunks_path)

    print("Step 1: Loading documents...")
    documents = load_all_documents(RAW_DATA_DIR)
    print(f"Documents extracted: {len(documents)}")

    print("Step 2: Creating chunks...")
    chunks = create_chunks(documents)
    print(f"Chunks created: {len(chunks)}")

    print(f"Step 3: Saving chunks to {chunks_path}...")
    save_chunks_to_jsonl(chunks, chunks_path)

    return chunks


def parse_args():
    parser = argparse.ArgumentParser(description="Create or reload document embeddings.")
    parser.add_argument(
        "--use-existing-chunks",
        action="store_true",
        help="Load data/processed/chunks.jsonl and regenerate only the embeddings.",
    )
    parser.add_argument(
        "--recreate-table",
        action="store_true",
        help="Drop and recreate document_chunks before inserting fresh embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of chunks to send per OpenAI embeddings request.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    chunks = build_chunks(args.use_existing_chunks)

    if not chunks:
        print("No chunks found. Please check your data/raw folder or data/processed/chunks.jsonl.")
        return

    print("Step 4: Connecting to PostgreSQL pgvector...")
    try:
        store = VectorStore()
    except psycopg.OperationalError as exc:
        print("Could not connect to PostgreSQL pgvector.")
        print("Start the database first, for example: docker compose up -d")
        print(f"Database error: {exc}")
        return

    try:
        print("Step 5: Creating embeddings...")
        embedder = Embedder()
        texts = [chunk["content"] for chunk in chunks]
        embeddings = embedder.embed_batch(texts, batch_size=args.batch_size)
        embedder.validate_dimension(embeddings[0])

        print("Step 6: Storing data in PostgreSQL pgvector...")
        store.create_table(recreate=args.recreate_table)
        store.insert_chunks(chunks, embeddings)
    finally:
        store.close()

    print("Done. Your documents are stored in the vector database.")


if __name__ == "__main__":
    main()
