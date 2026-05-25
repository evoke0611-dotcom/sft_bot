import os
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Always load the root .env file forcefully
load_dotenv(BASE_DIR / ".env", override=True)


def normalize_database_url(url: str | None) -> str:
    """
    Encode reserved characters in the username/password part of a database URL.

    Example:
    Raw password with @ can break URL parsing.
    abc@123 should become abc%40123 in the final URL.
    """

    if not url:
        raise RuntimeError(
            "DATABASE_URL is missing. Please add DATABASE_URL in your root .env file."
        )

    parts = urlsplit(url)

    if "@" not in parts.netloc:
        return url

    userinfo, hostinfo = parts.netloc.rsplit("@", 1)

    # Encode username/password area but keep ':' and '%' safe
    encoded_userinfo = quote(userinfo, safe=":%")

    return urlunsplit(parts._replace(netloc=f"{encoded_userinfo}@{hostinfo}"))


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

RAW_DATA_DIR = BASE_DIR / os.getenv("RAW_DATA_DIR", "data/raw")
PROCESSED_DATA_DIR = BASE_DIR / os.getenv("PROCESSED_DATA_DIR", "data/processed")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".csv", ".xlsx"]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small"
)