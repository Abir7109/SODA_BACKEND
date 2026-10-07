"""
Lightweight performance metrics for the SODA HUD (stdlib sqlite3 only).

Adapted from concepts in open-jarvis/OpenJarvis (Apache-2.0).

Tables:
  tool_runs(name, duration_ms, success, ts) - every dispatch_local_tool call
  turns(first_audio_ms, total_ms, ts)        - voice turn latency (user speech -> first model audio)
  usage(tokens_in, tokens_out, ts)           - Gemini token usage (LiveServerMessage.usage_metadata)

Writes are short synchronous inserts (local WAL sqlite, us-scale); every
record_* call swallows its own errors so metrics can never break a caller.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("projects/metrics.db")

_SCHEMA = (
    "PRAGMA journal_mode=WAL",
    "CREATE TABLE IF NOT EXISTS tool_runs(name TEXT, duration_ms REAL, success INTEGER, ts REAL)",
    "CREATE TABLE IF NOT EXISTS turns(first_audio_ms REAL, total_ms REAL, ts REAL)",
    "CREATE TABLE IF NOT EXISTS usage(tokens_in INTEGER, tokens_out INTEGER, ts REAL)",
)


def _insert(sql, params):
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            for stmt in _SCHEMA:
                conn.execute(stmt)
            with conn:
                conn.execute(sql, params)
        finally:
            conn.close()
    except Exception:
        pass


def record_tool_run(name, duration_ms, success):
    _insert(
        "INSERT INTO tool_runs VALUES (?,?,?,?)",
        (str(name)[:80], round(float(duration_ms), 1), 1 if success else 0, time.time()),
    )


def record_turn(first_audio_ms, total_ms=None):
    _insert("INSERT INTO turns VALUES (?,?,?)", (round(float(first_audio_ms), 1), total_ms, time.time()))


def record_usage(tokens_in, tokens_out):
    _insert("INSERT INTO usage VALUES (?,?,?)", (int(tokens_in), int(tokens_out), time.time()))


def get_summary(hours=1):
    """Aggregate the last `hours` window. Never raises."""
    try:
        hours = max(1, min(int(hours or 1), 720))
    except Exception:
        hours = 1
    cutoff = time.time() - hours * 3600
    tools_row, top, turns_row, usage_row = (0, 0, 0), [], (0, None), (0, 0)
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=5)
        try:
            for stmt in _SCHEMA:
                conn.execute(stmt)
            tools_row = conn.execute(
                "SELECT COUNT(*), AVG(duration_ms), SUM(success) FROM tool_runs WHERE ts >= ?",
                (cutoff,),
            ).fetchone()
            top = conn.execute(
                "SELECT name, COUNT(*), AVG(duration_ms) FROM tool_runs WHERE ts >= ?"
                " GROUP BY name ORDER BY 2 DESC LIMIT 5",
                (cutoff,),
            ).fetchall()
            turns_row = conn.execute(
                "SELECT COUNT(*), AVG(first_audio_ms) FROM turns WHERE ts >= ?", (cutoff,)
            ).fetchone()
            usage_row = conn.execute(
                "SELECT COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0) FROM usage WHERE ts >= ?",
                (cutoff,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        pass
    count = tools_row[0] or 0
    return {
        "window_hours": hours,
        "tools": {
            "count": count,
            "avg_duration_ms": round(tools_row[1] or 0, 1),
            "success_rate": round((tools_row[2] or 0) / count, 3) if count else None,
            "top": [
                {"name": n, "count": c, "avg_duration_ms": round(a or 0, 1)}
                for n, c, a in top
            ],
        },
        "turns": {
            "count": turns_row[0] or 0,
            "avg_first_audio_ms": round(turns_row[1] or 0) if turns_row[0] else None,
        },
        "usage": {"tokens_in": usage_row[0] or 0, "tokens_out": usage_row[1] or 0},
        "generated_at": time.time(),
    }
