import os
import traceback
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(".env", override=True)

database_url = os.getenv("DATABASE_URL")

print("DATABASE_URL loaded:", bool(database_url))

if database_url:
    parsed = urlparse(database_url)
    print("DB scheme:", parsed.scheme)
    print("DB host:", parsed.hostname)
    print("DB port:", parsed.port)
    print("DB username:", parsed.username)
    print("DB path:", parsed.path)

try:
    conn = psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor,
        connect_timeout=15,
    )

    cur = conn.cursor()
    cur.execute("SELECT NOW() AS current_time;")
    print("Database connected successfully")
    print(cur.fetchone())

    cur.close()
    conn.close()

except Exception as e:
    print("Database connection failed")
    print("Error type:", type(e).__name__)
    print("Error repr:", repr(e))
    print("Full traceback:")
    print(traceback.format_exc())