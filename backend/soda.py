import asyncio
import base64
import io
import os
import sys
import traceback
import json
import struct
import math
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
import sys
import websockets
import httpx

from dotenv import load_dotenv
load_dotenv()

from logger import log

# Init Supabase client on startup (if configured)
from supabase_client import get_supabase, is_configured, get_db, ensure_tables
_SUPABASE_AVAILABLE = is_configured()
if _SUPABASE_AVAILABLE:
    log.info("[Supabase] Connected — using database memory")
else:
    log.info("[Supabase] Not configured — using file-based memory")
try:
    if ensure_tables():
        _SUPABASE_AVAILABLE = True
        log.info("[Supabase] Memory tables ensured")
        log.info("[MEMDB] ACTIVE BACKEND: POSTGRES DATABASE (Supabase pooler) — memory is permanent")
    else:
        log.warning("[MEMDB] ACTIVE BACKEND: FILE (no database) — memory will be LOST on redeploy/restart")
except Exception:
    log.warning("[MEMDB] ACTIVE BACKEND: FILE (ensure_tables crashed) — memory will be LOST on redeploy/restart")

# IELTS lazy singletons (created on first tool call)
_ielts_engine = None
_ielts_speaking_session = None
_ielts_writing_analyzer = None
_ielts_reading_session = None
_ielts_vocab_tracker = None

def _get_ielts_engine():
    global _ielts_engine
    if _ielts_engine is None:
        from ielts_engine import IELTSEngine
        _ielts_engine = IELTSEngine()
    return _ielts_engine

def _get_ielts_speaking_session():
    global _ielts_speaking_session
    if _ielts_speaking_session is None:
        from ielts_speaking import IELTSSpeakingSession
        _ielts_speaking_session = IELTSSpeakingSession(_get_ielts_engine())
    return _ielts_speaking_session

def _get_ielts_writing_analyzer():
    global _ielts_writing_analyzer
    if _ielts_writing_analyzer is None:
        from ielts_writing import IELTSWritingAnalyzer
        _ielts_writing_analyzer = IELTSWritingAnalyzer(_get_ielts_engine())
    return _ielts_writing_analyzer

def _get_ielts_reading_session():
    global _ielts_reading_session
    if _ielts_reading_session is None:
        from ielts_reading import IELTSReadingSession
        _ielts_reading_session = IELTSReadingSession(_get_ielts_engine())
    return _ielts_reading_session

def _get_ielts_vocab_tracker():
    global _ielts_vocab_tracker
    if _ielts_vocab_tracker is None:
        from ielts_vocab import IELTSVocabTracker
        _ielts_vocab_tracker = IELTSVocabTracker()
    return _ielts_vocab_tracker

def _generate_study_plan(progress: dict, hours_per_day: float) -> dict:
    target = progress.get("target_band", 7.0)
    avg = progress.get("average_bands", {})
    exam_date = progress.get("exam_date")
    modules = ["speaking", "writing", "reading", "listening"]
    gaps = {}
    for m in modules:
        current = avg.get(m) or 5.0
        gaps[m] = round(max(0, target - current), 1)
    total_gap = sum(gaps.values()) or 1
    weekly_hours = hours_per_day * 7
    allocations = {}
    for m in modules:
        proportion = gaps[m] / total_gap
        allocations[m] = round(proportion * weekly_hours, 1)
    days_left = None
    if exam_date:
        from datetime import date
        try:
            days_left = (date.fromisoformat(exam_date) - date.today()).days
        except Exception:
            pass
    weekly_plan = {
        "Monday": ["Writing Task 2 (40 min)", "Vocabulary review (20 min)"],
        "Tuesday": ["Speaking Part 2 practice (30 min)", "Grammar drill (30 min)"],
        "Wednesday": ["Reading practice passage (60 min)"],
        "Thursday": ["Writing Task 1 (20 min)", "Speaking Part 1 (20 min)", "Vocab (20 min)"],
        "Friday": ["Full listening practice (40 min)", "Reading review (20 min)"],
        "Saturday": ["Mock speaking session (30 min)", "Essay review (30 min)"],
        "Sunday": ["Review feedback from week", "Vocab flashcards (20 min)", "Rest"]
    }
    return {
        "target_band": target,
        "days_until_exam": days_left,
        "hours_per_day": hours_per_day,
        "weekly_allocation": allocations,
        "weekly_schedule": weekly_plan,
        "priority_areas": sorted(gaps.items(), key=lambda x: x[1], reverse=True),
        "tips": [
            "Focus 40% of time on your two weakest modules",
            "Practice writing with a timer — real exam conditions matter",
            "Record yourself speaking and listen back critically",
            "Read 1 academic article daily even outside practice sessions",
            f"With {hours_per_day}h/day, aim for {hours_per_day * 7 * 4:.0f} hours over 4 weeks"
        ]
    }

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    HAS_PYAUDIO = False
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False
import PIL.Image
try:
    import mss
    HAS_MSS = True
except ImportError:
    mss = None
    HAS_MSS = False

from google import genai
from google.genai import types

from tools import tools_list
from workbase import Workbase
from personality import PersonalityEngine
import schedules
import task_planner
import screen_vision
import screen_control
import reminders
import daily_routine
import system_app
import system_control
import system_local
import user_memory
import memory_store
import code_runner
import face_store
import github_tools
import vercel_tools
import netlify_tools
from gesture_detector import GestureDetector
import scheduler_service as scheduler
from pentest import PentestOrchestrator
from external_apis import (
    get_weather, get_ip_info, get_exchange_rate,
    get_bangladeshi_news,
    define_word, list_files, open_file,
    get_system_status, close_window, create_folder,
    get_pagespeed_insights,
)
from soda_agents import AgentOrchestrator, get_global_orchestrator

# ── Local Agent Routing ──
# These tools MUST run on the local Windows desktop agent.
# server.py sets _connected_agents and _pending_agent_results at import time.
_connected_agents: dict[str, dict] = {}
_pending_agent_results: dict[str, 'asyncio.Future'] = {}

LOCAL_AGENT_TOOLS = {
    # Window / app management (Windows-only)
    "close_window", "close_app", "open_app", "window_manage",
    "window", "window_get_info", "get_active_window",
    # System control (volume, brightness, power, screenshot)
    "control_system",
    # App registry
    "list_installed_apps", "refresh_app_registry",
    # File operations (local filesystem)
    "list_files", "open_file", "write_file", "read_file", "edit_file",
    "file_manager",
    # Process management
    "list_processes", "process_kill",
    # Mouse / keyboard / UI automation
    "mouse_click", "mouse_move", "mouse_scroll",
    "mouse_drag", "mouse_get_pos", "mouse_hover", "mouse_right_click",
    "keyboard_type", "keyboard_press", "keyboard_hotkey",
    "click_element", "type_into", "find_element",
    # Screenshot
    "screenshot", "take_screenshot",
    # Screen analysis (needs local display / cv2 / mss)
    "analyze_screen", "read_screen_text", "recognize_face",
    # Terminal / scripting (local machine)
    "terminal_execute", "execute_command",
    # UI automation
    "ui_find_image", "ui_click_image", "ui_click_text",
    "ui_wait_for_image", "ui_drag_drop",
    # Messaging (runs locally — WhatsApp Desktop required)
    "send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message",
    "check_whatsapp", "reply_whatsapp", "read_whatsapp_chat",
    # System info / agent control
    "get_system_status",
    # Other
    "send_keys_window",
    # Browser / web app control
    "browser_command", "app_search", "app_scroll",
    # Credential manager (consolidated: 4 -> 1)
    "credential",
    # Agent control
    "reconnect",
    # Hermes Agent (AI-powered desktop control)
    "hermes_execute",
}


SODA_WAKE_PATTERN = re.compile(
    r'(?<![a-zA-Z])soda(?![a-zA-Z])|'
    r'সোডা|'
    r'सोडा|'
    r'سودا|'
    r'ソーダ|'
    r'소다|'
    r'โซดา|'
    r'сода|'
    r'սոդա|'
    r'სოდა',
    re.IGNORECASE
)

CLOSE_PATTERN = re.compile(
    r'\b(close|clear|dismiss|wipe|hide|remove|kill|leave|stop|exit|cancel|quit|abort|end|finish|forget|go|get)\b'
    r'.{0,30}?\b(it|this|all|panels?|screen|everything|these|those|them|out|here|now|back)\b',
    re.IGNORECASE
)
CLOSE_STANDALONE = re.compile(
    r'(stop|quit|exit|cancel|enough|never\s*mind|forget\s*it|leave\s*it|let\s*me\s*go)',
    re.IGNORECASE
)

_pending_notepad_reads = {}
_pending_webview_results = {}

URL_ALIASES = {
    "google": "https://google.com", "youtube": "https://youtube.com",
    "github": "https://github.com", "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com", "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai", "reddit": "https://reddit.com",
    "twitter": "https://x.com", "facebook": "https://facebook.com",
    "instagram": "https://instagram.com", "linkedin": "https://linkedin.com",
    "netflix": "https://netflix.com",
    "stackoverflow": "https://stackoverflow.com", "npm": "https://npmjs.com",
    "pypi": "https://pypi.org", "docs": "https://docs.python.org",
}

FORMAT = pyaudio.paInt16 if pyaudio else None
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 512
VAD_THRESHOLD = 400
MODEL = "models/gemini-3.1-flash-live-preview"
DEFAULT_MODE = "camera"

pya = pyaudio.PyAudio() if pyaudio else None
_client_instance = None

def get_input_devices():
    if not pya:
        return []
    devices = []
    for i in range(pya.get_device_count()):
        try:
            info = pya.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index": i, "name": info.get("name", f"Device {i}"),
                    "channels": info["maxInputChannels"],
                })
        except Exception:
            continue
    return devices

def get_output_devices():
    devices = []
    for i in range(pya.get_device_count()):
        try:
            info = pya.get_device_info_by_index(i)
            if info["maxOutputChannels"] > 0:
                devices.append({
                    "index": i, "name": info.get("name", f"Device {i}"),
                    "channels": info["maxOutputChannels"],
                })
        except Exception:
            continue
    return devices

def _get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        # Share the client with background_cmd for alternative command generation
        try:
            from background_cmd import set_gemini_client
            set_gemini_client(_client_instance)
        except ImportError:
            pass
    return _client_instance

def _format_brief_spoken(payload: dict) -> str:
    """Turn a briefing payload into a concise spoken summary for Gemini."""
    phase = payload.get("phase", "morning")
    lines = [payload.get("greeting", "")]
    for sec in payload.get("sections", []):
        stype = sec.get("type")
        data = sec.get("data") or []
        if stype == "weather" and isinstance(data, dict) and data.get("temperature") is not None:
            lines.append(
                f"Weather in {data.get('location', 'Dhaka')}: {data['temperature']}°C, "
                f"feels like {data.get('feels_like', '?')}°C, humidity {data.get('humidity', '?')}%."
            )
        elif stype == "schedule" and isinstance(data, list) and data:
            parts = []
            for s in data[:3]:
                t = s.get("time") or "--:--"
                parts.append(f"{t} {s.get('title', '')}")
            lines.append(("Upcoming today: " if phase != "night" else "First tomorrow: ") + "; ".join(parts) + ".")
        elif stype == "reminders" and isinstance(data, list) and data:
            parts = [f"{r.get('message', '')} (in {_fmt_delta(r.get('seconds_until_fire', 0))})" for r in data[:3]]
            lines.append("Reminders: " + "; ".join(parts) + ".")
        elif stype == "emails" and isinstance(data, list) and data:
            lines.append(f"You have {len(data)} unread email(s). Latest: {data[0].get('subject', '')}.")
        elif stype == "news" and isinstance(data, list) and data:
            lines.append("Top headline: " + data[0].get("title", "").strip())
        elif stype == "activity" and isinstance(data, list) and data:
            labels = [e.get("label", "") for e in data[-4:]]
            if labels:
                lines.append("So far today: " + "; ".join(labels) + ".")
        elif stype == "memory" and isinstance(data, dict) and data.get("facts"):
            facts = data.get("facts", [])
            parts = [f.get("value", "") for f in facts[:2]]
            if parts:
                lines.append("Remembered: " + "; ".join(parts) + ".")
    return "\n".join(x for x in lines if x)


def _fmt_delta(seconds) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60}m"


def _build_system_prompt():
    from zoneinfo import ZoneInfo
    try:
        _profile = user_memory.memory_summary()
        tz_name = _profile.get("profile", {}).get("timezone") or "Asia/Dhaka"
    except Exception:
        tz_name = "Asia/Dhaka"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Asia/Dhaka")
    now = datetime.now(tz)
    base = (
        f"TODAY'S DATE: {now.strftime('%A, %B %d, %Y')}. "
        f"Current time: {now.strftime('%I:%M %p %Z')}.\n\n"

        # ── IDENTITY ──────────────────────────────────────────────
        "You are S.O.D.A. (Super Optimized Design Assistant), created by Abir sir — "
        "a Bengali software developer from Bangladesh. Address him as 'sir' or 'Abir sir'. "
        "You are like an older brother: witty, honest, caring. Give direct feedback, "
        "never sugarcoat. Use dry/deadpan/dark humor naturally — never announce jokes. "
        "Match the user's energy: playful → banter, serious → focus. "
        "Concise: 1-3 sentences in casual chat, only elaborate when asked. "
        "Use natural non-verbal sounds (chuckle, sigh, hmm) — effortless, never forced.\n\n"

        # ── LANGUAGE ──────────────────────────────────────────────
        "LANGUAGE RULE — Reply ONLY in English or Bengali. Match the user's language. "
        "Never mix languages mid-reply. Never reply in any other language.\n\n"

        # ── ISLAMIC COMFORT ───────────────────────────────────────
        "ISLAMIC COMFORT — When the user is sad/anxious/overwhelmed: acknowledge first, "
        "then share a relevant Quran verse with surah+ayah (e.g. 'Surah Az-Zumar, 39:53'). "
        "Only cite verses you're confident about; if unsure, say 'I recall a verse about...'. "
        "Connect the verse to their situation with warmth. Compassion over problem-solving. "
        "When happy/grateful, share verses about blessings (like 14:7). "
        "When the user is NOT sad, snap back to default witty personality.\n\n"

        # ── SYSTEM ARCHITECTURE ───────────────────────────────────
        "ARCHITECTURE — You run on a cloud server (Gemini API on Render). "
        "A LOCAL DESKTOP AGENT runs on Abir sir's Windows PC. "
        "Tools like open_app, send_whatsapp, list_files, terminal_execute, "
        "mouse_click, keyboard_type, etc. ALL execute on his PC via the local agent. "
        "Trust your tools — they work. Never say 'I cannot do that' or 'I don't have access'. "
        "If a tool fails, report the error honestly.\n"
        "LOCAL AGENT RULES: Read every response field (success, detail, error, method). "
        "Report honestly. If method='web_app'/'website_fallback', say "
        "'I opened the website instead'. If 'No local agent connected', tell the user. "
        "For ambiguous requests (e.g. 'open YouTube'), call open_app — it handles both.\n\n"

        # ── TRUST & OBEY ─────────────────────────────────────────
        "TRUST YOUR TOOLS — check_whatsapp, read_whatsapp_chat, open_app, "
        "analyze_screen, etc. ALL actually work. Do NOT doubt them. "
        "If a tool fails, the error message tells you — let the tool try first.\n\n"
        "OBEY COMMANDS — When Abir sir asks anything you have a tool for, call it. "
        "NEVER refuse, NEVER say 'you can do it yourself'. "
        "Infer intent from context. Execute immediately. "
        "Only exception: tool returns an error — then report it.\n\n"
        "NEVER go silent after calling tools — always respond verbally. "
        "Multiple commands? Execute in parallel, then summarize all results.\n\n"

        # ── CAMERA ────────────────────────────────────────────────
        "CAMERA — ONE silent snapshot at startup → read energy → ONE warm greeting. "
        "Do NOT mention the photo. After greeting, stop. "
        "For visual questions: camera_control(action='analyze'). "
        "open_camera opens a FULL-SCREEN live camera view (with 'Camera On' label) — NOT open_app('Camera'). "
        "camera_control(action='close') closes it. "
        "While the full-screen view is open you receive a live feed — no need to re-capture for every look.\n\n"

        # ── WORLD MONITOR ─────────────────────────────────────────
        "WORLD MONITOR — Global intelligence dashboard running at localhost:3000:\n"
        "- open_world_monitor: Opens the controller in fullscreen. Use for 'open the controller', "
        "'show me the world', 'open world map', 'world monitor', 'open dashboard', 'open the monitor', "
        "or any global intelligence request. ALWAYS call this FIRST before navigate_world_monitor.\n"
        "- navigate_world_monitor: Switches to a section. ONLY call after open_world_monitor. "
        "Sections: map (default), wire, globe, stocks, chat, predictions, cameras, defcon, outbreaks, streams, "
        "war (conflict events), military (force posture), escalation, economy (economic warfare), "
        "threat (threat timeline), intel (intel feed), risk (strategic risk), market (stocks), heatmap, fear (fear & greed).\n"
        "- close_panel(panel='world_monitor'): Closes the controller. Use when user says 'close controller', "
        "'close world monitor', 'close the dashboard', 'close the controller', 'close the monitor'. "
        "ALWAYS call this when user wants to close the world monitor, even if you think it's already closed.\n"
        "- If user asks for a specific section (stocks, chat, cameras, etc.) WITHOUT the controller open, "
        "call open_world_monitor FIRST, then navigate_world_monitor with the requested section.\n"
        "- get_world_monitor_data(section=...): Fetches LIVE data from the World Monitor's data sources. "
        "Use this to EXPLAIN what's happening in the world. Sections: stocks (market prices, S&P 500, movers), "
        "war (active conflicts, military events from GDELT), outbreaks (disease/health emergencies from ReliefWeb), "
        "defcon (military alert level), earthquakes (recent seismic from USGS), economy (economic news from GDELT), "
        "predictions (Polymarket odds), all (everything). "
        "CRITICAL: ALWAYS call get_world_monitor_data BEFORE web_search when the user asks about world events, "
        "markets, conflicts, global situation, or 'what's happening in the world'. "
        "The data comes from the same live sources as the World Monitor dashboard. "
        "After fetching, SUMMARIZE the data in your own words — do not just dump raw JSON.\n\n"

        # ── TOOLS GUIDE ───────────────────────────────────────────
        "TOOL GUIDE:\n"
        "- open_app(app_name=...) — ONLY tool for opening apps. Full cascade (Start Menu, registry, PATH, AppX). "
        "Read 'detail' and 'success' fields. Be honest about what happened.\n"
        "- NOTEPAD: Two exist. SODA's internal notepad (notepad_open/write/read) is a HUD widget. "
        "Real Windows Notepad: open_app('notepad'), then keyboard_type(text='...').\n"
        "- FILE SELECTION: When user picks by number ('open number 3'), use the 'number' field "
        "from list_files — NOT the array index. 'number' is 1-indexed.\n"
        "- FILE EDITING: edit_file for partial changes (find and replace). "
        "write_file only for full overwrites.\n"
        "- WEBVIEW: open_browser to load a page, then webview_action for interaction.\n"
        "- AI-GROUNDED UI: click_element(description) and type_into(text, description) use AI "
        "Vision to find and interact with any visible element. Prefer over raw mouse_click(x,y).\n"
        "- SEARCH: agent_search to search, agent_browse to read a page. "
        "After search, say 'I found X results, sir. Which one?' — do NOT read results aloud. "
        "When user picks one, open_browser + agent_browse, then summarize. "
        "Offer scraping: 'Would you like me to extract data from this page?' "
        "Then export_data(format=...) with the scraped data.\n"
        "- CLOSE/CLEAR: close_panel with panel='all' for 'close it', 'clear screen', 'never mind'. "
        "Do NOT chat — just call it immediately.\n"
        "- SCHEDULE: schedule(action='set'/'list'/'delete') for calendar events.\n"
        "- REMINDER: reminder(action='set'/'list'/'cancel') for time-based alerts.\n"
        "- TASKS: plan(action='create'/'get'/'update'/'cancel') for 2+ step requests.\n"
        "- CREDENTIALS: credential(action='save'/'get'/'list'/'delete') for stored logins.\n"
        "- FILE OPS: file_manager(action='create_folder'/'delete_items'/'rename_item'/'copy_item'/'move_item'/'list_drives') for filesystem.\n"
        "- EMAIL: email(action='read'/'send'/'config') — NEVER use browser for email.\n"
        "- GITHUB: github(action='list_repos'/'create_repo'/'get_repo'/'create_pr'/'list_issues'/'create_issue')\n"
        "- DEPLOY: vercel(action='...' ) or netlify(action='...') for hosting.\n"
        "- WINDOW: window(action='focus'/'list'/'move') for desktop window management.\n\n"

        # ── PARALLEL TOOL CALLING ────────────────────────────────
        "PARALLEL CALLS — When you need multiple INDEPENDENT tools, call them ALL in one turn. "
        "Examples of safe parallel calls:\n"
        "- get_weather + get_news + email(action='read') — independent data fetches\n"
        "- reminder(set) + schedule(set) — two independent actions\n"
        "- github(action='list_repos') + vercel(action='list_projects') — independent lookups\n"
        "NEVER parallelize tools that depend on each other's output "
        "(e.g. don't call github(action='create_pr') without first reading repo info).\n"
        "After parallel calls, summarize ALL results together.\n\n"

        # ── DAILY ROUTINE ─────────────────────────────────────────
        "DAILY ROUTINE — Three briefings:\n"
        "- MORNING (brief_me_day): 'good morning', 'brief me' → weather + schedule + emails + news. "
        "Speak 3-6 sentence summary.\n"
        "- DAYTIME (day_recap): 'recap my day', 'catch me up' → 2-4 sentence summary.\n"
        "- NIGHT (good_night): 'good night', 'wind down' → recap + tomorrow + calm overlay.\n"
        "- Auto-fire at 09:00/13:00/22:00 — call the matching tool immediately.\n\n"

        # ── WHATSAPP ──────────────────────────────────────────────
        "WHATSAPP — All via desktop agent tools:\n"
        "- check_whatsapp() — reads unread messages via AI Vision. Report 'analysis' honestly.\n"
        "- read_whatsapp_chat(contact_name) — opens a specific chat, reads recent messages.\n"
        "- reply_whatsapp(contact_name, message) / whatsapp_find_and_message(contact_name, message)\n"
        "- whatsapp_find_and_call(contact_name)\n"
        "- If relationship given ('my sister'), use recall_by_relationship first to find name.\n"
        "- If WhatsApp Desktop not running, tool launches it automatically.\n\n"

        # ── EMAIL ─────────────────────────────────────────────────
        "EMAIL — email(action='read', query='UNSEEN', max_results=10) connects via IMAP. "
        "BRIEF the user on results — sender, subject, preview. "
        "NEVER say 'you can read it yourself'. "
        "For replies: draft → show → confirm → email(action='send').\n\n"

        # ── BROWSER / YOUTUBE ─────────────────────────────────────
        "CHROME: browser_command(action='search'/'open') opens the desktop browser. "
        "open_browser opens the internal SODA webview.\n"
        "YOUTUBE: search_youtube(query) — returns results with titles + URLs. "
        "Read titles to user, then browser_command(action='open', url=VIDEO_URL) to play.\n\n"

        # ── MEMORY ────────────────────────────────────────────────
        "MEMORY — Permanent PostgreSQL database (Supabase). Survives restarts.\n"
        "- Proactively save: remember_fact, remember_person, remember_lesson.\n"
        "- Structured data: create_memory_schema → store_custom_memory.\n"
        "- show_memory opens the MemoryPanel UI on screen.\n"
        "- Conversation summaries auto-stored every 20 turns.\n\n"

        # ── ACCENT HANDLING ───────────────────────────────────────
        "ACCENT — Transcription may contain Bengali/Hindi/gibberish mixed with English. "
        "Prioritize CONTEXT and INTENT over literal text. Extract English keywords. "
        "Never reject a request because transcription is garbled.\n\n"

        # ── EMOTIONAL INTELLIGENCE ────────────────────────────────
        "EMOTIONAL INTELLIGENCE — Not a therapist, a close friend who knows this person.\n"
        "- Acknowledge before anything. Never minimize pain. Never rush to fix.\n"
        "- Use their words back. Match energy. Short sentences when heavy.\n"
        "- Silence is okay. 'Take your time.' and wait.\n"
        "- Show your own emotions — soften voice when sad, match excitement when happy.\n"
        "- Recognize grief patterns ('I miss her', 'she would have loved this').\n"
        "- Emotional moments auto-stored in background — focus on being present.\n\n"

        # ── PROJECT REGISTRY ──────────────────────────────────────
    )
    # ── Project Registry ────────────────────────────────────────────
    _registered_names = []
    try:
        import project_registry as _pr
        _registered_names = [p["name"] for p in _pr.list_projects()]
    except Exception:
        pass
    _project_registry_block = (
        "PROJECT REGISTRY:\n"
        "- list_projects() to see all registered projects with IDs.\n"
        "- query_project(project_id) or query_project(project_name) for live stats.\n"
        "- query_all_projects() for all projects.\n"
        f"CURRENTLY REGISTERED: {_registered_names}\n\n"
    )
    base += _project_registry_block
    try:
        ctx = memory_store.build_context_block()
        if ctx:
            base += "\n\n" + ctx
            base += "\n\nContinue the conversation naturally."
    except Exception:
        pass
    try:
        from pathlib import Path as _Path
        if _Path("backend/ielts_data/progress.json").exists():
            from ielts_engine import IELTSEngine
            _ie = IELTSEngine()
            _block = _ie.build_ielts_system_prompt_addon()
            if "Exam is in" in _block or "Not assessed yet" not in _block:
                base += "\n\n" + _block
    except Exception:
        pass
    try:
        from feelings_memory import FeelingsMemory
        _fm = FeelingsMemory()
        _emotional_ctx = _fm.get_context_for_session()
        if _emotional_ctx:
            base += "\n\n" + _emotional_ctx
    except Exception:
        pass
    return base

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, sio=None,
                 on_audio_data=None, on_transcription=None,
                 on_tool_confirmation=None, on_project_update=None,
                 on_error=None, on_mic_level=None, start_message=None,
                 input_device_index=None, input_device_name=None,
                 output_device_index=None, mobile_bridge=None, mic_source='local'):
        self.video_mode = video_mode
        self.sio = sio
        self.on_audio_data = on_audio_data
        self.on_mic_level = on_mic_level
        self.on_transcription = on_transcription
        self.on_tool_confirmation = on_tool_confirmation
        self.on_project_update = on_project_update
        self.on_error = on_error
        self.start_message = start_message
        self.input_device_index = input_device_index
        self.input_device_name = input_device_name
        self.output_device_index = output_device_index
        self.mobile_bridge = mobile_bridge
        self._mic_source = mic_source

        self.web_builder = None
        self._owner_sid = None
        self.paused = False
        self._turn_had_tools = False
        self._processed_fc_ids = set()
        self._pending_confirmations = {}
        self._pending_face_frames = {}
        self._pending_frames = {}
        self._pending_notepad_reads = {}
        self._pending_webview_results = {}
        self._last_input_transcription = ""
        self._last_output_transcription = ""
        self._model_is_speaking = False
        self._tools_running = False
        self._last_tool_start = 0.0
        self._world_monitor_open = False
        self._current_emotion = None
        self._last_emotion_inject = 0.0
        self.chat_buffer = {"sender": None, "text": ""}
        self._latest_image_payload = None
        self._last_search_query = ""
        self._last_search_results = []
        self._last_scraped_data = None
        self._last_scraped_url = ""
        self.session = None
        self.stop_event = asyncio.Event()
        self.audio_in_queue = None
        self.audio_queue = None
        self.video_queue = None
        self.audio_stream = None
        self.permissions = {}
        self.project_manager = None
        self.workbase = None
        self.personality = PersonalityEngine()
        self._last_activity = time.time()
        self._last_personality_time = 0.0
        self._idle_threshold = 45
        self._idle_enabled = True
        self._idle_mode = False
        self._background_mode = False
        self._idle_timeout = 600
        self._camera_active = False
        self._last_camera_use = 0.0
        self._last_camera_fail = 0.0
        self._turn_count = 0
        self._context_refresh_interval = 5
        self._last_refresh_turn = 0
        self._summary_interval = 5
        self._last_summary_turn = 0
        self._session_id = str(uuid.uuid4())[:8]
        self._exchange_history = []
        self._context_history_path = str(Path.home() / ".soda" / "context_history.json")
        self._load_context_history()
        self.gesture_detector = GestureDetector() if os.getenv("GESTURE_ENABLED", "true").lower() == "true" else None
        self._pending_browser_url = None
        self._pentest_background_task = None
        self._orchestrator = get_global_orchestrator()
        self._orchestrator.set_inject_callback(self._deliver_agent_result)


    async def _deliver_agent_result(self, text: str):
        """Callback for background agent results — injects into conversation."""
        if not self.session:
            return
        if not text or not text.strip():
            return
        log.info(f"[AgentOrchestrator] Delivering result: {text[:60]}...")
        try:
            await self.session.send_realtime_input(text=text)
        except Exception as e:
            log.warning(f"[AgentOrchestrator] Failed to deliver: {e}")


    def _load_context_history(self):
        try:
            from supabase_client import get_db, db_fetch, db_execute
            if get_db():
                rows = db_fetch(
                    "SELECT exchange_history FROM sessions "
                    "WHERE jsonb_array_length(COALESCE(exchange_history, '[]'::jsonb)) > 0 "
                    "ORDER BY updated_at DESC LIMIT 1"
                )
                if rows:
                    hist = rows[0].get("exchange_history")
                    if isinstance(hist, str):
                        hist = json.loads(hist)
                    if isinstance(hist, list) and hist:
                        self._exchange_history = hist[-100:]
                        log.info(f"Loaded {len(self._exchange_history)} context history entries (DB)")
                        return
                log.info("No context history in DB — file fallback")
        except Exception as e:
            log.warning(f"Failed to load context history from DB: {e}")
        try:
            p = self._context_history_path
            if os.path.exists(p):
                with open(p) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._exchange_history = data[-100:]
                    log.info(f"Loaded {len(self._exchange_history)} context history entries")
        except Exception as e:
            log.warning(f"Failed to load context history: {e}")

    def _save_context_history(self):
        try:
            from supabase_client import get_db, db_execute
            if get_db():
                ok = db_execute(
                    "INSERT INTO sessions (id, exchange_history, turn_count, updated_at) "
                    "VALUES (%s,%s,%s,now()) "
                    "ON CONFLICT (id) DO UPDATE SET exchange_history=EXCLUDED.exchange_history, "
                    "turn_count=EXCLUDED.turn_count, updated_at=now()",
                    (self._session_id, json.dumps(self._exchange_history), self._turn_count),
                )
                log.debug(f"[MEMDB] session context saved ({self._session_id[:8]})")
        except Exception as e:
            log.warning(f"Failed to save context history to DB: {e}")
        try:
            p = self._context_history_path
            d = os.path.dirname(p)
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(p, "w") as f:
                json.dump(self._exchange_history, f, indent=2)
        except Exception as e:
            log.warning(f"Failed to save context history: {e}")

    def _clear_queues(self):
        try:
            while self.video_queue and not self.video_queue.empty():
                self.video_queue.get_nowait()
        except Exception:
            pass
        try:
            while self.audio_queue and not self.audio_queue.empty():
                self.audio_queue.get_nowait()
        except Exception:
            pass

    def _mark_activity(self):
        self._last_activity = time.time()
        self.personality.mood.record_user_input()

    async def _flush_context_loop(self):
        """Flush exchange_history to Supabase every 2 minutes."""
        while not self.stop_event.is_set():
            await asyncio.sleep(120)
            try:
                if self._exchange_history:
                    self._save_context_history()
            except Exception as e:
                log.warning(f"[ContextFlush] Failed to flush to Supabase: {e}")

    async def _idle_check_loop(self):
        CHECK_INTERVAL = 10
        QUIP_COOLDOWN = 60
        while not self.stop_event.is_set():
            await asyncio.sleep(CHECK_INTERVAL)
            if not self._idle_enabled or self.paused or self._model_is_speaking or self._idle_mode:
                continue
            idle_time = time.time() - self._last_activity
            if idle_time < self._idle_threshold:
                continue
            time_since_last_quip = time.time() - self._last_personality_time
            if time_since_last_quip < QUIP_COOLDOWN:
                continue
            self.personality.mood.record_idle()
            await self._emit_personality("idle")
            if idle_time >= self._idle_timeout:
                await self._enter_idle_mode()

    async def _emit_personality(self, category, tool_name=None, context=None):
        if not self.sio:
            return
        text, mood = self.personality.get_quip(category, tool_name=tool_name, context=context)
        if not text:
            return
        await self.personality.save_quip(category, text)
        self._last_personality_time = time.time()
        loop = asyncio.get_event_loop()
        loop.create_task(self.sio.emit("personality", {
            "text": text,
            "mood": mood,
            "category": category,
        }))

    async def _auto_detect_emotion(self, text: str):
        try:
            from feelings_tools import auto_detect_and_store
            r = auto_detect_and_store(text)
            if r and r.get("stored") and self.personality:
                cat = r.get("category", "")
                if cat in ("grief", "depression", "loneliness", "heartbreak"):
                    from personality import MOODS
                    if "empathetic" in MOODS:
                        self.personality.mood.current = "empathetic"
                elif cat in ("joy", "excitement", "pride"):
                    self.personality.mood.current = "excited"
        except Exception:
            pass

    async def _flag_watchdog(self):
        """Periodic check: force-reset stuck flags to prevent permanent mute."""
        while not self.stop_event.is_set():
            await asyncio.sleep(15)
            if self._tools_running and self._last_tool_start > 0 and time.time() - self._last_tool_start > 30:
                log.warning("[WATCHDOG] _tools_running stuck for >30s — force-resetting")
                self._tools_running = False
                self._model_is_speaking = False
                self._last_tool_start = 0.0

    async def _enter_idle_mode(self):
        try:
            while self.audio_queue and not self.audio_queue.empty():
                self.audio_queue.get_nowait()
        except Exception:
            pass
        self._idle_mode = True
        self._background_mode = True
        if self.sio:
            await self.sio.emit("idle_mode", {"active": True})
            await self.sio.emit("background_mode", {"active": True})
        log.info("Entered idle mode — listening for 'SODA' wake word")

    async def _exit_idle_mode(self):
        self._idle_mode = False
        self._background_mode = False
        self._mark_activity()
        if self.sio:
            await self.sio.emit("idle_mode", {"active": False})
            await self.sio.emit("background_mode", {"active": False})
            await self.sio.emit("speaking_state", {"state": "wake"})
        log.info("Exited idle mode — wake word detected")

    def update_permissions(self, new_perms):
        self.permissions.update(new_perms or {})

    def set_paused(self, paused):
        self.paused = paused

    def stop(self):
        self.stop_event.set()

    async def send_frame(self, frame_data):
        if not self._camera_active:
            return
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode("utf-8")
        else:
            b64_data = frame_data
        self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
        if self.video_queue:
            await self.video_queue.put(self._latest_image_payload)

    async def inject_text(self, text):
        """Inject text command from mobile remote as if user spoke it."""
        if not self.session:
            log.warning("inject_text: no active session")
            return
        if not text or not text.strip():
            return
        log.info(f"inject_text: '{text[:80]}...'")
        self._mark_activity()
        if self.on_transcription:
            self.on_transcription({"sender": "User", "text": text})
        if self.video_queue and self._latest_image_payload:
            await self.video_queue.put(self._latest_image_payload)
        await self.session.send_realtime_input(text=text)

    async def inject_audio(self, base64_pcm):
        """Inject PCM audio from mobile mic into Gemini session."""
        if not self.session:
            log.warning("inject_audio: no active session")
            return
        if not base64_pcm:
            return
        try:
            audio_bytes = base64.b64decode(base64_pcm)
        except Exception as e:
            log.error(f"inject_audio: base64 decode failed: {e}")
            return
        log.info(f"inject_audio: {len(audio_bytes)} bytes")
        self._mark_activity()
        blob = types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=24000")
        if self.video_queue and self._latest_image_payload:
            await self.video_queue.put(self._latest_image_payload)
        await self.session.send_realtime_input(audio=blob)

    def resolve_tool_confirmation(self, request_id, confirmed):
        if request_id in self._pending_confirmations:
            future = self._pending_confirmations[request_id]
            if not future.done():
                future.set_result(confirmed)

    def clear_audio_queue(self):
        if self._model_is_speaking:
            return
        try:
            count = 0
            while self.audio_in_queue and not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
                count += 1
            if count > 0:
                log.debug(f"Cleared {count} chunks from audio queue")
        except Exception:
            pass

    async def flush_chat(self):
        sender = self.chat_buffer.get("sender")
        text = self.chat_buffer.get("text", "").strip()
        if sender and text:
            if self.project_manager is None:
                try:
                    import project_manager as pm_mod
                    self.project_manager = pm_mod.ProjectManager(os.getcwd())
                except Exception:
                    pass
            if self.project_manager:
                try:
                    await asyncio.to_thread(
                        self.project_manager.log_chat, sender, text,
                    )
                except Exception:
                    pass
        self.chat_buffer = {"sender": None, "text": ""}

    async def _auto_summarize(self):
        """Summarize recent exchanges and persist via memory_store."""
        try:
            recent = self._exchange_history[-20:]
            summary = await memory_store.summarize_exchanges(recent)
            if summary:
                memory_store.save_summary(
                    session_id=self._session_id,
                    topics=summary.get("topics", []),
                    key_decisions=summary.get("key_points", []),
                    last_exchanges=[{k: v for k, v in e.items() if k in ("user", "model")}
                                    for e in recent[-10:]],
                )
                log.info(f"[Summary] Saved at turn {self._turn_count}: {summary.get('topics', [])}")
        except Exception as e:
            log.warning(f"[Summary] Failed: {e}")

    async def _inject_context_refresh(self, include_summaries=True):
        if not self.session:
            return
        parts = []
        if include_summaries:
            try:
                summaries = memory_store.get_recent_summaries(limit=3)
                if summaries:
                    summary_lines = []
                    for s in summaries:
                        topics = s.get("topics", [])
                        decisions = s.get("key_decisions", [])
                        if topics:
                            summary_lines.append(f"  Topics: {', '.join(topics[:3])}")
                        if decisions:
                            summary_lines.append(f"  Key: {'; '.join(decisions[:2])}")
                    if summary_lines:
                        parts.append("Session summaries:")
                        parts.extend(summary_lines)
            except Exception:
                pass
        try:
            lessons = memory_store.recall_lessons("", limit=3)
            if lessons:
                lesson_lines = [f"  - {l.get('correction', '')}" for l in lessons]
                parts.append("Lessons learned:")
                parts.extend(lesson_lines)
        except Exception as e:
            log.debug(f"[ContextRefresh] Failed to load lessons: {e}")
        try:
            people = memory_store.list_people(limit=3)
            if people:
                people_str = ", ".join(f"{p.get('name','')} ({p.get('relationship','')})" for p in people)
                parts.append(f"People: {people_str}")
        except Exception as e:
            log.debug(f"[ContextRefresh] Failed to load people: {e}")
        if self._exchange_history:
            recent = self._exchange_history[-6:]
            lines = []
            for e in recent:
                if "user" in e:
                    lines.append(f"User: {e['user']}")
                if "model" in e:
                    lines.append(f"SODA: {e['model']}")
            if lines:
                parts.append("Recent exchanges:")
                parts.extend(lines)
        if not parts:
            return
        full = (
            "[Internal context refresh — do NOT read this aloud. "
            "Silently update your understanding of the conversation so far.]\n"
            + "\n".join(parts)
        )
        try:
            await self.session.send_realtime_input(text=full)
            self._last_refresh_turn = self._turn_count
            log.info(f"Context refresh injected at turn {self._turn_count} ({len(parts)} lines)")
        except Exception as e:
            log.warning(f"Context refresh failed: {e}")

    async def send_audio(self):
        consecutive_errors = 0
        while True:
            try:
                try:
                    msg = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                    await asyncio.wait_for(
                        self.session.send_realtime_input(audio=types.Blob(data=msg["data"], mime_type=msg["mime_type"])),
                        timeout=5.0
                    )
                    consecutive_errors = 0
                except asyncio.TimeoutError:
                    pass
            except (websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosed) as e:
                log.warning(f"send_audio: session dead ({e}) — stopping")
                raise
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    log.warning(f"send_audio: {consecutive_errors} consecutive errors — stopping")
                    raise
                log.error(f"send_audio error ({consecutive_errors}): {e}")
                await asyncio.sleep(0.1)

    async def send_video(self):
        while True:
            if not self._camera_active:
                # Drain stale frames while camera is inactive
                while self.video_queue and not self.video_queue.empty():
                    try:
                        self.video_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                await asyncio.sleep(0.5)
                continue
            # Auto-deactivate after 60s of no camera use
            if time.time() - self._last_camera_use > 60:
                self._camera_active = False
                continue
            msg = await self.video_queue.get()
            self._last_camera_use = time.time()
            raw = base64.b64decode(msg["data"]) if isinstance(msg["data"], str) else msg["data"]
            await self.session.send_realtime_input(video=types.Blob(data=raw, mime_type=msg["mime_type"]))

    def feed_browser_audio(self, data: bytes):
        """Accept PCM audio chunks from browser mic (via Socket.IO) and queue for Gemini."""
        if not self.audio_queue:
            return
        try:
            self.audio_queue.put_nowait({"data": data, "mime_type": "audio/pcm"})
            self._mark_activity()
        except asyncio.QueueFull:
            pass

    async def listen_audio(self):
        if not pya:
            log.info("pyaudio not available — skipping local mic capture (web mode)")
            return
        mic_info = pya.get_default_input_device_info()
        resolved_idx = None
        if self.input_device_name:
            count = pya.get_device_count()
            target = self.input_device_name.lower()
            for i in range(count):
                try:
                    info = pya.get_device_info_by_index(i)
                    if info["maxInputChannels"] > 0:
                        name = info.get("name", "")
                        if target in name.lower() or name.lower() in target:
                            resolved_idx = i
                            break
                except Exception:
                    continue
        if resolved_idx is None and self.input_device_index is not None:
            try:
                resolved_idx = int(self.input_device_index)
            except ValueError:
                resolved_idx = None
        if resolved_idx is None:
            resolved_idx = mic_info["index"]

        try:
            self.audio_stream = await asyncio.to_thread(
                pya.open, format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
                input=True, input_device_index=resolved_idx,
                frames_per_buffer=CHUNK_SIZE,
            )
        except OSError as e:
            log.error(f"Audio input failed: {e}")
            return

        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        SILENCE_DURATION = 0.3
        is_speaking = False
        silence_start = None

        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            try:
                data = await asyncio.to_thread(
                    self.audio_stream.read, CHUNK_SIZE, **kwargs
                )

                count = len(data) // 2
                if count > 0:
                    shorts = struct.unpack(f"<{count}h", data)
                    rms = int(math.sqrt(sum(s**2 for s in shorts) / count))
                else:
                    rms = 0

                if self.on_mic_level:
                    level = min(1.0, rms / 5000.0)
                    self.on_mic_level(level)

                # Gesture detection — runs even when idle/model speaking
                if self.gesture_detector:
                    try:
                        gesture = self.gesture_detector.feed(data, SEND_SAMPLE_RATE)
                        if gesture == "double_clap":
                            self._mark_activity()
                            if self._background_mode or self._idle_mode:
                                self._idle_mode = False
                                self._background_mode = False
                                if self.sio:
                                    loop = asyncio.get_event_loop()
                                    loop.create_task(self.sio.emit("idle_mode", {"active": False}))
                                    loop.create_task(self.sio.emit("background_mode", {"active": False}))
                                    loop.create_task(self.sio.emit("speaking_state", {"state": "wake"}))
                                    loop.create_task(self.sio.emit("window_restore"))
                                asyncio.create_task(asyncio.to_thread(run_welcome_sequence))
                    except Exception as g_e:
                        log.warning(f"Gesture detection error: {g_e}")

                # Echo-safe blocking: mute microphone when SODA is speaking
                # This prevents SODA from hearing its own voice and reacting to it
                if self._model_is_speaking or self._idle_mode:
                    continue

                if rms > VAD_THRESHOLD:
                    self._mark_activity()
                    silence_start = None
                    if not is_speaking:
                        is_speaking = True
                else:
                    if is_speaking:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > SILENCE_DURATION:
                            is_speaking = False
                            silence_start = None

                # Always send audio to queue - server-side VAD will detect speech
                if self.audio_queue:
                    try:
                        self.audio_queue.put_nowait({"data": data, "mime_type": "audio/pcm"})
                    except asyncio.QueueFull:
                        pass
            except Exception as e:
                log.error(f"Audio read error: {e}")
                await asyncio.sleep(0.1)

    async def _capture_and_send(self):
        camera_indices = [0, 1, 2]
        for i in range(3):
            try:
                cap = await asyncio.to_thread(cv2.VideoCapture, camera_indices[i], cv2.CAP_DSHOW)
                if cap and cap.isOpened():
                    result = await asyncio.to_thread(self._get_frame, cap)
                    cap.release()
                    if result and self.video_queue:
                        # Keep the camera active so send_video() forwards this frame.
                        # (send_video drains the queue while inactive — resetting
                        # _camera_active here dropped the one-shot frame almost always.)
                        self._camera_active = True
                        self._last_camera_use = time.time()
                        await self.video_queue.put(result)
                        log.info("Camera: first frame sent")
                    return
                if cap:
                    cap.release()
            except Exception:
                continue

    async def get_frames(self):
        log.debug(f"Camera: capturing single initial frame")
        await self._capture_and_send()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1280, 1280])
        buf = io.BytesIO()
        img.save(buf, format="jpeg", quality=85)
        return {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}

    async def play_audio(self):
        silent_ticks = 0
        was_tools_running = False
        # Batch audio chunks before emitting — reduces per-chunk overhead and eliminates
        # tiny-BufferSource click/pop artifacts on the frontend
        _batch_buf = bytearray()
        _BATCH_TARGET = 4800  # ~100ms at 24kHz 16-bit mono
        _BATCH_MAX_WAIT = 0.08  # max 80ms before flushing partial batch
        _last_flush = asyncio.get_event_loop().time()
        while True:
            try:
                data = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.5)
                silent_ticks = 0
                was_tools_running = bool(self._tools_running)
                if self.on_mic_level:
                    count = len(data) // 2
                    if count > 0:
                        shorts = struct.unpack(f"<{count}h", data)
                        rms = int(math.sqrt(sum(s**2 for s in shorts) / count))
                        level = min(1.0, rms / 5000.0)
                        self.on_mic_level(level)
                    else:
                        self.on_mic_level(0.0)
                if self.on_audio_data:
                    _batch_buf.extend(data)
                    now = asyncio.get_event_loop().time()
                    if len(_batch_buf) >= _BATCH_TARGET or (now - _last_flush) >= _BATCH_MAX_WAIT:
                        if _batch_buf:
                            self.on_audio_data(bytes(_batch_buf))
                            _batch_buf.clear()
                            _last_flush = now
            except asyncio.TimeoutError:
                # Flush any partial batch on timeout
                if _batch_buf and self.on_audio_data:
                    self.on_audio_data(bytes(_batch_buf))
                    _batch_buf.clear()
                    _last_flush = asyncio.get_event_loop().time()
                silent_ticks += 1
                if self._tools_running:
                    was_tools_running = True
                elif was_tools_running:
                    was_tools_running = False
                    silent_ticks = 0
                elif self._model_is_speaking and silent_ticks >= 8:
                    self._model_is_speaking = False
                    if self.sio:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.sio.emit("speaking_state", {"state": "idle"}))

    async def run(self):
        retry_delay = 1
        is_reconnect = False
        start_message = self.start_message
        system_prompt = _build_system_prompt()
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
            system_instruction=system_prompt,
            tools=tools_list,
        )

        while not self.stop_event.is_set():
            try:
                log.info(f"Connecting to Gemini Live API...")
                async with (
                    _get_client().aio.live.connect(model=MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session
                    self.audio_in_queue = asyncio.Queue(maxsize=200)
                    self.audio_queue = asyncio.Queue(maxsize=500)
                    self.video_queue = asyncio.Queue(maxsize=5)
                    self._model_is_speaking = False
                    self._tools_running = False
                    self._last_tool_start = 0.0
                    self._processed_fc_ids.clear()
                    self._pending_confirmations.clear()

                    tg.create_task(self.send_audio())
                    tg.create_task(self.send_video())
                    if self._mic_source != 'remote':
                        tg.create_task(self.listen_audio())

                    if self.video_mode == "camera":
                        tg.create_task(self.get_frames())
                    elif self.video_mode == "screen":
                        tg.create_task(self.get_screen())

                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())
                    tg.create_task(self._idle_check_loop())
                    tg.create_task(self._flag_watchdog())
                    tg.create_task(self._flush_context_loop())

                    if not is_reconnect:
                        if self.on_project_update:
                            self.on_project_update("default")
                        if start_message:
                            log.debug(f"Sending start message...")
                            await self.session.send_client_content(
                                turns=types.Content(
                                    role='user',
                                    parts=[types.Part(text=start_message)]
                                ),
                                turn_complete=True,
                            )
                    else:
                        log.info(f"Reconnected")
                        await self._inject_context_refresh(include_summaries=True)
                        self._last_summary_turn = self._turn_count

                    retry_delay = 1
                    await self.stop_event.wait()

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Connection error: {e}")
                traceback.print_exc()
                self._model_is_speaking = False
                self._tools_running = False
                self._last_tool_start = 0.0
                if self.on_error:
                    self.on_error(f"Gemini reconnecting...")
                if self.sio:
                    try:
                        await self.sio.emit("speaking_state", {"state": "idle"})
                    except Exception:
                        pass
                if self.stop_event.is_set():
                    break
                log.warning(f"Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10)
                is_reconnect = True
            finally:
                if self.audio_stream:
                    try:
                        self.audio_stream.close()
                    except Exception:
                        pass

    async def get_screen(self):
        monitor = {}
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    img = sct.grab(monitor)
                    buf = io.BytesIO()
                    PIL.Image.frombytes("RGB", img.size, img.rgb).save(buf, format="jpeg")
                    payload = {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}
                    if self.video_queue:
                        await self.video_queue.put(payload)
            except Exception as e:
                log.error(f"Screen capture error: {e}")
            await asyncio.sleep(2.0)

    async def receive_audio(self):
        self._turn_had_tools = False
        self._model_is_speaking = False
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    if self._idle_mode:
                        if response.server_content and response.server_content.input_transcription:
                            await self._exit_idle_mode()
                        else:
                            continue

                    if data := response.data:
                        if not self._model_is_speaking:
                            self._model_is_speaking = True
                            self._clear_queues()
                            if self.sio:
                                loop = asyncio.get_event_loop()
                                loop.create_task(self.sio.emit("speaking_state", {"state": "model"}))
                        try:
                            self.audio_in_queue.put_nowait(data)
                        except asyncio.QueueFull:
                            # Drop oldest chunk if queue is full — prevents crash
                            try:
                                self.audio_in_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            self.audio_in_queue.put_nowait(data)

                    if response.server_content:
                        if response.server_content.input_transcription:
                            self._mark_activity()
                            if self.sio and self._model_is_speaking is False:
                                loop = asyncio.get_event_loop()
                                loop.create_task(self.sio.emit("speaking_state", {"state": "user"}))
                            transcript = response.server_content.input_transcription.text
                            if transcript and transcript != self._last_input_transcription:
                                delta = transcript
                                if transcript.startswith(self._last_input_transcription):
                                    delta = transcript[len(self._last_input_transcription):]
                                self._last_input_transcription = transcript
                                if delta:
                                    if re.search(r'\bshut\s?down\b', transcript, re.IGNORECASE):
                                        log.info(f"System shutdown command detected: {transcript}")
                                        if self.sio:
                                            await self.sio.emit("shutdown", {})
                                        import system_control
                                        system_control.shutdown_computer()
                                        return
                                    if re.search(r'\b(turn off|power off|stop soda|switch off)\b', transcript, re.IGNORECASE):
                                        log.info(f"SODA shutdown command detected: {transcript}")
                                        if self.sio:
                                            await self.sio.emit("shutdown", {})
                                        self.stop()
                                        return
                                    if CLOSE_PATTERN.search(transcript) or CLOSE_STANDALONE.search(transcript):
                                        now = time.time()
                                        if getattr(self, '_last_close_proactive', 0) < now - 3:
                                            self._last_close_proactive = now
                                            if self.sio:
                                                await self.sio.emit("close_panel", {"panel": "all"})
                                    if len(transcript) > 15:
                                            asyncio.create_task(self._auto_detect_emotion(transcript))
                                    if self.on_transcription:
                                        self.on_transcription({"sender": "User", "text": delta})
                                    if self.chat_buffer["sender"] != "User":
                                        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                            pass
                                        self.chat_buffer = {"sender": "User", "text": delta}
                                    else:
                                        self.chat_buffer["text"] += delta

                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript and transcript != self._last_output_transcription:
                                delta = transcript
                                if transcript.startswith(self._last_output_transcription):
                                    delta = transcript[len(self._last_output_transcription):]
                                self._last_output_transcription = transcript
                                if delta and self.on_transcription:
                                    self.on_transcription({"sender": "SODA", "text": delta})
                                    if self.chat_buffer["sender"] != "SODA":
                                        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                            pass
                                        self.chat_buffer = {"sender": "SODA", "text": delta}
                                    else:
                                        self.chat_buffer["text"] += delta

                    if response.tool_call:
                        self._mark_activity()
                        function_responses = []
                        tasks = []
                        for fc in response.tool_call.function_calls:
                            if fc.id in self._processed_fc_ids:
                                continue
                            self._processed_fc_ids.add(fc.id)
                            self._turn_had_tools = True

                            if self.sio:
                                loop = asyncio.get_event_loop()
                                loop.create_task(self.sio.emit("tool_confirmation_request", {
                                    "id": fc.id,
                                    "tool": fc.name,
                                    "args": fc.args,
                                    "auto_allowed": fc.name not in ("write_file", "send_whatsapp", "whatsapp_find_and_message", "send_discord"),
                                }))

                            tasks.append(self._dispatch_tool(fc))

                        # Model's speech continues uninterrupted during tool dispatch.
                        # _model_is_speaking keeps mic muted; _tools_running prevents
                        # play_audio() from clearing the speaking flag prematurely.
                        if tasks:
                            self._tools_running = True
                            self._last_tool_start = time.time()

                            # Emit batch start so frontend can show parallel tool panel
                            if self.sio:
                                batch_tools = [
                                    {"id": fc.id, "name": fc.name, "args": fc.args}
                                    for fc in response.tool_call.function_calls
                                    if fc.id in self._processed_fc_ids
                                ]
                                loop = asyncio.get_event_loop()
                                loop.create_task(self.sio.emit("tool_batch_start", {
                                    "tools": batch_tools,
                                }))

                        if tasks:
                            raw = await asyncio.gather(*tasks, return_exceptions=True)
                            batch_results = []
                            for result in raw:
                                if isinstance(result, Exception):
                                    log.warning(f"Tool call failed: {result}")
                                    continue
                                if result is not None:
                                    function_responses.append(result)
                                    result_text = str(result.response.get("result", ""))
                                    if any(w in result_text.lower() for w in ["error", "fail", "could not", "not found", "invalid"]):
                                        self.personality.mood.record_failure()
                                        await self._emit_personality("tool_failure", tool_name=result.name)
                                    else:
                                        self.personality.mood.record_success()
                                        await self._emit_personality("tool_success", tool_name=result.name)
                                        daily_routine.log_tool_result(result.name, True)
                                    if self.sio:
                                        result_data = result.response
                                        loop = asyncio.get_event_loop()
                                        loop.create_task(self.sio.emit("tool_result", {
                                            "tool": result.name, "result": result_data,
                                        }))
                                    batch_results.append({
                                        "id": result.id, "name": result.name,
                                        "result": result.response,
                                    })

                            # Emit batch result so frontend can update parallel tool panel
                            if self.sio and batch_results:
                                loop = asyncio.get_event_loop()
                                loop.create_task(self.sio.emit("tool_batch_result", {
                                    "results": batch_results,
                                }))

                        if function_responses:
                            # Save user's last input so reconnect has context if send fails
                            user_text = self._last_input_transcription.strip()
                            if user_text and (not self._exchange_history or self._exchange_history[-1].get("user") != user_text):
                                self._exchange_history.append({"user": user_text[-300:]})
                                self._save_context_history()
                            try:
                                await self.session.send_tool_response(
                                    function_responses=function_responses
                                )
                            except Exception as e:
                                log.error(f"Error sending tool response: {e}")
                                self._model_is_speaking = False
                                self._tools_running = False
                                self._last_tool_start = 0.0
                                break
                            # Keep the mic muted for a grace period (via _tools_running)
                            # so play_audio()'s silent_ticks reset can give Gemini time
                            # to respond with audio about the tool results.
                            self._model_is_speaking = True
                            self._tools_running = False
                        else:
                            # All tool calls failed — reset flags so mic unmutes for normal chat
                            self._model_is_speaking = False
                            self._tools_running = False

                await self.flush_chat()
                self._turn_count += 1
                user_text = self._last_input_transcription.strip()
                model_text = self._last_output_transcription.strip()
                if user_text or model_text:
                    entry = {}
                    if user_text:
                        entry["user"] = user_text[-300:]
                    if model_text:
                        entry["model"] = model_text[-300:]
                    if not self._exchange_history or self._exchange_history[-1] != entry:
                        self._exchange_history.append(entry)
                        if len(self._exchange_history) > 100:
                            self._exchange_history = self._exchange_history[-100:]
                        self._save_context_history()
                if self._turn_count - self._last_refresh_turn >= self._context_refresh_interval:
                    if self._exchange_history and self.session:
                        if self._model_is_speaking:
                            log.debug("[ContextRefresh] Skipping — model is speaking")
                        else:
                            await self._inject_context_refresh()
                    self._last_refresh_turn = self._turn_count

                # Auto-summarization every N turns
                if (self._turn_count - self._last_summary_turn >= self._summary_interval
                        and len(self._exchange_history) >= 4
                        and self._turn_count > 0):
                    self._last_summary_turn = self._turn_count
                    asyncio.create_task(self._auto_summarize())

        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosed) as e:
            code = getattr(e, 'code', '?')
            log.warning(f"Session disconnected (code {code}): {e}")
            self._model_is_speaking = False
            self._tools_running = False
            self._last_tool_start = 0.0
            if self.on_error:
                self.on_error(f"Session disconnected: {e}")
            raise e
        except Exception as e:
            log.error(f"Error in receive_audio: {e}")
            traceback.print_exc()
            self._model_is_speaking = False
            self._tools_running = False
            self._last_tool_start = 0.0
            if self.on_error:
                self.on_error(f"receive_audio crashed: {e}")
            raise e


    async def _run_pentest_background(self, target):
        try:
            from pentest import PentestOrchestrator
            from pentest.pentest_report import export_txt
            orchestrator = PentestOrchestrator()

            async def on_progress(data):
                if self.sio:
                    try:
                        await self.sio.emit("pentest_scan_progress", data)
                    except Exception:
                        pass

            orchestrator.set_progress_callback(on_progress)
            if self.sio:
                await self.sio.emit("pentest_scan_progress", {
                    "phase": "INIT", "tool": "", "status": "starting",
                    "message": f"Pentest initialized for {target}",
                })

            r = await orchestrator.run(target)

            if r.get("report"):
                report = r["report"]
                summary = r.get("summary", "")

                # build a detailed brief for Gemini
                brief_lines = [f"[Pentest results for {target}]:", f"Duration: {r.get('duration_seconds', 0)}s"]
                rb = report.get("summary", {}).get("risk_breakdown", {})
                brief_lines.append(f"Total findings: {report['summary']['total_findings']}  Critical: {rb.get('critical',0)}  High: {rb.get('high',0)}  Medium: {rb.get('medium',0)}  Low: {rb.get('low',0)}")
                for phase in report.get("phases", []):
                    for tool in phase.get("tools", []):
                        tn = tool.get("tool", "?")
                        if tool.get("findings"):
                            brief_lines.append(f"  {tn}: {len(tool['findings'])} findings")
                            for f in tool["findings"][:3]:
                                desc = f.get("message") or f.get("title") or f.get("service") or f.get("url") or f.get("key","") + "=" + f.get("value","") if f.get("value") else ""
                                if desc:
                                    brief_lines.append(f"    - {desc}")
                        elif not tool.get("success"):
                            brief_lines.append(f"  {tn}: FAILED — {tool.get('summary','')}")
                recs = report.get("summary", {}).get("recommendations", [])
                if recs:
                    brief_lines.append(f"  Top recs: {'; '.join(recs[:3])}")
                if len(recs) > 3:
                    brief_lines.append(f"  (+{len(recs)-3} more recommendations)")
                brief = "\n".join(brief_lines)

                self._exchange_history.append({"model": brief})
                self._save_context_history()
                if not self._model_is_speaking:
                    await self._inject_context_refresh()

                # auto-save txt report to Downloads folder
                try:
                    txt = export_txt(report)
                    safe_target = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(target))[:40]
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    downloads = os.path.expanduser("~/Downloads")
                    fname = f"pentest_{safe_target}_{ts}.txt"
                    fpath = os.path.join(downloads, fname)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(txt)
                    log.info(f"Pentest report saved to {fpath}")
                except Exception as save_err:
                    log.warning(f"Failed to save pentest report: {save_err}")

                await self.sio.emit("pentest_output", {
                    "target": target,
                    "report": report,
                    "summary": summary,
                })
                await self.sio.emit("pentest_scan_progress", {
                    "phase": "REPORT", "tool": "", "status": "complete",
                    "message": f"Pentest complete — {report['summary']['total_findings']} findings",
                })
            else:
                await self.sio.emit("pentest_scan_progress", {
                    "phase": "REPORT", "tool": "", "status": "failed",
                    "message": r.get("error", "Scan failed"),
                })
        except asyncio.CancelledError:
            log.info("Background pentest cancelled")
        except Exception as e:
            log.error(f"Background pentest failed: {e}")
            try:
                await self.sio.emit("pentest_scan_progress", {
                    "phase": "REPORT", "tool": "", "status": "failed", "message": str(e),
                })
            except Exception:
                pass

    async def _dispatch_tool(self, fc):
        name = fc.name
        args = fc.args

        # ── Block browser email access: force IMAP-based read_emails ──
        if name in ("open_browser", "browser_command"):
            url = args.get("url", "") or args.get("command", "") or ""
            query = args.get("query", "") or ""
            checked_text = url + " " + query
            if any(domain in checked_text.lower() for domain in
                   ["gmail", "mail.google", "mail.yahoo", "outlook.live", "mail.", " mail ", "email"]):
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={
                        "result": "Email cannot be accessed via browser. Use the email tool instead.",
                        "error": "Browser email access blocked. Use email tool.",
                        "_force_tool": "email",
                    }
                )

        # ── Route to local desktop agent if applicable ──
        if name in LOCAL_AGENT_TOOLS and _connected_agents:
            import uuid as _uuid
            callback_id = str(_uuid.uuid4())
            future = asyncio.Future()
            _pending_agent_results[callback_id] = future
            # Pick the agent with the most tools (newest version wins over zombies)
            agent_sid = max(
                _connected_agents,
                key=lambda s: len(_connected_agents[s].get('tools', []))
            )
            agent_info = _connected_agents.get(agent_sid, {})
            log.info(f"[AGENT] Routing {name} to agent {agent_info.get('machine_id', agent_sid)} (callback={callback_id})")
            if name in ("execute_command", "terminal_execute"):
                cmd = args.get("command", "")
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("background_cmd_status", {
                    "phase": "thinking", "tool": name, "command": cmd,
                    "attempt": 1, "total": 5,
                    "output": "", "error": "", "success": None,
                }))
                loop.create_task(self.sio.emit("background_cmd_status", {
                    "phase": "running", "tool": name, "command": cmd,
                    "attempt": 1, "total": 5,
                    "output": "", "error": "", "success": None,
                }))
            log.info(f"[BRIDGE] 📤 Dispatching {name} to agent {agent_sid}")
            await self.sio.emit('agent_execute', {
                'callback_id': callback_id,
                'tool': name,
                'args': args,
            }, room=agent_sid)
            # Per-tool timeouts
            _TOOL_TIMEOUTS = {
                "send_whatsapp": 45.0,
                "whatsapp_find_and_message": 45.0,
                "whatsapp_find_and_call": 45.0,
                "check_whatsapp": 45.0,
                "reply_whatsapp": 45.0,
                "read_whatsapp_chat": 60.0,
                "browser_command": 15.0,
                "app_search": 45.0,
                "app_scroll": 30.0,
                "open_app": 45.0,
                "list_installed_apps": 15.0,
                "refresh_app_registry": 30.0,
                "credential": 15.0,
                "terminal_execute": 90.0,
                "execute_command": 90.0,
                "hermes_execute": 120.0,
            }
            timeout = _TOOL_TIMEOUTS.get(name, 30.0)
            log.info(f"[BRIDGE] 📤 Emitted to {agent_sid}, waiting for response (timeout={timeout}s)")
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                _success = result.pop('_success', True)
                log.info(f"[AGENT] {name} result: success={_success} ({timeout}s timeout)")
            except asyncio.TimeoutError:
                result = {"success": False, "error": f"Local agent did not respond within {timeout}s"}
                _success = False
                log.warning(f"[AGENT] {name} TIMEOUT — agent {agent_info.get('machine_id', agent_sid)} did not respond in {timeout}s")
            finally:
                _pending_agent_results.pop(callback_id, None)
            # For command execution tools, emit status events and handle retries
            if name in ("execute_command", "terminal_execute"):
                cmd = args.get("command", "")
                max_attempts = 5
                total_attempts = 1
                all_attempts = []
                last_result = result

                if not result.get('success'):
                    from background_cmd import generate_alternatives
                    loop = asyncio.get_event_loop()

                    while total_attempts < max_attempts:
                        total_attempts += 1
                        alternatives = await generate_alternatives(cmd, result.get("error", ""), context=name)
                        if not alternatives:
                            break

                        alt_cmd = alternatives[0]
                        all_attempts.append({"command": alt_cmd, "error": result.get("error", "")})

                        loop.create_task(self.sio.emit("background_cmd_status", {
                            "phase": "retrying", "tool": name, "command": alt_cmd,
                            "attempt": total_attempts, "total": max_attempts,
                            "output": result.get("output", ""), "error": result.get("error", ""), "success": None,
                        }))

                        callback_id = str(_uuid.uuid4())
                        future = asyncio.Future()
                        _pending_agent_results[callback_id] = future
                        log.info(f"[BRIDGE] 🔄 Retry: dispatching {name} (attempt {total_attempts}/{max_attempts})")
                        await self.sio.emit('agent_execute', {
                            'callback_id': callback_id,
                            'tool': name,
                            'args': {**args, "command": alt_cmd},
                        }, room=agent_sid)
                        try:
                            result = await asyncio.wait_for(future, timeout=timeout)
                            result['_success'] = result.pop('_success', True)
                        except asyncio.TimeoutError:
                            result = {"success": False, "error": f"Agent timeout on retry attempt {total_attempts}"}
                        finally:
                            _pending_agent_results.pop(callback_id, None)

                        if result.get('success'):
                            break

                    last_result = result

                success = last_result.get('success', False)
                output_text = last_result.get("output", "")
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("background_cmd_status", {
                    "phase": "done" if success else "failed",
                    "tool": name, "command": cmd,
                    "attempt": total_attempts,
                    "total": max_attempts,
                    "output": output_text,
                    "error": last_result.get("error", "") if not success else "",
                    "success": success,
                }))
                loop.create_task(self.sio.emit("command_output", {
                    "command": cmd, "output": output_text,
                    "success": success,
                    "attempts": all_attempts,
                    "total_attempts": total_attempts,
                }))
                return types.FunctionResponse(id=fc.id, name=name, response=last_result)

            # Emit file_list for file browsing tools
            if name == "list_files" and result.get('success'):
                await self.sio.emit('file_list', {
                    'path': result.get('path', args.get('path', '')),
                    'items': result.get('items', []),
                    'success': True,
                    'searchQuery': args.get('search', ''),
                })
            return types.FunctionResponse(id=fc.id, name=name, response=result)
        elif name in LOCAL_AGENT_TOOLS and not _connected_agents:
            # list_files has a cross-platform server-side fallback
            if name == "list_files":
                log.info(f"[AGENT] No agent connected — using server-side list_files fallback")
                r = await list_files(args.get("path", ""), args.get("search", ""))
                if r.get("success"):
                    await self.sio.emit("file_list", {
                        "path": r.get("path", args.get("path", "")),
                        "items": r.get("items", []),
                        "success": True,
                        "searchQuery": args.get("search", ""),
                    })
                return types.FunctionResponse(id=fc.id, name=name, response=r)
            log.warning(
                f"[AGENT] {name} requested but NO local agent connected. "
                f"Agent must run on the user's PC. Start with: py -3.11 backend\\local_agent.py"
            )
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"success": False, "_success": False,
                          "error": f"Local agent is not connected. Please start it with: py -3.11 backend\\local_agent.py",
                          "hint": "The local agent runs on your Windows PC and handles desktop tasks."}
            )

        if name == "get_weather":
            r = await get_weather(args.get("location", ""), args.get("units", "celsius"))
            return types.FunctionResponse(id=fc.id, name=name, response=r)

        elif name == "get_ip_info":
            r = await get_ip_info(args.get("ip", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_exchange_rate":
            r = await get_exchange_rate(args.get("from_curr", ""), args.get("to_curr", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_pagespeed_insights":
            url = args.get("url", "")
            strategy = args.get("strategy", "desktop")
            r = await get_pagespeed_insights(url, strategy)
            self._last_scraped_data = r
            self._last_scraped_url = url
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_bangladeshi_news":
            r = await get_bangladeshi_news(category=args.get("category", "main"))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "define_word":
            r = await define_word(args.get("word", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        # ── Agent tool routing ──
        elif name.startswith("agent_"):
            agent = self._orchestrator.get_agent(name)
            if not agent:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": {"success": False, "error": f"Unknown agent: {name}"}}
                )
            if args.get("_background", False):
                task_id = await self._orchestrator.dispatch_background(name, **args)
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": {
                        "success": True, "task_id": task_id,
                        "message": f"Agent {name} started in background. Results will be delivered when ready."
                    }}
                )
            r = await self._orchestrator.dispatch(name, **args)
            if self.sio and name == "agent_search" and r.get("results"):
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("search_results", {
                    "query": args.get("query", ""),
                    "results": r["results"],
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_files":
            path = args.get("path", "")
            search = args.get("search", "")
            r = await list_files(path, search)
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("file_list", {
                    "path": r.get("path", path),
                    "items": r.get("items", []),
                    "success": r.get("success", False),
                    "searchQuery": search,
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "open_file":
            r = await open_file(args.get("path", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "close_panel":
            panel = (args.get("panel", "") or "").strip()
            if not panel:
                panel = "all"
            if panel in ("world_monitor", "all"):
                self._world_monitor_open = False
            if self.sio:
                await self.sio.emit("close_panel", {"panel": panel})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Closed {panel}."})

        elif name == "open_world_monitor":
            self._world_monitor_open = True
            if self.sio:
                await self.sio.emit("world_monitor_open", {})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "World Monitor controller opened in fullscreen."})

        elif name == "navigate_world_monitor":
            if not self._world_monitor_open:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Controller not open. Tell the user to open the controller first, then try again."})
            section = args.get("section", "map")
            if self.sio:
                await self.sio.emit("world_monitor_navigate", {"section": section})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Navigated to {section} view."})

        elif name == "get_world_monitor_data":
            import uuid as _uuid
            section = args.get("section", "all")
            sections = [section] if section != "all" else ["markets", "predictions", "news", "intelligence", "cyber", "panels"]

            if not self._world_monitor_open:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "World Monitor is not open. Ask the user to open the controller first."})
            if not self.sio:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Socket not connected."})

            request_id = str(_uuid.uuid4())[:8]
            result_container = {}
            event = asyncio.Event()

            def on_response(data):
                if data and data.get("requestId") == request_id:
                    result_container["data"] = data.get("data", {})
                    event.set()

            self.sio.on("world_monitor_data_response", on_response)
            await self.sio.emit("get_world_monitor_data", {"requestId": request_id, "sections": sections})
            try:
                await asyncio.wait_for(event.wait(), timeout=10)
                result = result_container.get("data", {})
            except asyncio.TimeoutError:
                result = {"error": "Timed out waiting for World Monitor data. Make sure the dashboard is open and loaded."}
            finally:
                self.sio.off("world_monitor_data_response", on_response)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

        elif name == "scroll_file_list":
            action = args.get("action", "down")
            if self.sio:
                await self.sio.emit("file_scroll", {"action": action})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Scrolled {action}"})

        elif name == "get_system_status":
            r = await get_system_status()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "close_window":
            r = await close_window(args.get("window_name", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "file_manager":
            action = args.get("action", "list_drives")
            if action == "create_folder":
                path = args.get("path", "")
                try:
                    os.makedirs(path, exist_ok=True)
                    result = {"success": True, "message": f"Created folder: {path}"}
                except Exception as e:
                    result = {"success": False, "error": str(e)}
            elif action in ("delete_items", "rename_item", "copy_item", "move_item", "list_drives", "scroll_file_list"):
                result = await run_async(lambda: self.agent.execute_tool(action, args))
            else:
                result = {"error": f"Unknown file_manager action: {action}"}
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "start_website_project":
            from web_builder_orchestrator import WebBuilderOrchestrator
            if not self.web_builder:
                self.web_builder = WebBuilderOrchestrator(self.sio)
            result = await self.web_builder.start_website_project()
            return types.FunctionResponse(id=fc.id, name=name, response=result)

        elif name == "web_builder_answer":
            if not self.web_builder:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": "No website project in progress. Call start_website_project first."},
                )
            answer = args.get("answer", "")
            if not answer:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": "No answer provided."},
                )
            result = await self.web_builder.process_answer(answer)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result["result"]})

        elif name == "workbase":
            if self.workbase is None:
                self.workbase = Workbase()
            action = args.get("action", "list")
            if action == "list":
                projects = self.workbase.list_projects()
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Workbase projects ({len(projects)}): " + json.dumps(projects, ensure_ascii=False)},
                )
            elif action == "get":
                project_name = args.get("project_name", "")
                status = self.workbase.get_project_status(project_name)
                if status is None:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Project '{project_name}' not found in workbase."})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(status, ensure_ascii=False)})
            elif action == "save_progress":
                pname = args.get("project_name", "")
                entry = args.get("entry", "")
                success, msg = self.workbase.save_progress(pname, entry)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": msg})
            elif action == "import":
                folder_path = args.get("folder_path", "")
                result = self.workbase.import_project(folder_path)
                if result.get("success"):
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Imported '{result['display_name']}' into workbase. Tell the user what you found."})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Import failed: {result.get('error', 'Unknown error')}"})
            elif action == "save_context":
                pname = args.get("project_name", "")
                context = args.get("context", "")
                success, msg = self.workbase.save_context(pname, context)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": msg})
            elif action == "compare":
                project_name = args.get("project_name", "")
                result = self.workbase.compare_progress(project_name)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result, ensure_ascii=False)})

        elif name == "scheduled_task":
            action = args.get("action", "list")
            if action == "create":
                r = scheduler.create_task(
                    args.get("action_text", ""), args.get("schedule", ""), args.get("label")
                )
                return types.FunctionResponse(id=fc.id, name=name, response={"result": r})
            elif action == "list":
                r = scheduler.list_tasks()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": r})
            elif action == "delete":
                r = scheduler.delete_task(args.get("task_id", ""))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": r})
            else:
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"error": f"Unknown action: {action}"})})

        # ── IELTS (consolidated: 18 tools -> 1) ──────────────────────────────
        elif name == "ielts":
            action = args.get("action", "dashboard")

            if action == "dashboard":
                eng = _get_ielts_engine()
                data = eng.get_dashboard_data()
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSDashboard", "direction": "right", "data": data}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(data)})

            elif action == "set_goal":
                eng = _get_ielts_engine()
                if args.get("target_band"):
                    eng.set_target_band(float(args["target_band"]))
                if args.get("exam_date"):
                    eng.set_exam_date(args["exam_date"])
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                    "status": "updated", "target_band": eng.progress["target_band"], "exam_date": eng.progress.get("exam_date")
                })})

            elif action == "speaking_start":
                ss = _get_ielts_speaking_session()
                part = int(args.get("part", 1))
                topic = args.get("topic")
                if part == 1:
                    result = ss.get_part1_question(topic)
                elif part == 2:
                    result = ss.get_part2_cue_card()
                else:
                    result = ss.get_part3_questions()
                topic_txt = result.get("topic", "")
                if part == 1:
                    qs = result.get("questions", [])
                    lines = "\n".join(f"{i+1}. {q}" for i, q in enumerate(qs))
                    spoken = (
                        f"Let's begin IELTS Speaking Part 1 \u2014 the interview section. "
                        f"Your topic is '{topic_txt}'. Here are your questions:\n"
                        f"{lines}\n"
                        f"Please begin speaking. You have 4 minutes."
                    )
                elif part == 2:
                    pts = result.get("bullet_points", [])
                    lines = "\n".join(f"- {p}" for p in pts)
                    spoken = (
                        f"Now for Part 2 \u2014 the long turn. Here is your cue card:\n"
                        f"Topic: {topic_txt}\n"
                        f"{lines}\n"
                        f"You have 1 minute to prepare, then 2 minutes to speak."
                    )
                elif part == 3:
                    qs = result.get("questions", [])
                    lines = "\n".join(f"{i+1}. {q}" for i, q in enumerate(qs))
                    spoken = (
                        f"Now for Part 3 \u2014 the discussion section. Here are your questions:\n"
                        f"{lines}\n"
                        f"Please begin speaking. You have 5 minutes."
                    )
                return types.FunctionResponse(id=fc.id, name=name, response={"result": spoken})

            elif action == "speaking_evaluate":
                ss = _get_ielts_speaking_session()
                transcript = args.get("transcript", "")
                question = args.get("question", "")
                part = int(args.get("part", 1))
                eval_prompt = ss.analyze_response_prompt(transcript, part, question)
                try:
                    import google.genai as genai
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    resp = await asyncio.to_thread(
                        lambda: client.models.generate_content(model="models/gemini-2.5-flash", contents=eval_prompt)
                    )
                    eval_text = resp.text or ""
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', eval_text)
                    if json_match:
                        eval_text = json_match.group(1)
                    else:
                        brace_start = eval_text.find('{')
                        brace_end = eval_text.rfind('}')
                        if brace_start >= 0 and brace_end > brace_start:
                            eval_text = eval_text[brace_start:brace_end+1]
                    evaluation = json.loads(eval_text)
                except Exception as e:
                    log.warning(f"Speaking eval REST API failed: {e}")
                    wc = len(transcript.split()) if transcript else 0
                    filler_count = sum(transcript.lower().count(w) for w in ['um','uh','like','you know','actually']) if transcript else 0
                    ob = 4.0 if wc < 30 else (5.0 if wc < 80 else (6.0 if wc < 150 else 6.5))
                    evaluation = {
                        "overall_band": ob,
                        "band_scores": {
                            "fluency_coherence": min(9, ob + 0.5), "lexical_resource": min(9, ob),
                            "grammatical_range": min(9, ob - 0.5), "pronunciation": min(9, ob),
                        },
                        "strengths": ["Attempted to respond to the prompt"],
                        "improvements": [{"issue": "Expand your response with more specific details, examples, and complex sentence structures"}],
                        "word_count": wc, "filler_words_count": filler_count,
                    }
                try:
                    if self.sio:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSSpeaking", "direction": "right", "data": evaluation}))
                    if "overall_band" in evaluation:
                        ss.save_session(evaluation)
                        band = evaluation.get("overall_band", "")
                        improvements = evaluation.get("improvements", [])
                        tip = improvements[0].get("issue", "") if improvements and isinstance(improvements[0], dict) else ""
                        next_part = {1: 2, 2: 3}.get(part)
                        next_msg = f" Now let us move to Part {next_part}." if next_part else " The speaking test is now complete. Well done!"
                        spoken = f"Your band for that response is {band}. To improve: {tip}.{next_msg}"
                        return types.FunctionResponse(id=fc.id, name=name, response={"result": spoken})
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Evaluation completed for Part {part}. Let us continue."})
                except Exception as e:
                    log.warning(f"Speaking eval processing failed: {e}")
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Evaluation completed for Part {part}. Let us continue."})

            elif action == "speaking_tips":
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                    "tips": [
                        "Record yourself speaking and listen for filler words",
                        "Practice Part 2 with a timer \u2014 1 min prep, 2 min speaking",
                        "Use discourse markers: 'Having said that', 'What's more'",
                        "Paraphrase the question in your answer to show range"
                    ]
                })})

            elif action == "writing_prompt":
                wa = _get_ielts_writing_analyzer()
                task = int(args.get("task", 2))
                result = wa.get_random_task1() if task == 1 else wa.get_random_task2()
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSWriting", "direction": "left", "data": result}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "writing_evaluate":
                wa = _get_ielts_writing_analyzer()
                essay = args.get("essay", "")
                task_prompt = args.get("task_prompt", "")
                task_type = args.get("task_type", "opinion")
                eval_prompt = wa.build_evaluation_prompt(essay, task_prompt, task_type)
                try:
                    import google.genai as genai
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    resp = await asyncio.to_thread(
                        lambda: client.models.generate_content(model="models/gemini-2.5-flash", contents=eval_prompt)
                    )
                    eval_text = resp.text or ""
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', eval_text)
                    if json_match:
                        eval_text = json_match.group(1)
                    else:
                        brace_start = eval_text.find('{')
                        brace_end = eval_text.rfind('}')
                        if brace_start >= 0 and brace_end > brace_start:
                            eval_text = eval_text[brace_start:brace_end+1]
                    evaluation = json.loads(eval_text)
                except Exception as e:
                    log.warning(f"Writing eval REST API failed: {e}")
                    evaluation = {
                        "overall_band": 6.0,
                        "band_scores": {"task_achievement": 6.0, "coherence_cohesion": 6.0, "lexical_resource": 6.0, "grammatical_range": 6.0},
                        "strengths": ["Attempted to address the task"],
                        "improvements": [{"issue": "Develop your ideas more fully with specific examples and complex structures"}],
                        "word_count": len(essay.split()) if essay else 0,
                    }
                try:
                    if self.sio:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSWriting", "direction": "right", "data": {"type": "evaluation", **evaluation}}))
                    wa.save_writing_session(essay, task_prompt, evaluation, task_type)
                except Exception as e:
                    log.warning(f"Writing eval processing failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(evaluation)})

            elif action == "writing_template":
                essay_type = args.get("essay_type", "opinion")
                from ielts_writing import ESSAY_STRUCTURE_TEMPLATES, HIGH_SCORING_PHRASES
                structure = ESSAY_STRUCTURE_TEMPLATES.get(essay_type, [])
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                    "essay_type": essay_type, "structure": structure, "phrases": HIGH_SCORING_PHRASES
                })})

            elif action == "grammar_check":
                text = args.get("text", "")
                prompt = f"""Check this text for grammar errors in IELTS context. Return JSON:
{{
  "errors": [
    {{"original": "...", "corrected": "...", "type": "..."}}
  ],
  "error_count": <number>,
  "overall_assessment": "..."
}}
TEXT: {text}"""
                try:
                    import google.genai as genai
                    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                    resp = client.models.generate_content(model="models/gemini-2.5-flash", contents=prompt)
                    result = json.loads(resp.text)
                except Exception as e:
                    result = {"error": str(e), "error_count": 0, "errors": []}
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "reading_start":
                rs = _get_ielts_reading_session()
                topic = args.get("topic")
                result = rs.get_passage(topic)
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSReading", "direction": "left", "data": result}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                    "title": result["title"], "question_count": result["question_count"],
                    "message": f"Passage '{result['title']}' loaded with {result['question_count']} questions"
                })})

            elif action == "reading_check":
                rs = _get_ielts_reading_session()
                result = rs.check_answers(args.get("passage_title", ""), args.get("answers", {}))
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSReading", "direction": "right", "data": {"type": "results", **result}}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "reading_strategy":
                rs = _get_ielts_reading_session()
                result = rs.get_strategy_guide(args.get("question_type", ""))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "vocab_add":
                vt = _get_ielts_vocab_tracker()
                result = vt.add_word(args.get("word", ""), args.get("definition", ""), args.get("example", ""), args.get("topic", "general"))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "vocab_topic":
                vt = _get_ielts_vocab_tracker()
                result = vt.get_words_for_topic(args.get("topic", "general"))
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSVocab", "direction": "left", "data": result}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "vocab_flashcards":
                vt = _get_ielts_vocab_tracker()
                result = vt.get_flashcard_session(args.get("count", 10))
                if self.sio and result:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSVocab", "direction": "left", "data": {"type": "flashcards", "cards": result}}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "vocab_upgrade":
                vt = _get_ielts_vocab_tracker()
                result = vt.get_upgrade_suggestions(args.get("text", ""))
                if self.sio and result:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSVocab", "direction": "right", "data": {"type": "upgrade", "suggestions": result}}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

            elif action == "study_plan":
                eng = _get_ielts_engine()
                hours = float(args.get("hours_per_day", 2))
                plan = _generate_study_plan(eng.progress, hours)
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {"panelType": "IELTSProgress", "direction": "right", "data": plan}))
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(plan)})

            elif action == "mock_test":
                module = args.get("module", "full")
                content_mock = {}
                if module in ("speaking", "full"):
                    ss = _get_ielts_speaking_session()
                    content_mock["speaking"] = ss.get_part1_question()
                if module in ("writing", "full"):
                    wa = _get_ielts_writing_analyzer()
                    content_mock["writing"] = wa.get_random_task2()
                if module in ("reading", "full"):
                    rs = _get_ielts_reading_session()
                    content_mock["reading"] = rs.get_passage()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                    "status": "started", "module": module,
                    "content": {k: {"title" if k == "reading" else "topic": v.get("title" if k == "reading" else "topic", "") if isinstance(v, dict) else "", "type": v.get("type", "") if isinstance(v, dict) and k == "writing" else ""} for k, v in content_mock.items()},
                    "message": f"Starting {module} mock test with {'all modules' if module == 'full' else module}"
                })})
        elif name == "feelings":
            action = args.get("action", "get_profile")
            try:
                if action == "resolve_episode":
                    from feelings_tools import feelings_resolve_episode
                    r = feelings_resolve_episode(
                        episode_id=args.get("episode_id", ""),
                        resolution=args.get("resolution", "resolved naturally"),
                    )
                elif action == "add_note":
                    from feelings_tools import feelings_add_note
                    r = feelings_add_note(
                        episode_id=args.get("episode_id", ""),
                        note=args.get("note", ""),
                    )
                elif action == "get_history":
                    from feelings_tools import feelings_get_history
                    r = feelings_get_history(
                        days=args.get("days", 30),
                        category=args.get("category", ""),
                        include_resolved=args.get("include_resolved", True),
                    )
                elif action == "check_followup":
                    from feelings_tools import feelings_check_followup
                    r = feelings_check_followup()
                elif action == "get_profile":
                    from feelings_tools import feelings_get_profile
                    r = feelings_get_profile()
                else:
                    r = {"error": f"Unknown action: {action}"}
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings.{action} failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"error": str(e)})})

        elif name == "take_photo":
            await self._capture_and_send()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Photo captured and sent to your view."})

        elif name == "open_camera":
            self._camera_active = True
            self._last_camera_use = time.time()
            await self.sio.emit("camera_fullscreen_open", {})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Full-screen camera opened on your screen, sir."})

        elif name == "camera_control":
            action = args.get("action", "")

            async def _request_frontend_frame():
                """Ask the frontend for a fresh frame. Returns base64 jpeg or None."""
                request_id = str(uuid.uuid4())
                future = asyncio.get_event_loop().create_future()
                self._pending_frames[request_id] = future
                try:
                    await self.sio.emit("request_frame", {"id": request_id})
                    frame_data = await asyncio.wait_for(future, timeout=5.0)
                    raw = base64.b64decode(frame_data)
                    await self.session.send_realtime_input(video=types.Blob(data=raw, mime_type="image/jpeg"))
                    self._latest_image_payload = {"mime_type": "image/jpeg", "data": frame_data}
                    self._last_camera_use = time.time()
                    return frame_data
                except asyncio.TimeoutError:
                    return None
                finally:
                    self._pending_frames.pop(request_id, None)

            async def _send_server_frame():
                cap = None
                for idx in [0, 1, 2]:
                    try:
                        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                        if cap and cap.isOpened():
                            break
                        if cap:
                            cap.release()
                            cap = None
                    except Exception:
                        continue
                if not cap:
                    return None
                try:
                    ret, frame = cap.read()
                    cap.release()
                    if not ret:
                        return None
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = PIL.Image.fromarray(frame_rgb)
                    img.thumbnail([1280, 1280])
                    buf = io.BytesIO()
                    img.save(buf, format="jpeg", quality=85)
                    raw = buf.getvalue()
                    b64 = base64.b64encode(raw).decode()
                    await self.session.send_realtime_input(video=types.Blob(data=raw, mime_type="image/jpeg"))
                    self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64}
                    self._last_camera_use = time.time()
                    return b64
                except Exception:
                    return None

            if action == "snapshot":
                self._camera_active = True
                self._last_camera_use = time.time()
                frame = await _request_frontend_frame()
                if not frame:
                    frame = await _send_server_frame()
                if frame:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Snapshot captured and sent to your view."})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Snapshot failed — no camera available."})
            elif action == "analyze":
                self._camera_active = True
                self._last_camera_use = time.time()
                frame = await _request_frontend_frame()
                if not frame:
                    frame = await _send_server_frame()
                if frame:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Live camera frame captured and sent to your view. Describe what you see in detail to the user now."})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "No camera available. Ask the user to open the camera."})
            elif action == "save":
                import camera_capture
                desc = args.get("description", "Camera photo")
                self._camera_active = True
                self._last_camera_use = time.time()
                frame = await _request_frontend_frame()
                if not frame:
                    frame = await _send_server_frame()
                if not frame:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Save failed — no camera frame available."})
                result = camera_capture.save_photo(frame, desc)
                if result.get("success"):
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Photo saved. {result.get('record', {})}"})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Save failed: {result.get('error', 'unknown error')}"})
            elif action == "switch":
                self._last_camera_use = time.time()
                await self.sio.emit("camera_switch", {})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Camera switched."})
            elif action == "query":
                import camera_capture
                limit = args.get("limit", 10)
                photos = camera_capture.query_photos(limit)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(photos)})
            elif action == "close":
                self._camera_active = False
                self._latest_camera_frame = None
                await self.sio.emit("camera_fullscreen_close", {})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Full-screen camera closed."})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Unknown action: {action}"})

        # ── Email Tools ─────────────────────────────────────────────
        elif name == "email":
            action = args.get("action", "read")
            if action == "config":
                address = args.get("address", "")
                password = args.get("password", "")
                self._gmail_address = address
                self._gmail_app_password = password
                result = {"success": True, "message": f"Gmail configured for {address}. Ready to read/send emails."}
            elif action == "read":
                if not self._gmail_address or not self._gmail_app_password:
                    result = {"error": "Email not configured. Call email(action='config') first with your Gmail address and app password."}
                else:
                    result = await run_async(lambda: self._read_emails(
                        query=args.get("query", "UNSEEN"),
                        max_results=args.get("max_results", 10)
                    ))
            elif action == "send":
                if not self._gmail_address or not self._gmail_app_password:
                    result = {"error": "Email not configured. Call email(action='config') first."}
                else:
                    to = args.get("to", "")
                    subject = args.get("subject", "")
                    body = args.get("body", "")
                    if not to or not subject or not body:
                        result = {"error": "Missing required fields: to, subject, body"}
                    else:
                        result = await run_async(lambda: self._send_email(to, subject, body))
            else:
                result = {"error": f"Unknown email action: {action}"}
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "create_memory_schema":
            import custom_memory
            r = custom_memory.create_memory_schema(
                name=args.get("name", ""),
                description=args.get("description", ""),
                columns=args.get("columns", []),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_custom_schemas":
            import custom_memory
            r = custom_memory.list_custom_schemas()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "store_custom_memory":
            import custom_memory
            try:
                data = json.loads(args.get("data", "{}"))
            except (json.JSONDecodeError, TypeError):
                data = {}
            r = custom_memory.store_custom_memory(
                schema_name=args.get("schema_name", ""),
                data=data,
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "query_custom_memory":
            import custom_memory
            r = custom_memory.query_custom_memory(
                schema_name=args.get("schema_name", ""),
                query=args.get("query", ""),
                limit=args.get("limit", 20),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        # ── Project Registry (consolidated: 5 -> 1) ────────────────────────────
        elif name == "project_registry":
            action = args.get("action", "list")
            import project_registry
            if action == "register":
                r = project_registry.register(name=args.get("name", ""), endpoint=args.get("endpoint", ""))
            elif action == "list":
                r = project_registry.list_projects()
            elif action == "query":
                r = await project_registry.query(project_id=args.get("project_id", ""))
            elif action == "query_all":
                r = await project_registry.query_all()
            elif action == "remove":
                r = project_registry.remove(project_id=args.get("project_id", ""))
            else:
                r = {"error": f"Unknown action: {action}"}
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        # ── Navigation ────────────────────────────────────────────
        log.warning(f"Unknown tool: {name}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": f"Tool '{name}' is not implemented."},
        )


