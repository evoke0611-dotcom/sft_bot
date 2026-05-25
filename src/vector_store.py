import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlsplit

from dotenv import load_dotenv

# Force-load root .env file before importing config
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

import psycopg
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector

from src.config import DATABASE_URL, EMBEDDING_DIM


def get_database_url() -> str:
    """
    Always read DATABASE_URL fresh from environment.
    This avoids stale values when FastAPI reloads.
    """
    database_url = os.getenv("DATABASE_URL") or DATABASE_URL

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Please add DATABASE_URL in your root .env file."
        )

    return database_url


class VectorStore:
    def __init__(self):
        self.database_url = get_database_url()

        try:
            self.conn = psycopg.connect(self.database_url, connect_timeout=10)

        except psycopg.OperationalError as exc:
            parsed_url = urlsplit(self.database_url)
            host = parsed_url.hostname or ""
            username = parsed_url.username or ""
            port = parsed_url.port

            if host.endswith(".supabase.co"):
                raise RuntimeError(
                    "Could not connect to the Supabase direct database host. "
                    "This host may resolve to IPv6 only on your network. "
                    "Use the Supabase IPv4-compatible pooler connection string in DATABASE_URL."
                ) from exc

            if "pooler.supabase.com" in host:
                raise RuntimeError(
                    "Could not connect to Supabase pooler. "
                    f"Detected host: {host}, port: {port}, user: {username}. "
                    "Please confirm DATABASE_URL uses this format: "
                    "postgresql://postgres.PROJECT_REF:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
                ) from exc

            raise

        self._ensure_vector_extension()
        register_vector(self.conn)

    def _ensure_vector_extension(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        self.conn.commit()

    def create_table(self, recreate: bool = False):
        """
        Creates pgvector extension and document_chunks table.
        """

        with self.conn.cursor() as cur:
            if recreate:
                cur.execute("DROP TABLE IF EXISTS document_chunks;")

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    chunk_id TEXT UNIQUE NOT NULL,
                    source_file TEXT,
                    file_type TEXT,
                    page INTEGER,
                    chunk_index INTEGER,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding VECTOR({EMBEDDING_DIM}),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_source_file
                ON document_chunks(source_file);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata
                ON document_chunks USING GIN(metadata);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
                ON document_chunks
                USING hnsw (embedding vector_cosine_ops);
            """)

        self.conn.commit()

    @staticmethod
    def generate_chunk_id(content: str, metadata: Dict[str, Any]) -> str:
        raw = (
            f"{metadata.get('source_file')}|"
            f"{metadata.get('page')}|"
            f"{metadata.get('chunk_index')}|"
            f"{content}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def insert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Inserts chunks and embeddings into PostgreSQL.
        """

        with self.conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings):
                metadata = chunk["metadata"]
                content = chunk["content"]

                chunk_id = self.generate_chunk_id(content, metadata)

                cur.execute("""
                    INSERT INTO document_chunks
                    (
                        chunk_id,
                        source_file,
                        file_type,
                        page,
                        chunk_index,
                        content,
                        metadata,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        source_file = EXCLUDED.source_file,
                        file_type = EXCLUDED.file_type,
                        page = EXCLUDED.page,
                        chunk_index = EXCLUDED.chunk_index,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """, (
                    chunk_id,
                    metadata.get("source_file"),
                    metadata.get("file_type"),
                    metadata.get("page"),
                    metadata.get("chunk_index"),
                    content,
                    Jsonb(metadata),
                    embedding,
                ))

        self.conn.commit()

    def search(self, query_embedding: List[float], top_k: int = 5):
        """
        Searches similar chunks using cosine distance.
        """

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (
                query_embedding,
                query_embedding,
                top_k,
            ))

            results = cur.fetchall()

        return [
            {
                "content": row[0],
                "metadata": row[1],
                "similarity": float(row[2]),
            }
            for row in results
        ]

    def close(self):
        if self.conn:
            self.conn.close()