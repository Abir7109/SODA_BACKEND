# Fix: Supabase Write-Through + Error Logging

## Root Cause
All 3 memory modules (`user_memory.py`, `memory_store.py`, `custom_memory.py`) use the same broken pattern:

**On Write** — When Supabase INSERT/UPDATE succeeds, the function returns immediately WITHOUT writing to the local file fallback. The data exists ONLY in Supabase.

**On Read** — When the Supabase SELECT fails (silently swallowed by `except Exception: pass`), the code falls through to the local file fallback which has NO data (because the write skipped it).

## Fix: Write-Through Caching
Every write function must ALWAYS write to local files regardless of Supabase success/failure. Remove all early returns on Supabase success.

## Fix: Error Logging
Every `except Exception: pass` block must log the error so we can see why Supabase fails.

---

## Changes

### 1. `backend/user_memory.py`

**`_load_profile()`** — Add error logging:
- Line 63: `except Exception: pass` → `except Exception as e: print(f"[Supabase] load_profile failed: {e}")`

**`add_fact()`** — Remove early return, add error logging:
- Lines 132-139: Change from:
  ```python
  if db:
      try:
          db.table("facts").insert({...}).execute()
          return {"success": True, ...}  # ← EARLY RETURN
      except Exception:
          pass
  # file fallback (only reached if Supabase fails)
  ```
  To:
  ```python
  if db:
      try:
          db.table("facts").insert({...}).execute()
      except Exception as e:
          print(f"[Supabase] add_fact failed: {e}")
  # ALWAYS write to file (write-through)
  ```

**`search_facts()`** — Add error logging:
- Line 160: `except Exception: pass` → `except Exception as e: print(f"[Supabase] search_facts failed: {e}")`

**`list_facts()`** — Add error logging:
- Line 198: `except Exception: pass` → `except Exception as e: print(f"[Supabase] list_facts failed: {e}")`

**`delete_fact()`** — Remove early return, add error logging:
- Lines 222-228: Change from:
  ```python
  if db:
      try:
          r = db.table("facts").delete().eq("key", key).execute()
          deleted = len(r.data) if r.data else 0
          return {"success": True, "key": key, "deleted": deleted}  # ← EARLY RETURN
      except Exception:
          pass
  ```
  To:
  ```python
  if db:
      try:
          r = db.table("facts").delete().eq("key", key).execute()
      except Exception as e:
          print(f"[Supabase] delete_fact failed: {e}")
  ```

---

### 2. `backend/memory_store.py`

**`remember_person()`** — Remove early returns, add error logging:
- Lines 56-63: Change from:
  ```python
  if existing.data and len(existing.data) > 0:
      db.table("people").update(payload).eq("id", existing.data[0]["id"]).execute()
      return {"success": True, "name": name, "action": "updated"}  # ← EARLY RETURN
  else:
      payload["created_at"] = now
      db.table("people").insert(payload).execute()
      return {"success": True, "name": name, "action": "created"}  # ← EARLY RETURN
  except Exception:
      pass
  ```
  To:
  ```python
  if existing.data and len(existing.data) > 0:
      db.table("people").update(payload).eq("id", existing.data[0]["id"]).execute()
  else:
      payload["created_at"] = now
      db.table("people").insert(payload).execute()
  except Exception as e:
      print(f"[Supabase] remember_person failed: {e}")
  ```
  Then at the end of the function (file fallback), the final return needs to match the variable name. Currently early returns use `"updated"`/`"created"`. After removing them, the final line `return {"success": True, "name": name, "action": "updated" if found else "created"}` already exists correctly.

**`recall_person()`** — Add error logging:
- Line 124: `except Exception: pass` → `except Exception as e: print(f"[Supabase] recall_person failed: {e}")`

**`recall_by_relationship()`** — Add error logging:
- Line 169: `except Exception: pass` → `except Exception as e: print(f"[Supabase] recall_by_relationship failed: {e}")`

**`list_people()`** — Add error logging:
- Line 211: `except Exception: pass` → `except Exception as e: print(f"[Supabase] list_people failed: {e}")`

**`remember_lesson()`** — Remove early return, add error logging:
- Lines 257-258: Change from:
  ```python
      return {"success": True, "situation": situation, "action": "updated" if existing.data else "created"}
  except Exception:
      pass
  ```
  To:
  ```python
  except Exception as e:
      print(f"[Supabase] remember_lesson failed: {e}")
  ```

**`recall_lessons()`** — Add error logging:
- Line 317: `except Exception: pass` → `except Exception as e: print(f"[Supabase] recall_lessons failed: {e}")`

**`save_summary()`** — Add error logging (already no early return):
- Line 415: `except Exception: pass` → `except Exception as e: print(f"[Supabase] save_summary failed: {e}")`

**`get_recent_summaries()`** — Add error logging:
- Line 458: `except Exception: pass` → `except Exception as e: print(f"[Supabase] get_recent_summaries failed: {e}")`

---

### 3. `backend/custom_memory.py`

**`create_memory_schema()`** — Remove early returns, add error logging:
- Lines 46-62: Change from:
  ```python
  if existing.data and len(existing.data) > 0:
      db.table("custom_schemas").update({...}).eq("id", existing.data[0]["id"]).execute()
      return {"success": True, "action": "updated", "schema": {...}}  # ← EARLY RETURN
  else:
      db.table("custom_schemas").insert({...}).execute()
      return {"success": True, "action": "created", "schema": {...}}  # ← EARLY RETURN
  except Exception:
      pass
  ```
  To:
  ```python
  if existing.data and len(existing.data) > 0:
      db.table("custom_schemas").update({...}).eq("id", existing.data[0]["id"]).execute()
  else:
      db.table("custom_schemas").insert({...}).execute()
  except Exception as e:
      print(f"[Supabase] create_memory_schema failed: {e}")
  ```
  The final `return` line (line 97) already has the correct `"updated" if found else "created"` logic — this becomes the single return path.

**`list_custom_schemas()`** — Add error logging:
- Line 115: `except Exception: pass` → `except Exception as e: print(f"[Supabase] list_custom_schemas failed: {e}")`

**`store_custom_memory()`** — Remove early return, add error logging:
- Lines 154-163: Change from:
  ```python
  if db:
      try:
          db.table("custom_entries").insert({...}).execute()
          return {"success": True, "entry": {...}}  # ← EARLY RETURN
      except Exception:
          pass
  ```
  To:
  ```python
  if db:
      try:
          db.table("custom_entries").insert({...}).execute()
      except Exception as e:
          print(f"[Supabase] store_custom_memory failed: {e}")
  ```

**`query_custom_memory()`** — Add error logging:
- Line 209: `except Exception: pass` → `except Exception as e: print(f"[Supabase] query_custom_memory failed: {e}")`

---

## Testing
1. `python -c "import py_compile; py_compile.compile('backend/user_memory.py', doraise=True); py_compile.compile('backend/memory_store.py', doraise=True); py_compile.compile('backend/custom_memory.py', doraise=True); print('all OK')"`
2. Run backend and test: save a fact, restart session, ask SODA about the fact
