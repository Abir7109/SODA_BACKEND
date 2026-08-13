"""
Dynamic schema-based memory for SODA.
Allows Gemini to create arbitrary memory schemas at runtime for recurring topics.
Storage: Supabase (if configured) or file-based fallback.

Tables:
- custom_schemas: {id, name, columns: [{name, type, description}], created_at}
- custom_entries: {id, schema_name, data: {jsonb}, created_at}
"""
import json
from pathlib import Path
from datetime import datetime

MEM_DIR = Path("projects/long_term_memory/custom").resolve()
MEM_DIR.mkdir(parents=True, exist_ok=True)
SCHEMAS_PATH = Path("projects/long_term_memory/custom_schemas.jsonl").resolve()

_SUPABASE = None

def _db():
    global _SUPABASE
    if _SUPABASE is None:
        from supabase_client import get_supabase
        _SUPABASE = get_supabase()
    return _SUPABASE


def _pg():
    from supabase_client import get_db, db_fetch, db_execute
    return get_db(), db_fetch, db_execute


# ── Real-table helpers (Postgres pooler) ──

_TYPE_MAP = {
    "text": "TEXT", "string": "TEXT", "str": "TEXT", "varchar": "TEXT",
    "integer": "INTEGER", "int": "INTEGER",
    "float": "DOUBLE PRECISION", "double": "DOUBLE PRECISION", "number": "DOUBLE PRECISION", "decimal": "DOUBLE PRECISION",
    "boolean": "BOOLEAN", "bool": "BOOLEAN",
    "date": "DATE", "datetime": "TIMESTAMPTZ",
    "json": "JSONB", "jsonb": "JSONB", "list": "JSONB", "array": "JSONB",
}


def _ident(name: str) -> str:
    """Sanitize an LLM-supplied identifier for use as a Postgres column/table name."""
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in (name or "").lower())
    if not out or out[0].isdigit():
        out = "_" + out
    return out or "_col"


def table_name_for(schema_name: str) -> str:
    return "mem_" + _ident(schema_name)


def _ensure_mem_table(db_execute, schema_name: str, columns: list) -> bool:
    name = table_name_for(schema_name)
    cols = ['"created_at" TIMESTAMPTZ DEFAULT now()']
    for col in columns or []:
        cname = _ident((col or {}).get("name", ""))
        ctype = _TYPE_MAP.get(str((col or {}).get("type", "text")).lower(), "TEXT")
        cols.append(f'"{cname}" {ctype}')
    sql = f'CREATE TABLE IF NOT EXISTS "{name}" ({", ".join(cols)})'
    if not db_execute(sql):
        return False
    for col in columns or []:
        cname = _ident((col or {}).get("name", ""))
        ctype = _TYPE_MAP.get(str((col or {}).get("type", "text")).lower(), "TEXT")
        db_execute(f'ALTER TABLE "{name}" ADD COLUMN IF NOT EXISTS "{cname}" {ctype}')
    return True


# ── Schema Management ──

def create_memory_schema(name, description="", columns=None):
    """Create a new memory schema with named columns.
    columns: list of {name, type, description}
    Returns {success, schema: {name, columns, created_at}}
    """
    name = name.strip().lower().replace(" ", "_")
    if not name:
        return {"success": False, "error": "Schema name is required"}
    if not columns or not isinstance(columns, list):
        return {"success": False, "error": "columns must be a non-empty list of {name, type, description}"}
    now = datetime.now().isoformat()

    db, fetch, execute = _pg()
    if db:
        try:
            _ensure_mem_table(execute, name, columns)
            rows = fetch("SELECT id FROM custom_schemas WHERE name=%s LIMIT 1", (name,))
            if rows:
                ok = execute(
                    "UPDATE custom_schemas SET columns=%s, description=%s, updated_at=%s WHERE id=%s",
                    (json.dumps(columns), description, now, rows[0]["id"]),
                )
            else:
                ok = execute(
                    "INSERT INTO custom_schemas (name, description, columns, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (name, description, json.dumps(columns), now, now),
                )
            if ok:
                print(f"[MEMDB] create_memory_schema({name!r}) -> db OK, real table created")
                return {"success": True, "action": "updated" if rows else "created",
                        "schema": {"name": name, "columns": columns, "description": description}}
            print(f"[MEMDB] create_memory_schema({name!r}) -> db FAIL, using fallback")
        except Exception as e:
            print(f"[Supabase] create_memory_schema failed: {e}")

    db = _db()
    if db:
        try:
            existing = db.table("custom_schemas").select("id").eq("name", name).limit(1).execute()
            if existing.data and len(existing.data) > 0:
                db.table("custom_schemas").update({
                    "columns": columns,
                    "description": description,
                    "updated_at": now,
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                db.table("custom_schemas").insert({
                    "name": name,
                    "description": description,
                    "columns": columns,
                    "created_at": now,
                    "updated_at": now,
                }).execute()
        except Exception as e:
            print(f"[Supabase] create_memory_schema failed: {e}")

    SCHEMAS_PATH.touch(exist_ok=True)
    schemas = []
    found = False
    try:
        with open(SCHEMAS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("name") == name:
                    entry["columns"] = columns
                    entry["description"] = description
                    entry["updated_at"] = now
                    found = True
                schemas.append(entry)
    except FileNotFoundError:
        pass
    if not found:
        schemas.append({
            "name": name,
            "description": description,
            "columns": columns,
            "created_at": now,
            "updated_at": now,
        })
    with open(SCHEMAS_PATH, "w", encoding="utf-8") as f:
        for s in schemas:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return {"success": True, "action": "updated" if found else "created", "schema": {"name": name, "columns": columns, "description": description}}


def list_custom_schemas():
    """List all custom memory schemas with their column definitions."""
    db, fetch, execute = _pg()
    if db:
        try:
            rows = fetch(
                "SELECT name, description, columns, created_at FROM custom_schemas "
                "ORDER BY id DESC"
            )
            if rows is not None:
                schemas = []
                for row in rows:
                    cols = row.get("columns") or []
                    if isinstance(cols, str):
                        try:
                            cols = json.loads(cols)
                        except Exception:
                            cols = []
                    schemas.append({
                        "name": row.get("name", ""),
                        "description": row.get("description", ""),
                        "columns": cols,
                        "created_at": str(row.get("created_at") or ""),
                    })
                return {"success": True, "count": len(schemas), "schemas": schemas}
        except Exception as e:
            print(f"[Supabase] list_custom_schemas failed: {e}")
    db = _db()
    if db:
        try:
            r = db.table("custom_schemas").select("*").execute()
            schemas = []
            for row in reversed(r.data or []):
                schemas.append({
                    "name": row.get("name", ""),
                    "description": row.get("description", ""),
                    "columns": row.get("columns", []),
                    "created_at": row.get("created_at", ""),
                })
            return {"success": True, "count": len(schemas), "schemas": schemas}
        except Exception as e:
            print(f"[Supabase] list_custom_schemas failed: {e}")
    if not SCHEMAS_PATH.exists():
        return {"success": True, "count": 0, "schemas": []}
    schemas = []
    try:
        with open(SCHEMAS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    schemas.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"success": False, "error": str(e), "schemas": []}
    return {"success": True, "count": len(schemas), "schemas": schemas}


# ── Data CRUD ──

def _get_entries_path(schema_name):
    return MEM_DIR / f"{schema_name}.jsonl"


def store_custom_memory(schema_name, data):
    """Store an entry in a custom schema.
    schema_name: name of previously created schema
    data: dict matching schema columns
    Returns {success, entry: {id, schema_name, data, created_at}}
    """
    schema_name = schema_name.strip().lower().replace(" ", "_")
    if not schema_name or not data or not isinstance(data, dict):
        return {"success": False, "error": "schema_name and data dict are required"}
    now = datetime.now().isoformat()
    entry_id = f"{schema_name}_{int(datetime.now().timestamp())}"

    db, fetch, execute = _pg()
    if db:
        try:
            tname = table_name_for(schema_name)
            rows = fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s", (tname,)
            )
            colnames = [r["column_name"] for r in (rows or []) if r["column_name"] != "created_at"]
            if colnames:
                cols = [f'"{c}"' for c in colnames]
                vals = [json.dumps(data.get(c)) if isinstance(data.get(c), (dict, list)) else data.get(c)
                        for c in colnames]
                placeholders = ", ".join(["%s"] * len(cols))
                ok = execute(
                    f'INSERT INTO "{tname}" ({", ".join(cols)}) VALUES ({placeholders})',
                    vals,
                )
                if ok:
                    print(f"[MEMDB] store_custom_memory({schema_name!r}) -> db OK")
                    return {"success": True, "entry": {"id": entry_id, "schema_name": schema_name,
                            "data": data, "created_at": now}}
                print(f"[MEMDB] store_custom_memory({schema_name!r}) -> db FAIL, using fallback")
        except Exception as e:
            print(f"[Supabase] store_custom_memory failed: {e}")

    db = _db()
    if db:
        try:
            db.table("custom_entries").insert({
                "id": entry_id,
                "schema_name": schema_name,
                "data": data,
                "created_at": now,
            }).execute()
        except Exception as e:
            print(f"[Supabase] store_custom_memory failed: {e}")

    path = _get_entries_path(schema_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": entry_id,
        "schema_name": schema_name,
        "data": data,
        "created_at": now,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[MEMDB] store_custom_memory({schema_name!r}) -> FILE fallback (NOT persistent across redeploys)")
    return {"success": True, "entry": entry}


def query_custom_memory(schema_name, query="", limit=20):
    """Query entries from a custom schema by full-text search on data values.
    Empty query returns all recent entries.
    """
    schema_name = schema_name.strip().lower().replace(" ", "_")
    if not schema_name:
        return {"success": False, "error": "schema_name is required"}
    q = query.lower().strip()

    db, fetch, execute = _pg()
    if db:
        try:
            tname = table_name_for(schema_name)
            if q:
                rows = fetch(
                    f'SELECT row_to_json(t) AS data, created_at FROM "{tname}" t '
                    f"WHERE row_to_json(t)::text ILIKE %s ORDER BY created_at DESC LIMIT %s",
                    (f"%{q}%", limit),
                )
            else:
                rows = fetch(
                    f'SELECT row_to_json(t) AS data, created_at FROM "{tname}" t '
                    f"ORDER BY created_at DESC LIMIT %s", (limit,)
                )
            if rows is not None:
                entries = []
                for r in rows:
                    d = r.get("data") or {}
                    if isinstance(d, str):
                        d = json.loads(d)
                    d.pop("created_at", None)
                    entries.append({"id": f"{schema_name}_{r.get('created_at', '')}",
                                    "schema_name": schema_name, "data": d,
                                    "created_at": str(r.get("created_at") or "")})
                return {"success": True, "schema": schema_name, "count": len(entries), "entries": entries}
        except Exception as e:
            print(f"[Supabase] query_custom_memory failed: {e}")

    db = _db()
    if db:
        try:
            if q:
                r = db.table("custom_entries").select("*").eq("schema_name", schema_name).limit(limit).execute()
            else:
                r = db.table("custom_entries").select("*").eq("schema_name", schema_name).limit(limit).execute()
            entries = []
            for row in reversed(r.data or []):
                d = row.get("data", {})
                if q:
                    searchable = json.dumps(d).lower()
                    if q not in searchable:
                        continue
                entries.append({
                    "id": row.get("id", ""),
                    "schema_name": row.get("schema_name", ""),
                    "data": d,
                    "created_at": row.get("created_at", ""),
                })
            return {"success": True, "schema": schema_name, "count": len(entries), "entries": entries}
        except Exception as e:
            print(f"[Supabase] query_custom_memory failed: {e}")

    path = _get_entries_path(schema_name)
    if not path.exists():
        return {"success": True, "schema": schema_name, "count": 0, "entries": []}
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if q:
                    searchable = json.dumps(entry.get("data", {})).lower()
                    if q not in searchable:
                        continue
                entries.append(entry)
    except Exception as e:
        return {"success": False, "error": str(e), "entries": []}
    entries = entries[-limit:]
    return {"success": True, "schema": schema_name, "count": len(entries), "entries": entries}
