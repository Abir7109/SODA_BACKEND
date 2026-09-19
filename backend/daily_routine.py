"""
Daily Routine engine for SODA — Jarvis-style morning / day / night briefings.

Assembles structured briefing payloads from existing data sources:
  - weather (default city Dhaka)
  - today's / tomorrow's schedules
  - reminders
  - unread emails (graceful skip when unconfigured)
  - Bangladesh news headlines
  - memory facts + profile

Also keeps a lightweight daily activity log so day/night recaps can
reference what actually happened today.

Storage: projects/long_term_memory/daily_log.json
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

MEM_DIR = Path("projects/long_term_memory").resolve()
MEM_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = MEM_DIR / "daily_log.json"

DEFAULT_CITY = "Dhaka"


# ── Daily Activity Log ────────────────────────────────────────────

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_log() -> dict:
    if not LOG_PATH.exists():
        return {"date": _today(), "entries": []}
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)
    except Exception:
        log = {}
    if log.get("date") != _today():
        log = {"date": _today(), "entries": []}
    return log


def _save_log(log: dict) -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def log_activity(label: str, tool: str = "") -> None:
    """Record a notable event in today's activity log (for recaps)."""
    if not label or not label.strip():
        return
    log = _load_log()
    log["entries"].append({
        "ts": datetime.now().isoformat(),
        "tool": tool,
        "label": label.strip(),
    })
    _save_log(log)


# Tools whose results are too noisy/verbose to clutter the day recap
_SILENT_TOOLS = {
    "read_file", "list_files", "project_registry", "get_system_status",
    "get_weather", "get_bangladeshi_news", "get_ip_info", "schedule",
    "reminder", "show_calendar", "brief_me_day", "day_recap", "good_night",
    "webview_action", "list_installed_apps",
}

# Human-readable labels for the most common tools
_TOOL_LABELS = {
    "write_file": "Wrote file",
    "edit_file": "Edited file",
    "open_file": "Opened file",
    "execute_command": "Ran command",
    "terminal_execute": "Ran terminal command",
    "run_code": "Ran code",
    "web_search_live": "Searched the web",
    "browse_webpage": "Browsed webpage",
    "open_app": "Opened app",
    "screenshot": "Took a screenshot",
    "email": "Email action",
    "reminder": "Set a reminder",
    "schedule": "Saved a schedule",
    "plan": "Planned tasks",
    "remember_fact": "Saved a fact",
    "analyze_screen": "Analyzed screen",
    "close_window": "Closed window",
}


def log_tool_result(tool: str, success: bool) -> None:
    """Log a tool completion into today's activity log (noise-filtered)."""
    if tool in _SILENT_TOOLS:
        return
    if not success:
        return
    label = _TOOL_LABELS.get(tool, tool.replace("_", " ").capitalize())
    log_activity(label, tool=tool)


def _activity_summary() -> list:
    log = _load_log()
    return [e for e in log.get("entries", [])]


# ── Data Collectors ───────────────────────────────────────────────

async def _get_weather() -> dict:
    try:
        from external_apis import get_weather
        r = await get_weather(DEFAULT_CITY, "celsius")
        if isinstance(r, dict) and "error" not in r and r.get("temperature") is not None:
            return r
    except Exception:
        pass
    return {}


async def _get_news() -> list:
    try:
        from external_apis import get_bangladeshi_news
        r = await get_bangladeshi_news("main")
        articles = r.get("articles", []) if isinstance(r, dict) else []
        return articles[:3]
    except Exception:
        return []


async def _get_emails() -> list:
    try:
        from email_reader import read_emails, email_configured
        if not email_configured():
            return []
        r = await read_emails("UNSEEN", 5)
        if isinstance(r, dict) and r.get("success") and r.get("emails"):
            return r["emails"][:5]
    except Exception:
        pass
    return []


def _get_schedules(day_offset: int = 0) -> list:
    try:
        import schedules
        r = schedules.list_schedules()
        items = r.get("schedules", []) if isinstance(r, dict) else []
        target = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        return [s for s in items if s.get("date") == target]
    except Exception:
        return []


def _get_reminders() -> list:
    try:
        import reminders
        r = reminders.list_reminders()
        items = r.get("reminders", []) if isinstance(r, dict) else []
        out = []
        for it in items:
            if it.get("next_fire") and it.get("seconds_until_fire", 0) >= 0:
                out.append({
                    "id": it.get("id", ""),
                    "message": it.get("message", ""),
                    "seconds_until_fire": it.get("seconds_until_fire", 0),
                })
        out.sort(key=lambda x: x["seconds_until_fire"])
        return out[:5]
    except Exception:
        return []


def _get_memory() -> dict:
    try:
        import user_memory
        summary = user_memory.memory_summary()
        facts = summary.get("recent_facts", []) or []
        profile = summary.get("profile", {}) or {}
        return {
            "name": profile.get("name") or "Sir",
            "facts": [{"key": f.get("key"), "value": f.get("value")} for f in facts[-3:]],
            "fact_count": summary.get("fact_count", 0),
        }
    except Exception:
        return {"name": "Sir", "facts": [], "fact_count": 0}


def _sort_by_time(schedules: list) -> list:
    return sorted(schedules, key=lambda s: s.get("time") or "00:00")


def _human_delta(seconds: int) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"


# ── Briefing Builders ─────────────────────────────────────────────

async def collect_morning_brief() -> dict:
    """Assemble the morning briefing payload."""
    now = datetime.now()
    weather, news, emails, memory = await asyncio.gather(
        _get_weather(), _get_news(), _get_emails(), asyncio.to_thread(_get_memory)
    )
    today_sched = _sort_by_time(_get_schedules(0))
    reminders = _get_reminders()

    sections = [
        {"type": "weather", "title": "WEATHER", "data": weather},
        {"type": "schedule", "title": "TODAY'S SCHEDULE", "data": today_sched},
        {"type": "reminders", "title": "REMINDERS", "data": reminders},
        {"type": "emails", "title": "UNREAD EMAILS", "data": emails},
        {"type": "news", "title": "TOP NEWS", "data": news},
        {"type": "memory", "title": "RECALL", "data": memory},
    ]
    return {
        "phase": "morning",
        "title": "MORNING BRIEF",
        "greeting": f"Good morning, {memory['name']}.",
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "sections": sections,
    }


async def collect_day_recap() -> dict:
    """Assemble the mid-day recap payload."""
    now = datetime.now()
    activity = _activity_summary()
    remaining_sched = _sort_by_time(_get_schedules(0))
    reminders = _get_reminders()

    remaining = []
    for s in remaining_sched:
        st = s.get("time") or "00:00"
        if st >= now.strftime("%H:%M"):
            remaining.append(s)

    sections = [
        {"type": "activity", "title": "SO FAR TODAY", "data": activity},
        {"type": "schedule", "title": "REMAINING TODAY", "data": remaining},
        {"type": "reminders", "title": "PENDING REMINDERS", "data": reminders},
    ]
    return {
        "phase": "day",
        "title": "DAY RECAP",
        "greeting": f"Here's how your day is going, {_get_memory()['name']}.",
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "sections": sections,
    }


async def collect_night_recap() -> dict:
    """Assemble the night wind-down payload."""
    now = datetime.now()
    activity = _activity_summary()
    tomorrow_sched = _sort_by_time(_get_schedules(1))
    reminders = _get_reminders()

    sections = [
        {"type": "activity", "title": "TODAY IN REVIEW", "data": activity},
        {"type": "schedule", "title": "TOMORROW", "data": tomorrow_sched},
        {"type": "reminders", "title": "PENDING REMINDERS", "data": reminders},
    ]
    return {
        "phase": "night",
        "title": "NIGHT RECAP",
        "greeting": f"It's been a full day, {_get_memory()['name']}. Let's wind down.",
        "date": now.strftime("%A, %B %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "sections": sections,
    }


# ── Socket Emit ───────────────────────────────────────────────────

async def emit_brief(sio, payload: dict) -> None:
    """Emit a briefing payload to the HUD frontend."""
    if not sio:
        return
    try:
        await sio.emit("daily_brief", payload)
    except Exception as e:
        print(f"[DAILY_ROUTINE] emit failed: {e}")


async def emit_night_winddown(sio) -> None:
    """Tell the HUD to show the calming wind-down overlay."""
    if not sio:
        return
    try:
        await sio.emit("night_winddown")
    except Exception as e:
        print(f"[DAILY_ROUTINE] night emit failed: {e}")


async def run_briefing(sio, phase: str) -> dict:
    """Run the requested briefing and emit it to the frontend.
    Returns the payload (also used as the spoken summary source)."""
    collectors = {
        "morning": collect_morning_brief,
        "day": collect_day_recap,
        "night": collect_night_recap,
    }
    fn = collectors.get(phase, collect_morning_brief)
    payload = await fn()
    await emit_brief(sio, payload)
    return payload


# ── Auto-Brief Schedule ───────────────────────────────────────────
# (hour, phase, injected instruction shown to Gemini)
AUTO_BRIEFS = [
    (9, "morning", "It's 09:00 — time for the morning briefing. Call brief_me_day now."),
    (13, "day", "It's 13:00 — time for the mid-day recap. Call day_recap now."),
    (22, "night", "It's 22:00 — time to wind down. Call good_night now."),
]


async def daily_brief_loop(sio, audio_loop, interval: int = 30):
    """Background task: fire the daily briefings at their scheduled hours.
    Fires via audio_loop.inject_text() so Gemini sees the instruction and
    calls the matching tool (which emits the panel + speaks)."""
    print("[DAILY_ROUTINE] Auto-brief loop started (09:00 / 13:00 / 22:00)")
    fired_for: dict = {}
    while True:
        try:
            await asyncio.sleep(interval)
            now = datetime.now()
            for hour, phase, instruction in AUTO_BRIEFS:
                if now.hour != hour:
                    continue
                key = f"{phase}:{now.strftime('%Y-%m-%d')}"
                if fired_for.get(key):
                    continue
                fired_for[key] = True
                print(f"[DAILY_ROUTINE] Auto-firing {phase} briefing")
                if audio_loop and hasattr(audio_loop, "inject_text"):
                    await audio_loop.inject_text(instruction)
                elif sio:
                    await sio.emit("status", {"msg": f"[Daily Routine] {phase} briefing due"})
        except asyncio.CancelledError:
            print("[DAILY_ROUTINE] Auto-brief loop stopped")
            raise
        except Exception as e:
            print(f"[DAILY_ROUTINE] Loop error: {e}")
            await asyncio.sleep(interval)
