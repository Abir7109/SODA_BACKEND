"""
Supabase storage for SODA.
Two backends, in priority order:
1. Postgres session pooler (SUPABASE_DB_URL) — raw SQL, SODA creates its own tables
2. Supabase REST client (SUPABASE_URL + SUPABASE_KEY) — legacy, tables must pre-exist
3. File-based fallback lives in each memory module
"""
import os
import threading
from typing import Optional

_SUPABASE_CLIENT = None
_PG_CONN = None
_PG_LOCK = threading.Lock()


# ── REST client (legacy) ──

def get_supabase():
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    url = os.getenv("SUPABASE_URL", "") or os.getenv("SUPABASE_PROJECT_URL", "")
    key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        _SUPABASE_CLIENT = False
        return None

    try:
        from supabase import create_client
        _SUPABASE_CLIENT = create_client(url, key)
        return _SUPABASE_CLIENT
    except Exception as e:
        print(f"[Supabase] Failed to initialize REST client: {e}")
        _SUPABASE_CLIENT = False
        return None


# ── Postgres session pooler ──

def get_db():
    """Return a psycopg2 connection to the Supabase session pooler, or None."""
    global _PG_CONN
    with _PG_LOCK:
        if _PG_CONN is not None:
            return _PG_CONN
        url = os.getenv("SUPABASE_DB_URL", "") or os.getenv("DATABASE_URL", "")
        if not url:
            print("[MEMDB] pooler NOT configured: SUPABASE_DB_URL missing — memory will use file fallback")
            return None
        try:
            import psycopg2
            # ponytail: single shared conn; per-request pool if concurrency ever matters
            _PG_CONN = psycopg2.connect(url, connect_timeout=10)
            print("[MEMDB] pooler connected — DATABASE BACKEND ACTIVE")
            return _PG_CONN
        except Exception as e:
            print(f"[MEMDB] pooler connect FAILED: {e} — memory will use file fallback")
            return None


def db_configured() -> bool:
    return get_db() is not None


def db_execute(sql: str, params=None) -> bool:
    conn = get_db()
    if not conn:
        print(f"[MEMDB] exec skipped (no DB): {_short_sql(sql)}")
        return False
    with _PG_LOCK:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params if params else None)
            conn.commit()
            print(f"[MEMDB] exec OK: {_short_sql(sql)}")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[MEMDB] exec FAIL: {_short_sql(sql)} — {e}")
            return False


def db_fetch(sql: str, params=None):
    """Run a SELECT, return list of dicts, or None on no-DB/failure."""
    conn = get_db()
    if not conn:
        print(f"[MEMDB] fetch skipped (no DB): {_short_sql(sql)}")
        return None
    with _PG_LOCK:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params if params else None)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.commit()
            print(f"[MEMDB] fetch OK: {_short_sql(sql)} -> {len(rows)} rows")
            return rows
        except Exception as e:
            conn.rollback()
            print(f"[MEMDB] fetch FAIL: {_short_sql(sql)} — {e}")
            return None


def _short_sql(sql: str, n: int = 110) -> str:
    sql = " ".join((sql or "").split())
    return sql if len(sql) <= n else sql[:n] + "..."


# ── Tables (SODA creates its own schema) ──

TABLES = {
    "profiles": """
        CREATE TABLE IF NOT EXISTS profiles (
            id SERIAL PRIMARY KEY,
            name TEXT DEFAULT 'Sir',
            creator TEXT DEFAULT '',
            nationality TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )""",
    "facts": """
        CREATE TABLE IF NOT EXISTS facts (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
    "people": """
        CREATE TABLE IF NOT EXISTS people (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            relationship TEXT DEFAULT '',
            traits TEXT DEFAULT '',
            preferences TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )""",
    "lessons": """
        CREATE TABLE IF NOT EXISTS lessons (
            id SERIAL PRIMARY KEY,
            situation TEXT NOT NULL,
            correction TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
    "conversation_summaries": """
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id SERIAL PRIMARY KEY,
            session_id TEXT DEFAULT '',
            summary JSONB DEFAULT '{}',
            topics JSONB DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
    "custom_schemas": """
        CREATE TABLE IF NOT EXISTS custom_schemas (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            columns JSONB DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )""",
    "custom_entries": """
        CREATE TABLE IF NOT EXISTS custom_entries (
            id TEXT PRIMARY KEY,
            schema_name TEXT NOT NULL,
            data JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
    "camera_photos": """
        CREATE TABLE IF NOT EXISTS camera_photos (
            id SERIAL PRIMARY KEY,
            ts TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            description TEXT DEFAULT '',
            facing TEXT DEFAULT 'user',
            created_at TIMESTAMPTZ DEFAULT now()
        )""",
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            exchange_history JSONB DEFAULT '[]',
            turn_count INTEGER DEFAULT 0,
            started_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )""",
}

# Legacy tables from older SODA versions lack the columns current code uses.
# Add them idempotently — existing data stays untouched.
COLUMN_FIXES = [
    ("facts", "id BIGSERIAL"),
    ("facts", "created_at TIMESTAMPTZ DEFAULT now()"),
    ("people", "created_at TIMESTAMPTZ DEFAULT now()"),
    ("people", "updated_at TIMESTAMPTZ DEFAULT now()"),
    ("lessons", "created_at TIMESTAMPTZ DEFAULT now()"),
    ("profiles", "created_at TIMESTAMPTZ DEFAULT now()"),
    ("profiles", "updated_at TIMESTAMPTZ DEFAULT now()"),
]

TYPE_FIXES = [
    # (table, column, new_type, cast_using, default_expr)
    ("conversation_summaries", "topics", "JSONB", "to_jsonb(topics)", "'[]'::jsonb"),
    ("conversation_summaries", "id", None, None, "gen_random_uuid()"),
    ("profiles", "id", None, None, "gen_random_uuid()"),
]


def ensure_tables() -> bool:
    """Create every table SODA's memory modules expect. Run once at startup."""
    conn = get_db()
    if not conn:
        return False
    with _PG_LOCK:
        try:
            with conn.cursor() as cur:
                for ddl in TABLES.values():
                    cur.execute(ddl)
                for table, col in COLUMN_FIXES:
                    cur.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {col}')
                for table, col, new_type, using, default in TYPE_FIXES:
                    if new_type:
                        cur.execute(
                            f'ALTER TABLE "{table}" ALTER COLUMN "{col}" DROP DEFAULT'
                        )
                        cur.execute(
                            f'ALTER TABLE "{table}" ALTER COLUMN "{col}" TYPE {new_type} USING {using}'
                        )
                    cur.execute(
                        f'ALTER TABLE "{table}" ALTER COLUMN "{col}" SET DEFAULT {default}'
                    )
            conn.commit()
            print(f"[Supabase] Pooler connected — ensured {len(TABLES)} tables")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[Supabase] ensure_tables failed: {e}")
            return False


def is_configured() -> bool:
    return get_supabase() is not None or db_configured()


def table_exists(table_name: str) -> bool:
    rows = db_fetch(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
        (table_name,),
    )
    if rows is None:
        client = get_supabase()
        if not client:
            return False
        try:
            client.table(table_name).select("id").limit(1).execute()
            return True
        except Exception:
            return False
    return bool(rows)


if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(env_path)
    ok = ensure_tables()
    tables = db_fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    ) or []
    print(f"ensure_tables: {'OK' if ok else 'NOT CONFIGURED'}")
    print("tables:", ", ".join(t["table_name"] for t in tables))
    sys.exit(0 if ok else 1)