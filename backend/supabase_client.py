import os
from typing import Optional

_SUPABASE_CLIENT = None


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
        print(f"[Supabase] Failed to initialize: {e}")
        _SUPABASE_CLIENT = False
        return None


def is_configured() -> bool:
    client = get_supabase()
    return client is not None and client is not False


def table_exists(table_name: str) -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        r = client.table(table_name).select("id").limit(1).execute()
        return True
    except Exception:
        return False
