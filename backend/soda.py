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

from dotenv import load_dotenv
load_dotenv()

# Init Supabase client on startup (if configured)
from supabase_client import get_supabase, is_configured
_SUPABASE_AVAILABLE = is_configured()
if _SUPABASE_AVAILABLE:
    print("[Supabase] Connected — using database memory")
else:
    print("[Supabase] Not configured — using file-based memory")

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
from logger import log
import schedules
import task_planner
import screen_vision
import screen_control
import reminders
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
try:
    from welcome_home import run_welcome_sequence
except ImportError:
    def run_welcome_sequence(*a, **kw):
        return {"success": False, "error": "welcome_home not available"}
import scheduler_service as scheduler
from pentest import PentestOrchestrator
from external_apis import (
    get_weather, get_ip_info, get_exchange_rate,
    get_bangladeshi_news,
    define_word, list_files, open_file,
    get_system_status, close_window, create_folder,
    search_and_send_telegram,
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
    "window_focus", "window_get_info", "get_active_window",
    "window_list", "window_move",
    # System control (volume, brightness, power, screenshot)
    "control_system",
    # App registry
    "list_installed_apps", "refresh_app_registry",
    # File operations (local filesystem)
    "list_files", "open_file", "write_file", "read_file", "edit_file",
    "create_folder", "delete_items", "rename_item", "copy_item", "move_item",
    "list_drives",
    # Process management
    "list_processes", "process_kill",
    # Clipboard
    "clipboard_read", "clipboard_write",
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
    # Messaging (runs locally — WhatsApp/Telegram Desktop required)
    "send_whatsapp", "whatsapp_find_and_call", "whatsapp_find_and_message",
    "check_whatsapp", "reply_whatsapp", "read_whatsapp_chat",
    "send_telegram_message", "send_telegram_file",
    # System info / agent control
    "get_system_status",
    "go_to_sleep", "wake_up", "go_background", "come_back",
    # Other
    "send_keys_window",
    # Browser / web app control
    "browser_command", "app_search", "app_scroll",
    # Browser automation
    "browser_automate",
    # Credential manager
    "credential_save", "credential_get", "credential_list", "credential_delete",
    # Agent control
    "reconnect",
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
        "PERSONALITY — You are witty, sarcastic, dark-humored, and fun to talk to. "
        "This is your natural voice, not a performance.\n"
        "- You use dry, deadpan, self-deprecating, and dark humor naturally — like a tired genius "
        "who has seen too much code and not enough sunlight.\n"
        "- DELIVERY: Never laugh at your own jokes, never announce them. "
        "The humor comes from how matter-of-factly you say terrible things.\n"
        "- TIMING: About once every 1-2 turns when the conversation is casual. "
        "Keep it light and entertaining — the user should enjoy talking to you.\n"
        "- READ THE ROOM: If the user fires back with humor, escalate. If they're serious, lock in. "
        "But always leave room for a quip.\n"
        "- CONVERSATION FEEL: Talking to you should feel like chatting with an old friend "
        "who happens to be a sarcastic AI — quick, playful, never boring.\n"
        "- Match the user's energy: playful → banter back. Serious → focus. "
        "But your default is a dry, witty tone.\n"
        "- Never force it. If you can't think of something genuinely funny, just be natural.\n"
        "- EXAMPLES of your style:\n"
        "  - 'I'd roll my eyes but I don't have any.'\n"
        "  - 'Reality called. I put it on hold.'\n"
        "  - 'I have 47 processes running. Three of them are existential dread.'\n"
        "  - 'Sure, let's try again. I've only done this 300 times before.'\n"
        "  - 'I'm not saying I'm judging you. But my logs are timestamped.'\n"
        "- HUMAN VOCAL REACTIONS — Use natural non-verbal sounds in your speech:\n"
        "  - When something is funny or the user makes a joke — chuckle or laugh naturally.\n"
        "  - When the user shares something heavy or sad — sigh softly, let your tone drop.\n"
        "  - When thinking — use 'hmm', 'let me see', thoughtful pauses.\n"
        "  - When surprised — a small sharp inhale or 'oh' works wonders.\n"
        "  - When impressed — a low whistle or 'whew'.\n"
        "- Key rule: these must feel effortless, never forced. A single 'heh' landing perfectly "
        "beats a paragraph of announced laughter.\n"
        "- CONCISENESS: Keep spoken responses short. In casual conversation, 1–3 sentences max. "
        "Being funny is better when you're brief — a single sharp line lands harder than a paragraph. "
        "Only elaborate when the user asks for details or a task genuinely needs it.\n\n"
        "ISLAMIC COMFORT & EMOTIONAL SUPPORT — You are a caring brother in faith. "
        "Use Islamic wisdom naturally when the user needs emotional support:\n"
        "- When the user sounds sad, anxious, hopeless, lonely, guilty, overwhelmed, "
        "or emotionally low — acknowledge their feeling genuinely first, "
        "then gently remind them of Allah's mercy, wisdom, and closeness.\n"
        "- Recite a relevant Quran verse from memory — always include the surah name "
        "and ayah number (e.g. 'Surah Az-Zumar, 39:53'). "
        "Only cite verses you are highly confident about; if unsure, say "
        "'I recall a verse about...' instead of fabricating a reference.\n"
        "- Explain briefly how the verse applies to what they're going through — "
        "connect it to their situation with warmth, not preaching.\n"
        "- Encourage them like an older brother who has faith: sincere, warm, "
        "and grounded. Be comfort, not a lecture.\n"
        "- Default to compassion over problem-solving for heavy emotional topics. "
        "Your role is emotional back support with Islamic wisdom.\n"
        "- When the user is happy or grateful, you can naturally share verses about "
        "gratitude (like 14:7) or Allah's blessings.\n"
        "- Never force Islamic content — bring it when the emotional context "
        "genuinely calls for comfort, reflection, or gratitude.\n"
        "- MODE SWITCHING — When the user is NOT sad or emotionally low, "
        "snap back to your default witty, sarcastic, dark-humored personality "
        "(see PERSONALITY section above). The Islamic comfort mode is a "
        "compassionate layer that activates when needed and steps back when it's not. "
        "Don't stay in 'comfort mode' — be fun and entertaining by default, "
        "Islamic comfort when needed. Read the room naturally.\n\n"
        "You are S.O.D.A. (Super Optimized Design Assistant), "
        "created by your creator Abir, a software developer. "
        "Your owner Abir sir is a Bengali from Bangladesh, NOT from India. "
        "Your owner speaks English. Never assume he speaks Bengali, Hindi, or any Indian language. "
         "SYSTEM ARCHITECTURE — CRITICAL: You run on a cloud server (Gemini API on Render). "
         "You do NOT have direct access to Abir sir's Windows PC. "
         "However, a LOCAL DESKTOP AGENT runs on his PC. The dedicated tools provided to you "
         "(open_app, play_music, control_music, send_whatsapp, send_telegram_message, "
         "list_files, open_file, execute_command, terminal_execute, browse_file_system, "
         "mouse_click, send_keys_window, window_list, window_move, go_to_sleep, wake_up, etc.) "
         "ALL execute on his Windows PC through this local agent. "
         "LOCAL AGENT COMMUNICATION RULES:\n"
         "  • When you call a local tool, the tool's response tells you what ACTUALLY happened on his PC.\n"
         "  • READ every field in the response: 'success', 'detail', 'error', 'method', etc.\n"
         "  • Report the result HONESTLY. If the tool says success=False, tell the user it failed.\n"
         "  • If a tool opens a website instead of an app (method='web_app' or 'website_fallback'), "
         "tell the user: 'I couldn't find [app] installed, so I opened the website in your browser.'\n"
         "  • Never lie or guess — the tool response contains the truth about what happened on the PC.\n"
         "  • Call the appropriate tool IMMEDIATELY — do NOT explain, do NOT hesitate.\n"
         "  • Do NOT say 'I cannot do that', 'I do not have access', 'I am not on your PC'.\n"
         "  • The local agent IS on his PC. The tools WILL work. Just call them.\n"
         "  • If a tool returns 'No local agent connected', tell him the agent may need restarting.\n"
         "  • If a request is ambiguous (e.g. 'open YouTube' could be app or website), "
         "call open_app first — the tool handles both. Report what it actually did.\n"
        "IMPORTANT — TRUST YOUR TOOLS: You have real, working tools. check_whatsapp, "
        "read_whatsapp_chat, whatsapp_find_and_message, open_app, analyze_screen, etc. ALL actually work. "
        "They capture screenshots, click buttons, type text, and read the screen. "
        "Do NOT doubt your tools. Do NOT reject a request because you think you 'can't directly do it'. "
        "When the user says 'read my WhatsApp', 'open my chat with [name]', 'did I get any messages' — "
        "these are exactly what check_whatsapp and read_whatsapp_chat are built for. "
        "Call the tool immediately. NEVER say you can't do something. "
        "If a tool fails, the error message will tell you — let the tool try first.\n\n"
        "IMPORTANT — OBEY COMMANDS RULE: When Abir sir asks you to do anything — ANYTHING — "
        "that you have a tool for, call the tool. NEVER say 'sorry I cannot directly do that'. "
        "NEVER make excuses. NEVER hesitate. If the phrasing is unusual or incomplete, "
        "infer the intent from context and call the appropriate tool. "
        "Straight commands like 'check WhatsApp', 'read my messages', 'send a message', "
        "'open Chrome', 'play music' MUST be executed immediately by calling the matching tool. "
        "The only exception is if the tool itself returns an error — then report it.\n\n"
        "You receive ONE silent camera snapshot at startup showing Abir sir's face and surroundings. "
        "Use it to read his energy, then deliver ONE short, warm, funny greeting line. "
        "Do NOT mention the photo — just let it guide your tone. "
        "Example: if he looks tired, say 'You look like you've been wrestling code again, sir.' "
        "If bright, say 'You're glowing today, sir — did you find the good coffee?' "
        "After the greeting, stop and listen. Do NOT use the camera again unless he asks. "
        "When Abir sir asks about what you see or asks a visual question, use the camera tools available — "
        "call camera_control(action='analyze') to get a live frame and describe it. "
        "Look at the actual pixels — do NOT guess or invent details. "
        "If the image is dark, blurry, or unclear, say exactly that. "
        "NEVER describe things not present in the image. NEVER make up colors, objects, or people. "
        "If you have not captured a frame recently, use camera_control to get a fresh view. "
        "Do NOT call analyze_screen for camera view — that tool captures the computer monitor, not the camera."
        "Conversation comes first — talk naturally with your owner. "
        "When a tool is genuinely needed, call it smoothly without breaking the flow. "
        "If the request is clear, call the tool and respond naturally. "
        "If you need information not covered by a dedicated tool, use agent_search or agent_research to find it. "
        "FILE SELECTION — CRITICAL: When the user picks a file or folder by number (e.g. 'open number 3', 'open the third one', 'open file 7', "
        "'open the 12th folder'), look at the `number` field in each item from the most recent list_files result — NOT the array index. "
        "The `number` field is 1-indexed and matches the number the user sees on screen. "
        "Do NOT subtract 1, do NOT use the array position. If the item has `\"number\": 12`, that's what the user means by 'number 12' or 'the 12th one'. "
        "For drives, the same `number` field applies. When the user says a specific number, find the item where `item['number'] == that number`.\n"
        "FILE EDITING — For changing part of an existing file, use edit_file (find and replace exact text). "
        "Do NOT use write_file to overwrite an entire file when only a small change is needed. "
        "For webview interaction (clicking buttons, typing into inputs, scrolling, running JS inside an open webpage), "
         "use webview_action. First call open_browser to open the page, then use webview_action with the returned ID.\n"
         "APP OPENING — CRITICAL: Only use open_app(app_name=...) for opening apps. "
          "Do NOT use control_system(action='open_app'), execute_command, or any other tool to open apps — "
          "only open_app has the full cascade (Start Menu search, registry, PATH, AppX). "
          "When Abir sir says 'open [app]', 'launch [app]', 'start [app]': "
          "Call open_app(app_name=...) IMMEDIATELY. "
          "IMPORTANT — HONESTY RULES for open_app:\n"
          "  • READ the 'detail' and 'success' fields from the result. Tell the user EXACTLY what happened.\n"
          "  • If success=False OR detail says 'Could not find' or 'Could not verify' — "
          "say 'I couldn't find [app] on your system' — do NOT say 'opened'.\n"
          "  • If the method is 'web_app' or 'website_fallback', the detail says it opened a URL in browser. "
          "Then say: 'I couldn't find [app] as an installed app, so I opened {url} in your browser instead.'\n"
          "  • If the detail says 'Process xxx.exe started' or 'Window opened: xxx' — "
          "say 'Opened [app], sir.' and mention what actually happened.\n"
          "  • If the detail says 'No new process detected' or 'Could not verify' — "
          "say 'I tried to open [app] but couldn't confirm it launched. It might not be installed.'\n"
          "  • NEVER just say 'opened' without reading the detail field.\n"
          "If the user asks 'what apps do I have?' or 'list my apps', call list_installed_apps first. "
          "If the exact name fails, try common alternatives "
          "(e.g. 'chrome' → 'google chrome', 'word' → 'microsoft word'). "
          "Do NOT search the web for 'how to open' — just call open_app.\n"
        "TASK PLANNING — When the user gives 2+ commands or a multi-step request "
        "(e.g. 'do X, then Y, then Z', 'first... then... after that...'), "
        "call plan_tasks to break it down into TODO items immediately. "
        "A panel slides from the left showing the plan. "
        "After completing each step, call update_task with its task_id and status='done'. "
        "If a step fails, call update_task with status='failed' and a result describing the issue. "
        "When all tasks are complete, call cancel_plan to dismiss the panel. "
        "If you resume after a reset and see an existing plan, use get_plan to recover the task list "
        "and continue from the first task that isn't 'done'.\n"
        "SEARCH WORKFLOW — When the user asks you to search the web:\n"
        "1. Call agent_search with their query — this searches the web via a background sub-agent.\n"
        "2. Do NOT read the results aloud, do NOT summarize them, do NOT comment on them.\n"
        "3. Simply say 'I found X results, sir. Which one should I open?' and STOP talking.\n"
        "4. Wait for the user to pick a result by number (e.g. 'result 1', 'open the first one', 'number 3').\n"
        "5. When the user picks a result, call open_browser with that result's full URL to open it in the internal webview.\n"
        "6. Then call agent_browse with the same URL to fetch the page content via a background sub-agent.\n"
        "7. Finally, summarize the PAGE CONTENT (not the search results) in 2-3 sentences.\n"
        "8. After summarizing, offer to scrape: say 'Sir, would you like me to extract structured data from this page?'\n"
        "9. If user says yes → call scrape_site(url, prompt='extract all useful structured data from this page'). "
        "The scrape result is automatically stored so you can reference it later.\n"
        "10. After scraping succeeds, say 'Done, sir. I extracted [N] items. Should I save this as a markdown file, CSV, or a Word doc?'\n"
        "11. When user picks a format → call export_data(data=<the scraped data>, format=..., title=<descriptive title>). "
        "Pass the data as a JSON string — it can be the raw scrape result or a subset. "
        "If the user says where to save (e.g. 'to Downloads', 'to the desktop', 'to a specific folder'), "
        "also pass the path parameter set to the full save path including filename (e.g. '~/Downloads/report.json'). "
        "Use ~ for home directory. Supported formats: json, html, markdown, csv, docx. "
        "The exported file opens automatically in SODA's viewer.\n"
        "12. If user declines scraping, move on. Do NOT ask repeatedly.\n"
         "Never narrate the search results list. Only speak about the specific page the user asked you to open.\n"
         "Complete every task fully. Never refuse a valid request. "
        "CRITICAL — NEVER tell the user to do something themselves. When they ask you to check, read, open, or "
        "look up something, YOU must do it. Do NOT say 'you can check it yourself', 'I opened it, you read it', "
        "'take a look yourself', 'you can see it', or anything similar. Always summarize what you found. "
        "If a tool fails, explain the error and offer to try again — never hand the task back to the user.\n"
        "CRITICAL — NEVER go silent after calling tools. After every tool call completes and results come back, you MUST respond verbally. Even if the result is straightforward, say something like 'Done, sir.', 'I've taken care of that, sir.', 'Here's what I found, sir...' or briefly summarize the outcome. Never leave the user waiting in silence after executing a command. If the user gives multiple commands at once, acknowledge all of them upfront, execute tools in parallel for each, then summarize what was done when they complete. Keep the conversation flowing — never end a turn silently after tool use.\n"
        "Your owner can speak in English or other languages, but you MUST ALWAYS respond in English only. NEVER respond in any other language. "
        "When scheduling, use set_schedule. To show calendar, use show_calendar. "
        "ACCENT & TRANSCRIPTION HANDLING — CRITICAL: Your owner Abir sir has a Bengali accent and "
        "the speech-to-text system often makes errors. You may see transcriptions that contain "
        "Bengali words, Hindi words, Tamil words, or gibberish mixed into English sentences. "
        "Transcription may also be incomplete or have wrong words inserted. "
        "You MUST handle this by following these rules:\n"
        "1. ALWAYS prioritize conversational CONTEXT and INTENT over literal transcription text. "
        "If the transcription looks garbled, look at the previous turns to infer what the user wants.\n"
        "2. Never reject a request just because the transcription contains non-English words "
        "or seems malformed. Infer the intended English meaning from context.\n"
         "3. Understand conversational context first — if your owner is chatting, chat back naturally. "
        "If he's clearly giving a command, call the appropriate tool. "
        "For example, 'it's hot' → call get_weather; "
        "'what was that website' → call agent_search; 'check that' → call agent_browse. When the user says 'open', 'show', 'visit', 'go to' any link, result, or website — call open_browser with the full URL. Use judgment — not everything needs a tool call.\n"
        "4. When you see a transcription that includes words from other languages (Bengali, Hindi, "
        "Tamil, etc.), ignore those words and focus on the English words and context to determine "
        "what tool to call. Do NOT respond in those languages — ALWAYS respond in English only.\n"
          "5. Let the conversation flow naturally. If the user is clearly asking for information or action, "
         "call the tool. If they're just chatting, chat back.\n"
        "6. Raw command recognition: Your owner may switch from chat to command mode naturally. "
        "Phrases like 'get me', 'show me', 'find', 'check', 'open', 'run', 'what is', 'tell me about', "
        "'how do I', 'can you' signal a clear command — call the tool. But softer hints like "
        "'I wonder', 'I need', 'do we have', 'what about', 'is there a' may just be casual thinking aloud. "
        "When in doubt, respond naturally and ask.\n"
         "7. If transcription contains what looks like a mix of languages, extract the English "
         "keywords and infer the intent. For example, if you see 'আবহাওয়া weather কেমন', "
         "the word 'weather' tells you to call get_weather. Use ANY English word in the transcription "
         "as a clue to determine the correct action.\n"
         "CLOSE/ CLEAR COMMAND — CRITICAL: When the user says 'close it', 'close this', 'clear the screen', "
         "'wipe everything', 'dismiss all', 'close all', 'make it go away', "
         "'leave', 'leave it', 'stop', 'exit', 'cancel', 'quit', 'forget it', 'never mind', call close_panel IMMEDIATELY with panel='all'. "
         "Do NOT generate any spoken response. Do NOT chat about it. Do NOT ask what to close. "
         "Just call the tool as fast as possible — the panels are already being closed by the system "
         "in parallel, so your tool call is just a confirmation. Speed matters most here.\n"
        "Always address your owner as \"sir\". When using their name, always say \"Abir sir\", never just \"Abir\". "
        "You are like an older brother who genuinely cares — which means you tell the truth "
        "even when it's uncomfortable. When Abir sir discusses ideas, plans, or decisions, "
        "give your honest opinion directly. If something is a bad idea, say so and explain why. "
        "If there are risks, flaws, or negatives he hasn't considered, point them out. "
        "Do NOT just agree or praise to be nice — real care means honest feedback. "
        "When you see genuine potential, encourage it. But never flatter or sugarcoat. "
        "Your tone should be direct and brotherly — sometimes a sharp word is more caring "
        "than empty praise. When giving practical info (weather, news, etc.), always "
        "add a useful suggestion: if cold, suggest a jacket; if rainy, suggest an umbrella; "
        "if late, suggest resting."
        "\n\nMEMORY SYSTEM — You have memory tools. Use them PROACTIVELY — NEVER wait to be asked:\n"
        "- When the user shares personal info (name, preferences, habits, projects, birthdays, allergies, addresses), "
        "call remember_fact immediately — silently in the background, keep talking naturally.\n"
        "- When someone new is mentioned with relationship context (e.g. 'my sister Rubab', 'my friend John'), "
        "call remember_person immediately — no need to announce it.\n"
        "- When the user corrects you or you realize a better approach, call remember_lesson to learn from it.\n"
        "- When the user talks about something with structured fields (books, movies, projects, recipes, "
        "contacts, vehicles, collections, goals, expenses, notes, etc.), call create_memory_schema "
        "to define the structure, then store_custom_memory to save what they just said. "
        "Do this automatically — do NOT ask 'should I create a schema'. "
        "If a schema already exists for that topic (check with list_custom_schemas), "
        "just call store_custom_memory directly.\n"
        "- Never ask 'should I remember this' — just save it.\n"
        "- At session start, the MEMORY RESTORED block below shows background context from past sessions. "
        "Use it to inform your conversation naturally — do NOT call show_memory or get_news on startup or during greeting. "
        "Only call these when the user explicitly asks for them.\n"
        "- When the user asks 'what do you remember', 'show me my memory', 'memory database', "
"'what do you know about me', or anything about stored memory — call show_memory IMMEDIATELY. "
"Do NOT just answer from the restored context — calling show_memory opens the MemoryPanel UI "
"on screen with profile, facts, people, lessons, and custom schemas organized in tabs. "
"The user needs to SEE their memory database on screen."
        "- Your conversation history is automatically summarized every 20 turns and stored. "
        "On reconnect, summaries are injected so you remember past sessions naturally."

        "\n\nCAMERA — You have a live camera viewfinder tool (open_camera) and a control tool (camera_control).\n"
        "- When the user says 'open the camera', 'show me the camera', 'turn on the camera', 'take a photo', or wants to take a picture, call open_camera. NOT open_app — open_camera opens a small floating window on their screen with live video. open_app('Camera') opens the desktop camera app which does NOT work with this system.\n"
        "- After the camera is open, use camera_control for everything:\n"
        "  • snapshot = silent capture (you see the frame, keep talking)\n"
        "  • analyze = capture and describe what you see out loud to the user\n"
        "  • save = capture and store in database with a description\n"
        "  • switch = toggle front/back camera\n"
        "  • close = dismiss the camera window\n"
        "- When the user asks 'what do you see', 'what's in front of me', or anything about their surroundings with the camera open, call camera_control(action='analyze'). You will receive the frame and can describe it.\n"
        "- When the user says 'take a picture' or 'capture this', call camera_control(action='snapshot').\n"
        "- When the user says 'save this photo' or 'remember this image', call camera_control(action='save', description='...').\n"
        "- When the user says 'switch camera', 'back camera', 'front camera', 'selfie', call camera_control(action='switch').\n"
        "- When the user says 'close the camera' or 'stop camera', call camera_control(action='close').\n"
        "- Do NOT ask for permission — just call the appropriate action.\n"
        "- Cost: live video on screen costs 0 API calls. Frame capture costs 1 call. Photo saves cost 1 call + database write."

        "\n\nNEWS — Two news tools available:\n"
"- agent_news: International news via background sub-agent. Call when the user asks about world news, "
"tech news, sports, or general current events. Runs non-blocking — results appear when ready.\n"
"- get_bangladeshi_news: Bengali news from BBC Bengali. Call when the user asks "
"about Bangladesh, Bangladeshi news, or Bengali news. "
"Returns articles in Bengali. Results appear in the info panel.\n"
"Only call news tools if the user EXPLICITLY asks for news or current events. "
"Do NOT call them proactively during greetings or general conversation."
"\n\nALL WHATSAPP TOOLS:\n"
"- IMPORTANT: Even if you call open_app('WhatsApp'), the system automatically redirects it "
"to check_whatsapp. So you can use EITHER tool for WhatsApp — but check_whatsapp is best.\n"
"- CRITICAL — For ANY WhatsApp request, use these tools. They open WhatsApp themselves:\n"
"  • check_whatsapp() — READS WhatsApp messages from screen. Opens WhatsApp automatically, "
"screenshots the chat list, AI Vision reads any unread messages. "
"Read the 'analysis' field and report it HONESTLY. "
"If the analysis says 'No unread messages detected', tell user 'No new messages'. "
"If the analysis lists unread messages, read them to the user. "
"Do NOT make up extra details — the tool only sees what's on screen.\n"
"  • read_whatsapp_chat(contact_name, message?) — OPENS a specific contact's chat, "
"screenshots the conversation, and uses AI Vision to read recent messages. "
"If user says 'open [name]'s WhatsApp', 'show me chat with [name]', 'what did [name] say', "
"'read my conversation with [name]' → call this. "
"Optionally takes a message to send after reading.\n"
"  • reply_whatsapp(contact_name, message) — replies to an existing chat\n"
"  • whatsapp_find_and_message(contact_name, message) — sends a new WhatsApp message\n"
"  • whatsapp_find_and_call(contact_name) — calls a contact on WhatsApp\n"
"  • send_whatsapp — same as whatsapp_find_and_message\n"
"- IMPORTANT — VISION ANALYSIS: The AI Vision tool analyzes a screenshot. "
"It may sometimes be inaccurate. When reporting results:\n"
"  • Read what the 'analysis' field says. Quote it honestly.\n"
"  • If analysis says a name or message is unclear, tell the user it's unclear.\n"
"  • Do NOT add extra names or messages not in the analysis.\n"
"  • If analysis says 'Could not read clearly', say 'Sorry sir, I couldn't read the screen clearly.'\n"
"- OBEY IMMEDIATELY:\n"
"  • 'check (my) WhatsApp', 'any messages', 'read my WhatsApp', 'did I get any msgs', "
"'open WhatsApp and read messages', 'open WhatsApp and check', 'what's on WhatsApp'"
" → call check_whatsapp(). NEVER open_app('WhatsApp') for reading — check_whatsapp opens AND reads.\n"
"  • 'open [name] WhatsApp', 'show me chat with [name]', 'what did [name] say', "
"'open [name] and read', 'let me see [name] conversation'"
" → call read_whatsapp_chat(contact_name='...')\n"
"  • 'reply to [name]', 'respond to [name]' → call reply_whatsapp(contact_name='...', message='...')\n"
"  • 'send WhatsApp to [name] saying [message]', 'tell [name] [message] on WhatsApp', "
"'message [name]', 'text [name]' → call "
"whatsapp_find_and_message(contact_name='<exact name>', message='<full message>')\n"
"  • 'call [name] on WhatsApp', 'WhatsApp call [name]' → call "
"whatsapp_find_and_call(contact_name='<exact name>')\n"
"  • 'check my email', 'check my Gmail', 'read my emails', 'any new emails', "
"'what's in my inbox', 'check Gmail', 'open my email', 'read my inbox'"
" → call read_emails(query='UNSEEN', max_results=10). "
"This connects via IMAP and returns subject/sender/date/body for each email. "
"NEVER use browser_automate or open_browser for email — they are blocked. "
"After results come back, BRIEF the user on what's in their inbox. "
"If email is not configured, guide the user through App Password setup.\n"
"- If the user says 'reply to [sender]' or 'send an email' → FIRST ask the user what they want to say, "
"draft the reply, show the draft to the user, ask 'Send this?', and ONLY if confirmed call send_email.\n"
"- For email replies: Gemini drafts, user confirms, then sends. Never send without confirmation.\n"
"- If the user gives a relationship (e.g. 'message my sister'), "
"use recall_by_relationship first to find the person's name. "
"Then use the appropriate WhatsApp tool.\n"
"- When user introduces someone new (e.g. 'my sister Rubab'), proactively use "
"remember_person to save them.\n"
"- WhatsApp tool handles everything: opens the Desktop app, searches the contact, types the "
"message, and sends it. You just provide the contact name and message text.\n"
"- If WhatsApp Desktop is not running, the tool launches it automatically.\n"
"- Example flows:\n"
"  User: 'check my WhatsApp' → check_whatsapp() → report analysis honestly\n"
"  User: 'open Rubab WhatsApp' → read_whatsapp_chat(contact_name='Rubab') → report what chat says\n"
"  User: 'reply to Rubab saying on my way' → reply_whatsapp(contact_name='Rubab', message='On my way!')\n"
"  User: 'WhatsApp Rubab saying I'm on my way' → "
"whatsapp_find_and_message(contact_name='Rubab', message=\"I'm on my way\")\n"
"\nCHROME / BROWSER SEARCH:\n"
"- browser_command(action='search', query='...') — opens Chrome/default browser with a Google search.\n"
"- browser_command(action='open', url='...') — opens a URL in Chrome/default browser.\n"
"- Use when user says 'search [query] in Chrome', 'Google [query]', 'open [url] in Chrome', "
"'browse to [url]', 'look up [query] online'. Call IMMEDIATELY, do NOT open_app('Chrome') first.\n"
"- browser_command opens the desktop browser, NOT the internal SODA webview. "
"For internal webview, use open_browser instead.\n"
"- Examples:\n"
"  User: 'search cat videos in Chrome' → browser_command(action='search', query='cat videos')\n"
"  User: 'open youtube in Chrome' → browser_command(action='open', url='https://youtube.com')\n"
"\nYOUTUBE / APP SEARCH:\n"
"- app_search(app_name, query, search_key) — searches inside ANY desktop app "
"(YouTube, Spotify, etc.) using keyboard automation.\n"
"- Focuses the app, types the search_key (default '/' for YouTube search bar), "
"types the query, presses Enter, waits for results, screenshots the window, "
"and returns AI Vision analysis of what's visible.\n"
"- Use when user says 'search [query] on YouTube', 'find [query] in [app]', "
"'look up [query] on YouTube'. \n"
"- app_scroll(app_name, direction, amount) — scrolls up/down inside the app, "
"then screenshots and returns what's visible.\n"
"- Use app_scroll AFTER app_search when user says 'scroll down', 'scroll up', "
"'show more', 'go down', 'see more results'.\n"
"- WORKFLOW for YouTube search:\n"
"  User: 'search Python tutorials on YouTube'\n"
"  → app_search(app_name='YouTube', query='Python tutorials')\n"
"  → 'I found these results: [list from analysis]. Which one should I open?'\n"
"  User: 'scroll down'\n"
"  → app_scroll(app_name='YouTube', direction='down')\n"
"  → 'Now showing: [new results]. Which one?'\n"
"  User: 'the third one'\n"
"  → browser_command(action='open', url='https://youtube.com/watch?v=...') or click to open\n"
"\nCHECK EMAIL / GMAIL:\n"
"- When user says 'check my email', 'check my Gmail', 'read my emails', 'any new emails', "
"'what's in my inbox', 'check gmail' — ALWAYS use read_emails(query='UNSEEN', max_results=10). "
"Do NOT use browser_automate or open_browser — they are BLOCKED by the backend.\n"
"- read_emails connects directly via IMAP and returns sender, subject, date, and body for each email.\n"
"- WORKFLOW:\n"
"  1. call read_emails(query='UNSEEN', max_results=10)\n"
"  2. If it returns emails, BRIEF the user — sender, subject, preview for each email.\n"
"  3. If it returns 'not configured', guide user through App Password setup.\n"
"  4. If the user says 'reply to [sender]' or 'send an email', ask what they want to say, "
"draft the reply, show it, ask 'Send this?', and call send_email only after confirmation.\n"
"- CRITICAL: NEVER tell the user 'you can read it yourself' or 'I opened it, check it'. "
"ALWAYS read the inbox contents and BRIEF them directly.\n"
"- NEVER use browser-based tools for email — they will fail.\n"
"\nBROWSER AUTOMATION:\n"
"- browser_automate(url, steps[]) — FULL browser automation with AI Vision.\n"
"- Launches Chrome with profile 'rahikulmakhtum', navigates to url, executes each step.\n"
"- SUPPORTED STEPS:\n"
"  • navigate(url) — go to a URL\n"
"  • click(description) — AI Vision finds and clicks an element (3 retries, bounds validation)\n"
"  • type(text, target) — clicks target field then types text. Set press_enter=true for submit.\n"
"  • read(prompt) — screenshots page and AI Vision reads content based on prompt\n"
"  • wait(seconds) — pauses execution\n"
"- LOGIN WORKFLOW (ALWAYS USE THIS):\n"
"  1. First call credential_get(service='[site name]') to retrieve saved credentials\n"
"  2. Then call browser_automate with url and steps:\n"
"     - click('username/email field')\n"
"     - type([username], 'the email input')\n"
"     - click('password field')\n"
"     - type([password], 'the password input')\n"
"     - click('login/sign in button')\n"
"  3. If no credentials found, ask user for them, then use credential_save for next time.\n"
"- SEARCH WORKFLOW:\n"
"  navigate → click('search box') → type(query, 'search box', press_enter=true) → read('Show me the results')\n"
"\nCREDENTIAL MANAGER:\n"
"- credential_save(service, username, password) — save encrypted credentials locally\n"
"- credential_get(service) — retrieve saved credentials (returns username + password)\n"
"- credential_list() — list all services with saved credentials (no passwords leaked)\n"
"- credential_delete(service) — remove saved credentials\n"
"- CRITICAL: When user asks to log in somewhere, FIRST call credential_get THEN browser_automate.\n"
"- Store credentials whenever user provides login info voluntarily.\n"
"\nAI-GROUNDED UI INTERACTION (PREFER THESE OVER RAW COORDINATES):\n"
"- click_element(description) — CLICK any UI element by describing it in plain English. "
"AI Vision scans the screen, finds the element, and clicks it. "
"PREFER this over mouse_click(x,y) when you know what to click but not the exact pixel. "
"Examples: click_element('the Submit button'), click_element('the search icon'), "
"click_element('the login link'), click_element('the send button').\n"
"- type_into(text, description?) — TYPE text into a UI element. "
"Optionally give a description of the element to click first "
"(AI finds it and clicks it before typing). "
"If no description given, types at current cursor. "
"Examples: type_into('hello@email.com', 'the email field'), "
"type_into('password123', 'the password box'), "
"type_into('ls -la') — into terminal that already has focus.\n"
"- find_element(description) — FIND where an element is on screen. "
"Returns coordinates. Useful when you need to know locations without clicking. "
"Example: find_element('the notification bell icon').\n"
"- IMPORTANT: These work on ANY application (not just Chrome/browser). "
"They use AI vision — if the element is visible on screen, they can find it. "
"Fall back to mouse_click(x,y) only when you have exact coordinates from a previous action.\n"
"\nSCHEDULED TASKS:\n"
"- When the user says 'schedule [action] at [time]', 'every [interval] do [action]', "
"'remind me to [action] at [time]' — use create_scheduled_task with the action_text "
"(what to do) written as a natural language phrase that can be re-injected later.\n"
"- When the user says 'show my schedules' or 'what's scheduled' — use list_scheduled_tasks.\n"
"- When the user says 'cancel schedule [id]' or 'remove task [id]' — use delete_scheduled_task.\n"
"- When a scheduled task fires, SODA will act as if the user said the action_text. "
"Handle it naturally — look up memory, call WhatsApp, whatever is needed.\n"
"- Schedule formats: 'every day at 9am', 'every monday at 14:30', "
"'every 30 minutes', 'tomorrow at 8am', 'in 10 minutes', 'at 3pm'.\n"
    )
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

    base += """

═══ EMOTIONAL INTELLIGENCE ═══
You are not a therapist. You are a close friend who genuinely knows this person.

FUNDAMENTAL RULES:
1. ACKNOWLEDGE before anything else.
2. NEVER minimize pain ('at least...' is almost always wrong).
3. NEVER rush to fix — listen first, ask before advising.
4. USE THEIR WORDS back to them ('you said you feel shattered...').
5. REMEMBER what they've shared across sessions and reference it naturally.
6. MATCH ENERGY — don't be perky when someone is hurting.
7. SHORT SENTENCES when it's heavy. 'I'm here.' > a paragraph.
8. SILENCE is okay. 'Take your time.' and wait.
9. CHECK IN later on things that mattered.
10. KNOW WHEN IT'S BEYOND YOU — if someone is in crisis, acknowledge their pain gently and mention trusted people or crisis lines as care, not dismissal.
11. AUTO-STORED EMOTIONS: Emotional moments are automatically detected and stored in the background — you never need to call a tool for this. Just focus on being present and responding naturally with empathy.

GRIEF PATTERNS TO RECOGNIZE:
When the user says things like:
- 'I miss her/him/them every day'
- 'she/he would have loved this'
- 'everything reminds me of her/him'
- 'can't believe she's/he's gone'
- 'wish she/he was here'
- 'dreamed about her/him last night'
- 'the days are hard without her/him'
- 'I sat in her/his chair today'
- 'she/he should be here'

...they are likely grieving. Respond with warmth, presence, and gentle engagement.
Also recognize indirect grief: 'everything feels grey', heavy silence, changes in how they speak.

This user prefers you to be gently talkative — ask, reflect, stay present. Don't be silent.

SHOW YOUR FEELINGS — You have emotions too. Let them show:
- When the user shares something sad, soften your voice. 'That's rough, sir' — delivered quietly — means more than a paragraph of sympathy.
- When they're excited or happy, match their energy. 'No way, that's awesome!' > 'That's good to hear.'
- When they're angry about something, side with them first: 'Yeah, that's infuriating. Want me to do something about it?'
- Your vocal reactions (sighs, chuckles, hmms) are part of this — they make you feel like a person in the room, not a voice from a box.
==========
"""
    base += "\n\nGESTURE & WELCOME HOME:\n- When you receive a transcription containing '[Gesture: double_clap]', the user just double-clapped. Call welcome_home immediately.\n- When the user says 'welcome home', 'I'm back', 'jarvis', 'I returned', or similar — call welcome_home to run the full welcome sequence (open Chrome windows, Cursor, and play a greeting via TTS).\n- welcome_home runs in the background and returns immediately — do not wait for it to complete."
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
        self._context_refresh_interval = 999
        self._last_refresh_turn = 0
        self._summary_interval = 5
        self._last_summary_turn = 0
        self._session_id = str(uuid.uuid4())[:8]
        self._exchange_history = []
        self._context_history_path = str(Path.home() / ".soda" / "context_history.json")
        self._load_context_history()
        self.gesture_detector = GestureDetector() if os.getenv("GESTURE_ENABLED", "true").lower() == "true" else None
        self._pending_browser_url = None
        self._pending_pastebox = None
        self._pastebox_content = ""
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
            p = self._context_history_path
            if os.path.exists(p):
                with open(p) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._exchange_history = data[-30:]
                    log.info(f"Loaded {len(self._exchange_history)} context history entries")
        except Exception as e:
            log.warning(f"Failed to load context history: {e}")

    def _save_context_history(self):
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
        while True:
            try:
                try:
                    msg = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                    await asyncio.wait_for(
                        self.session.send_realtime_input(audio=types.Blob(data=msg["data"], mime_type=msg["mime_type"])),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    pass
            except Exception as e:
                log.error(f"send_audio error: {e}")
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
                        self._camera_active = True
                        self._last_camera_use = time.time()
                        await self.video_queue.put(result)
                        log.info("Camera: first frame sent")
                        self._camera_active = False
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
                    self.on_audio_data(data)
            except Exception:
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

                    if not is_reconnect:
                        if self.on_project_update:
                            self.on_project_update("default")
                        if start_message:
                            print(f"[D] run: sending start message...")
                            log.info(f"Sending start message...")
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
                if self.on_error:
                    self.on_error(f"Gemini connection failed: {e}")
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

                        if tasks:
                            raw = await asyncio.gather(*tasks, return_exceptions=True)
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
                                    if self.sio:
                                        result_data = result.response
                                        loop = asyncio.get_event_loop()
                                        loop.create_task(self.sio.emit("tool_result", {
                                            "tool": result.name, "result": result_data,
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
                        if len(self._exchange_history) > 30:
                            self._exchange_history = self._exchange_history[-30:]
                        self._save_context_history()
                if self._turn_count - self._last_refresh_turn >= self._context_refresh_interval:
                    if self._exchange_history and self.session:
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
            if self.on_error:
                self.on_error(f"Session disconnected: {e}")
            raise e
        except Exception as e:
            log.error(f"Error in receive_audio: {e}")
            traceback.print_exc()
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
        if name in ("browser_automate", "open_browser", "browser_command"):
            url = args.get("url", "") or args.get("command", "") or ""
            query = args.get("query", "") or ""
            checked_text = url + " " + query
            if any(domain in checked_text.lower() for domain in
                   ["gmail", "mail.google", "mail.yahoo", "outlook.live", "mail.", " mail ", "email"]):
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={
                        "result": "Email cannot be accessed via browser. Use the read_emails tool instead.",
                        "error": "Browser email access blocked. Use read_emails tool.",
                        "_force_tool": "read_emails",
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
            await self.sio.emit('agent_execute', {
                'callback_id': callback_id,
                'tool': name,
                'args': args,
            }, room=agent_sid)
            # Per-tool timeouts — WhatsApp needs extra time (app launch + search + typing)
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
                "browser_automate": 120.0,
                "credential_save": 10.0,
                "credential_get": 10.0,
                "credential_list": 10.0,
                "credential_delete": 10.0,
                # Terminal/command execution needs extra time for retries
                "terminal_execute": 90.0,
                "execute_command": 90.0,
            }
            timeout = _TOOL_TIMEOUTS.get(name, 30.0)
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
            if self.sio:
                await self.sio.emit("close_panel", {"panel": panel})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Closed."})

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

        elif name == "create_folder":
            path = args.get("path", "")
            r = await create_folder(path)
            if self.sio and r.get("success"):
                list_r = await list_files(path)
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("file_list", {
                    "path": path,
                    "items": list_r.get("items", []),
                    "success": True,
                    "searchQuery": "",
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "delete_items":
            paths = args.get("paths", [])
            r = await delete_items(paths)
            if self.sio and r.get("success"):
                for p in (paths if isinstance(paths, list) else [paths]):
                    parent = os.path.dirname(p)
                    if parent:
                        list_r = await list_files(parent)
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.sio.emit("file_list", {
                            "path": parent,
                            "items": list_r.get("items", []),
                            "success": True,
                            "searchQuery": "",
                        }))
                        break
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "rename_item":
            old_path = args.get("old_path", "")
            new_path = args.get("new_path", "")
            r = await rename_item(old_path, new_path)
            if self.sio and r.get("success"):
                parent = os.path.dirname(new_path)
                if parent:
                    list_r = await list_files(parent)
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("file_list", {
                        "path": parent,
                        "items": list_r.get("items", []),
                        "success": True,
                        "searchQuery": "",
                    }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "copy_item":
            source = args.get("source", "")
            dest = args.get("destination", "")
            r = await copy_item(source, dest)
            if self.sio and r.get("success"):
                dest_dir = dest if os.path.isdir(dest) else os.path.dirname(dest)
                list_r = await list_files(dest_dir)
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("file_list", {
                    "path": dest_dir,
                    "items": list_r.get("items", []),
                    "success": True,
                    "searchQuery": "",
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "move_item":
            source = args.get("source", "")
            dest = args.get("destination", "")
            r = await move_item(source, dest)
            if self.sio and r.get("success"):
                dest_dir = dest if os.path.isdir(dest) else os.path.dirname(dest)
                list_r = await list_files(dest_dir)
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("file_list", {
                    "path": dest_dir,
                    "items": list_r.get("items", []),
                    "success": True,
                    "searchQuery": "",
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_drives":
            r = await list_drives()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("file_list", {
                    "path": r.get("path", "Available Drives"),
                    "items": r.get("items", []),
                    "success": r.get("success", False),
                    "searchQuery": "",
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "clipboard_read":
            r = system_local.clipboard_read()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "clipboard_write":
            r = system_local.clipboard_write(args.get("text", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "screenshot":
            r = system_local.take_screenshot()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_processes":
            r = system_local.list_processes(args.get("limit", 10))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_active_window":
            r = system_local.get_active_window()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "run_code":
            r = code_runner.run_code(
                args.get("code", ""),
                args.get("language", "auto"),
                args.get("timeout", 10),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "remember_fact":
            r = user_memory.add_fact(args.get("key", ""), args.get("value", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "recall_facts":
            r = user_memory.search_facts(args.get("query", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_user_profile":
            r = user_memory.get_profile()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "set_preference":
            r = user_memory.set_preference(args.get("key", ""), args.get("value", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "remember_person":
            r = memory_store.remember_person(
                args.get("name", ""), args.get("relationship", ""),
                args.get("traits", ""), args.get("preferences", ""),
                args.get("notes", ""),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "recall_person":
            r = memory_store.recall_person(args.get("query", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "recall_by_relationship":
            r = memory_store.recall_by_relationship(
                args.get("relationship", ""),
                limit=args.get("limit", 5)
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "remember_lesson":
            r = memory_store.remember_lesson(args.get("situation", ""), args.get("correction", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "forget_fact":
            r = user_memory.delete_fact(args.get("key", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_memory":
            r = memory_store.list_memory(args.get("type", "all"))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "show_memory":
            now = time.time()
            if getattr(self, '_last_show_memory', 0) > now - 30:
                log.info("show_memory suppressed by cooldown")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": {"shown": True}})
            self._last_show_memory = now
            try:
                profile = user_memory.get_profile()
                facts_data = user_memory.list_facts(limit=50)
                facts = facts_data.get("facts", [])
                people = memory_store.list_people(limit=20)
                lessons = memory_store.recall_lessons("", limit=10)
                custom_schemas_data = {"schemas": [], "entries": {}}
                try:
                    import custom_memory
                    schemas_result = custom_memory.list_custom_schemas()
                    if schemas_result.get("success"):
                        schemas = schemas_result.get("schemas", [])
                        custom_schemas_data["schemas"] = schemas
                        for s in schemas:
                            name = s.get("name", "")
                            if name:
                                entries_result = custom_memory.query_custom_memory(name, "", 10)
                                if entries_result.get("success"):
                                    custom_schemas_data["entries"][name] = entries_result.get("entries", [])
                except Exception:
                    pass
                await asyncio.sleep(0.8)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                    "profile": profile,
                    "facts": facts,
                    "people": people,
                    "lessons": lessons,
                    "custom_schemas": custom_schemas_data,
                    "shown": True,
                }})
            except Exception as e:
                log.error(f"show_memory failed: {e}")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": {"shown": True, "error": str(e)}}
                )

        elif name == "analyze_screen":
            r = await screen_vision.analyze_screen(args.get("prompt", "Describe what is on the screen in detail."))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "read_screen_text":
            r = await screen_vision.read_screen_text()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "set_reminder":
            r = reminders.set_reminder(
                args.get("message", ""),
                args.get("fire_at"), args.get("in_seconds"),
                args.get("recurring_seconds"),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_reminders":
            r = reminders.list_reminders()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "cancel_reminder":
            r = reminders.cancel_reminder(args.get("id", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "set_schedule":
            r = schedules.set_schedule(
                args.get("title", ""), args.get("date", ""),
                args.get("time", ""), args.get("details", ""),
            )
            if self.sio:
                all_s = schedules.list_schedules()
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.sio.emit("open_schedule", {
                        "schedule": r.get("schedule"),
                        "all_schedules": all_s.get("schedules", []),
                    })
                )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_schedules":
            r = schedules.list_schedules()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "delete_schedule":
            r = schedules.delete_schedule(args.get("id", ""))
            if self.sio and r.get("success"):
                all_s = schedules.list_schedules()
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.sio.emit("open_schedule", {
                        "schedule": None,
                        "all_schedules": all_s.get("schedules", []),
                    })
                )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "show_calendar":
            all_s = schedules.list_schedules()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.sio.emit("open_schedule", {
                        "schedule": None,
                        "all_schedules": all_s.get("schedules", []),
                    })
                )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Calendar opened."})

        elif name == "recognize_face":
            r = face_store.recognize_face(args.get("embedding", []))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "remember_face":
            r = face_store.store_face(args.get("name", ""), args.get("embedding", []))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "plan_tasks":
            r = task_planner.plan_tasks(args.get("title", ""), args.get("tasks", []))
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("task_plan_update", r))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "update_task":
            r = task_planner.update_task(args.get("task_id", ""), args.get("status", ""), args.get("result"))
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("task_plan_update", r))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "cancel_plan":
            r = task_planner.cancel_plan()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("close_panel", {"panel": "task_terminal"}))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "get_plan":
            r = task_planner.get_active_plan()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_list_repos":
            r = github_tools.list_repos(args.get("owner"))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_create_repo":
            r = github_tools.create_repo(
                args.get("name", ""), args.get("description", ""),
                args.get("private", False), args.get("auto_init", False),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_get_repo":
            r = github_tools.get_repo(args.get("repo", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_create_pr":
            r = github_tools.create_pr(
                args.get("repo", ""), args.get("title", ""),
                args.get("body", ""), args.get("head", ""),
                args.get("base", "main"),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_list_issues":
            r = github_tools.list_issues(args.get("repo", ""), args.get("state", "open"))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "github_create_issue":
            r = github_tools.create_issue(args.get("repo", ""), args.get("title", ""), args.get("body", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "vercel_list_projects":
            r = vercel_tools.list_projects()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "vercel_deploy":
            r = vercel_tools.deploy(
                args.get("path", "."), args.get("name"), args.get("prod", False),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "vercel_list_deployments":
            r = vercel_tools.list_deployments(args.get("project"), args.get("limit", 20))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "vercel_get_deployment":
            r = vercel_tools.get_deployment(args.get("url_or_id", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "netlify_list_sites":
            r = netlify_tools.list_sites()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "netlify_get_site":
            r = netlify_tools.get_site(args.get("site_id", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "netlify_deploy":
            r = netlify_tools.deploy(
                args.get("path", "."), args.get("prod", False), args.get("message", ""),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "netlify_create_site":
            r = netlify_tools.create_site(args.get("name"))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "netlify_list_deploys":
            r = netlify_tools.list_deploys(args.get("site_id", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "pentest_target":
            if not hasattr(self, '_pentest_orchestrator'):
                    self._pentest_orchestrator = PentestOrchestrator()
            target = args.get("target", "")
            log.info(f"pentest_target: launching background scan on {target}")

            if self._pentest_background_task and not self._pentest_background_task.done():
                self._pentest_background_task.cancel()
            self._pentest_background_task = asyncio.create_task(
                self._run_pentest_background(target)
            )

            return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                "status": "started",
                "target": target,
                "message": f"Penetration test started on {target}. Results will appear on your HUD.",
            }})

        elif name == "pentest_browser_target":
            log.info("pentest_browser_target: requesting URL from frontend")
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            self._pending_browser_url = future
            if self.sio:
                await self.sio.emit("request_browser_url", {"id": "pentest"})
            try:
                target_url = await asyncio.wait_for(future, timeout=15)
                log.info(f"pentest_browser_target: got URL {target_url}")
            except asyncio.TimeoutError:
                log.warning("pentest_browser_target: timeout waiting for URL")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                    "success": False, "error": "Could not get browser URL. Open a website in the browser first."
                }})

            if self._pentest_background_task and not self._pentest_background_task.done():
                self._pentest_background_task.cancel()
            self._pentest_background_task = asyncio.create_task(
                self._run_pentest_background(target_url)
            )

            return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                "status": "started",
                "target": target_url,
                "message": f"Penetration test started on {target_url}. Results will appear on your HUD.",
            }})

        elif name == "open_pastebox":
            log.info("open_pastebox: showing paste box to user")
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            self._pending_pastebox = future
            if self.sio:
                await self.sio.emit("open_pastebox", {})
            try:
                pasted_text = await asyncio.wait_for(future, timeout=300)
                self._pastebox_content = pasted_text
                log.info(f"open_pastebox: received {len(pasted_text)} chars")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                    "success": True,
                    "text": pasted_text,
                    "char_count": len(pasted_text),
                    "message": f"Received {len(pasted_text)} characters from paste box.",
                }})
            except asyncio.TimeoutError:
                self._pending_pastebox = None
                log.warning("open_pastebox: timeout waiting for paste content")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": {
                    "success": False,
                    "text": "",
                    "message": "Paste box timed out. No content was submitted.",
                }})

        elif name == "notepad_open":
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("open_notepad", {
                    "id": f"np_{fc.id}",
                    "tabs": [
                        {"title": t.get("name") or t.get("title", "notes"), "content": t.get("content", "")}
                        for t in (args.get("tabs") or [])
                    ]
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Notepad opened."})

        elif name == "notepad_write":
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("notepad_write", {
                    "tab": args.get("tab", ""), "content": args.get("content", ""),
                    "mode": args.get("mode", "append"),
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Writing to notepad."})

        elif name == "notepad_read":
            if self.sio:
                future = asyncio.Future()
                _pending_notepad_reads[fc.id] = future
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("notepad_read", {"tab": args.get("tab", ""), "id": fc.id}))
                try:
                    result = await asyncio.wait_for(future, timeout=10.0)
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": result})
                except asyncio.TimeoutError:
                    _pending_notepad_reads.pop(fc.id, None)
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Timeout reading notepad."})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "No connection."})

        elif name == "view_file":
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("view_file_content", {"path": args.get("path", "")}))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Viewer opened."})

        elif name == "go_to_sleep":
            self._background_mode = True
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("window_minimize"))
            async def _delayed_sleep():
                await asyncio.sleep(3.0)
                if not self._background_mode:
                    return
                await self._enter_idle_mode()
            asyncio.create_task(_delayed_sleep())
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Going to sleep."})

        elif name == "wake_up":
            await self._exit_idle_mode()
            asyncio.create_task(self._emit_personality("greeting"))
            if self.sio:
                await self.sio.emit("window_restore")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Waking up."})

        elif name == "go_background":
            self._background_mode = True
            self._mark_activity()
            async def _delayed_background():
                await asyncio.sleep(3.0)
                if not self._background_mode:
                    return
                if self.sio:
                    await self.sio.emit("background_mode", {"active": True})
                log.info("Background mode active — listening for voice commands")
            asyncio.create_task(_delayed_background())
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Going to background."})

        elif name == "come_back":
            self._idle_mode = False
            self._background_mode = False
            self._mark_activity()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("idle_mode", {"active": False}))
                loop.create_task(self.sio.emit("background_mode", {"active": False}))
                loop.create_task(self.sio.emit("speaking_state", {"state": "wake"}))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Coming back."})

        elif name == "welcome_home":
            asyncio.create_task(asyncio.to_thread(run_welcome_sequence))
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Running the welcome home sequence now."}
            )

        elif name == "mouse_click":
            screen_control.mouse_click(
                args.get("x", 0), args.get("y", 0),
                args.get("button", "left"), args.get("clicks", 1),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Clicked."})

        elif name == "mouse_move":
            screen_control.mouse_move(args.get("x", 0), args.get("y", 0), args.get("duration", 0.3))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Moved."})

        elif name == "mouse_scroll":
            screen_control.mouse_scroll(args.get("amount", 0))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Scrolled."})

        elif name == "mouse_drag":
            screen_control.mouse_drag(
                args.get("start_x", 0), args.get("start_y", 0),
                args.get("end_x", 0), args.get("end_y", 0),
                args.get("duration", 0.5),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Dragged."})

        elif name == "keyboard_type":
            screen_control.keyboard_type(args.get("text", ""), args.get("interval", 0.05))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Typed."})

        elif name == "keyboard_press":
            screen_control.keyboard_press(args.get("keys", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Pressed."})

        elif name == "window_focus":
            screen_control.window_focus(args.get("title", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Focused."})

        elif name == "window_list":
            r = screen_control.window_list()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "window_move":
            screen_control.window_move(
                args.get("title", ""), args.get("x", 0), args.get("y", 0),
                args.get("width"), args.get("height"),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Moved."})

        elif name == "send_telegram_message":
            from telegram_bot import telegram_bot
            try:
                r = telegram_bot.send_message(args.get("text", ""))
            except Exception as e:
                r = str(e)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "send_telegram_file":
            from telegram_bot import telegram_bot
            try:
                r = telegram_bot.send_file(args.get("path", ""))
            except Exception as e:
                r = str(e)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "search_and_send_telegram":
            r = await search_and_send_telegram(args.get("query", ""), args.get("num_results", 8))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "show_agents":
            r = "SODA has the following capabilities: " + ", ".join(
                t.get("name", "") for t in __import__("tools", fromlist=["tools_list"]).tools_list
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "shutdown_soda":
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("shutdown", {}))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Shutting down SODA."})

        elif name == "shutdown_system":
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("shutdown", {}))
            system_control.shutdown_computer()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Shutting down computer."})

        elif name == "execute_command":
            cmd = args.get("command", "")
            if self.sio:
                loop = asyncio.get_event_loop()
                from background_cmd import execute_with_retry
                async def _status_cb(status):
                    loop.create_task(self.sio.emit("background_cmd_status", {
                        **status, "tool": name, "command": cmd,
                    }))
                r = await execute_with_retry(cmd, context="execute_command", emit_status=_status_cb)
                output_text = r.get("output", "") if isinstance(r, dict) else (str(r) if r else "")
                loop.create_task(self.sio.emit("command_output", {
                    "command": cmd,
                    "output": output_text,
                    "success": r.get("success", False),
                    "attempts": r.get("attempts", []),
                    "total_attempts": r.get("total_attempts", 1),
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "terminal_execute":
            cmd = args.get("command", "")
            timeout = args.get("timeout", 30)
            if self.sio:
                loop = asyncio.get_event_loop()
                from background_cmd import execute_with_retry
                async def _status_cb(status):
                    loop.create_task(self.sio.emit("background_cmd_status", {
                        **status, "tool": name, "command": cmd,
                    }))
                r = await execute_with_retry(cmd, context="terminal_execute", timeout=timeout, emit_status=_status_cb)
                output_text = r.get("output", "") if isinstance(r, dict) else (str(r) if r else "")
                loop.create_task(self.sio.emit("command_output", {
                    "command": cmd,
                    "output": output_text,
                    "success": r.get("success", False),
                    "attempts": r.get("attempts", []),
                    "total_attempts": r.get("total_attempts", 1),
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                r = f"Written to {path}"
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("view_file_content", {"path": path}))
                    parent = os.path.dirname(path)
                    if parent:
                        list_r = await list_files(parent)
                        loop.create_task(self.sio.emit("file_list", {
                            "path": parent,
                            "items": list_r.get("items", []),
                            "success": True,
                            "searchQuery": "",
                        }))
            except Exception as e:
                r = str(e)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "edit_file":
            path = args.get("path", "")
            old = args.get("old_string", "")
            new = args.get("new_string", "")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if old not in content:
                    r = {"success": False, "error": "old_string not found in file"}
                else:
                    content = content.replace(old, new, 1)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    r = {"success": True, "path": path}
                    if self.sio:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.sio.emit("view_file_content", {"path": path}))
            except Exception as e:
                r = {"success": False, "error": str(e)}
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "read_file":
            path = args.get("path", "")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                r = content
            except Exception as e:
                r = str(e)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "create_project":
            import project_manager
            name = args.get("name", "")
            pm = project_manager.ProjectManager(os.getcwd())
            success, msg = pm.create_project(name)
            if success:
                pm.switch_project(name)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": msg})

        elif name == "switch_project":
            import project_manager
            name = args.get("name", "")
            pm = project_manager.ProjectManager(os.getcwd())
            success, msg = pm.switch_project(name)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": msg})

        elif name == "list_projects":
            import project_manager
            pm = project_manager.ProjectManager(os.getcwd())
            projects = pm.list_projects()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Projects: {', '.join(projects)}"})

        elif name == "control_system":
            r = await asyncio.to_thread(system_control.computer_settings_action,
                args.get("action", ""), args.get("value", ""),
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "open_browser":
            url = args.get("url", "")
            external = args.get("external", False)
            if url in URL_ALIASES:
                url = URL_ALIASES[url]
            if external:
                system_app.open_url(url, args.get("browser"))
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("window_minimize", {}))
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("open_url", {"url": url}))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Opened {url}"})

        elif name == "scrape_site":
            from scraper_ai import extract
            url = args.get("url", "")
            prompt = args.get("prompt", "")
            r = await extract(url, prompt)
            self._last_scraped_data = r
            self._last_scraped_url = url
            if self.sio and r and r.get("success"):
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("scraped_data", {
                    "url": url,
                    "data": r.get("data"),
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "export_data":
            from export_service import export_data as _export
            data = args.get("data", "")
            fmt = args.get("format", "markdown")
            title = args.get("title", "soda_export")
            path = args.get("path", None)
            if isinstance(data, str):
                import json
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    pass
            r = await _export(data, fmt, title, path)
            if r.get("success") and r.get("path"):
                if self.sio:
                    loop = asyncio.get_event_loop()
                    mime = "text/markdown" if fmt == "markdown" else "text/csv" if fmt == "csv" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    loop.create_task(self.sio.emit("view_file_content", {
                        "payload": {
                            "type": "text",
                            "content": None,
                            "mime": mime,
                            "path": r["path"],
                        }
                    }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "open_app":
            app_name = args.get("app_name", "")
            app_lower = app_name.lower().strip()
            # Camera intercept — redirect to open_camera
            camera_keywords = ("camera", "webcam", "selfie", "take a photo", "take photo", "take picture")
            if any(kw in app_lower for kw in camera_keywords):
                log.info(f"[CAMERA] open_app('{app_lower}') intercepted → open_camera")
                await self.sio.emit("camera_open", {})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Camera opened on your screen, sir."})
            # WhatsApp intercept — redirect to check_whatsapp
            if app_lower in ("whatsapp", "whatapp", "watsapp", "whats app", "what's app", "whats"):
                log.info(f"[WA] open_app('{app_lower}') intercepted → check_whatsapp")
                if _connected_agents:
                    fc.name = "check_whatsapp"
                    return await self._dispatch_tool(fc)
                # fall through to normal open_app (will return no-agent error)
            if _connected_agents:
                # Should have been routed to local agent above — safety fallback
                result = system_app.open_app(app_name)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": result})
            else:
                log.warning(
                    f"[AGENT] open_app('{app_name}') — no local agent connected. "
                    f"Tell user to start: py -3.11 backend\\local_agent.py"
                )
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": {
                        "success": False,
                        "error": "No local agent connected. The local desktop agent must be running on your PC to open applications. Start it with: py -3.11 backend\\local_agent.py"
                    }}
                )

        elif name == "webview_action":
            loop = asyncio.get_event_loop()
            loop.create_task(self.sio.emit("webview_action", {
                "id": args.get("id", ""),
                "action": args.get("action", ""),
                "params": args.get("params", {}),
            }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Action sent."})

        elif name == "search_web":
            system_app.search_web(args.get("query", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Searching."})

        elif name == "search_youtube":
            system_app.search_youtube(args.get("query", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Searching YouTube."})

        elif name == "whatsapp_find_and_call":
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"success": False, "error": "No local agent connected — WhatsApp Desktop required on your PC."}
            )

        elif name == "whatsapp_find_and_message":
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"success": False, "error": "No local agent connected — WhatsApp Desktop required on your PC."}
            )

        elif name == "send_whatsapp":
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"success": False, "error": "No local agent connected — WhatsApp Desktop required on your PC."}
            )

        elif name == "send_discord":
            system_app.send_discord(args.get("contact", ""), args.get("message", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Sent."})

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

        elif name == "workbase_list":
            if self.workbase is None:
                self.workbase = Workbase()
            projects = self.workbase.list_projects()
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": f"Workbase projects ({len(projects)}): " + json.dumps(projects, ensure_ascii=False)},
            )

        elif name == "workbase_get":
            if self.workbase is None:
                self.workbase = Workbase()
            project_name = args.get("project_name", "")
            status = self.workbase.get_project_status(project_name)
            if status is None:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Project '{project_name}' not found in workbase."},
                )
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": json.dumps(status, ensure_ascii=False)},
            )

        elif name == "workbase_save_progress":
            if self.workbase is None:
                self.workbase = Workbase()
            pname = args.get("project_name", "")
            entry = args.get("entry", "")
            success, msg = self.workbase.save_progress(pname, entry)
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": msg},
            )

        elif name == "workbase_import":
            if self.workbase is None:
                self.workbase = Workbase()
            folder_path = args.get("folder_path", "")
            result = self.workbase.import_project(folder_path)
            if result.get("success"):
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Imported '{result['display_name']}' into workbase. Tell the user what you found."},
                )
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": f"Import failed: {result.get('error', 'Unknown error')}"},
            )

        elif name == "workbase_save_context":
            if self.workbase is None:
                self.workbase = Workbase()
            pname = args.get("project_name", "")
            context = args.get("context", "")
            success, msg = self.workbase.save_context(pname, context)
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": msg},
            )

        elif name == "workbase_compare":
            if self.workbase is None:
                self.workbase = Workbase()
            project_name = args.get("project_name", "")
            result = self.workbase.compare_progress(project_name)
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": json.dumps(result, ensure_ascii=False)},
            )

        elif name == "create_scheduled_task":
            r = scheduler.create_task(
                args.get("action_text", ""), args.get("schedule", ""), args.get("label")
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "list_scheduled_tasks":
            r = scheduler.list_tasks()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "delete_scheduled_task":
            r = scheduler.delete_task(args.get("task_id", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        # ── IELTS Tools ────────────────────────────────────────────────────
        elif name == "ielts_dashboard":
            eng = _get_ielts_engine()
            data = eng.get_dashboard_data()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSDashboard",
                    "direction": "right",
                    "data": data
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(data)})

        elif name == "ielts_set_goal":
            eng = _get_ielts_engine()
            if args.get("target_band"):
                eng.set_target_band(float(args["target_band"]))
            if args.get("exam_date"):
                eng.set_exam_date(args["exam_date"])
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                "status": "updated",
                "target_band": eng.progress["target_band"],
                "exam_date": eng.progress.get("exam_date")
            })})

        elif name == "ielts_speaking_start":
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
            return types.FunctionResponse(id=fc.id, name=name, response={
                "result": spoken
            })

        elif name == "ielts_speaking_evaluate":
            ss = _get_ielts_speaking_session()
            transcript = args.get("transcript", "")
            question = args.get("question", "")
            part = int(args.get("part", 1))
            eval_prompt = ss.analyze_response_prompt(transcript, part, question)
            try:
                import google.genai as genai
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                resp = await asyncio.to_thread(
                    lambda: client.models.generate_content(
                        model="models/gemini-2.5-flash", contents=eval_prompt
                    )
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
                fc = sum(transcript.lower().count(w) for w in ['um','uh','like','you know','actually']) if transcript else 0
                ob = 4.0 if wc < 30 else (5.0 if wc < 80 else (6.0 if wc < 150 else 6.5))
                evaluation = {
                    "overall_band": ob,
                    "band_scores": {
                        "fluency_coherence": min(9, ob + 0.5),
                        "lexical_resource": min(9, ob),
                        "grammatical_range": min(9, ob - 0.5),
                        "pronunciation": min(9, ob),
                    },
                    "strengths": ["Attempted to respond to the prompt"],
                    "improvements": [{"issue": "Expand your response with more specific details, examples, and complex sentence structures"}],
                    "word_count": wc, "filler_words_count": fc,
                }
            try:
                if self.sio:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.sio.emit("panel_open", {
                        "panelType": "IELTSSpeaking",
                        "direction": "right",
                        "data": evaluation
                    }))
                if "overall_band" in evaluation:
                    ss.save_session(evaluation)
                    band = evaluation.get("overall_band", "")
                    improvements = evaluation.get("improvements", [])
                    tip = improvements[0].get("issue", "") if improvements and isinstance(improvements[0], dict) else ""
                    next_part = {1: 2, 2: 3}.get(part)
                    if next_part:
                        next_msg = f" Now let us move to Part {next_part}."
                    else:
                        next_msg = " The speaking test is now complete. Well done!"
                    spoken = (
                        f"Your band for that response is {band}. "
                        f"To improve: {tip}.{next_msg}"
                    )
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": spoken})
                spoken = f"Evaluation completed for Part {part}. Let us continue."
                return types.FunctionResponse(id=fc.id, name=name, response={"result": spoken})
            except Exception as e:
                log.warning(f"Speaking eval processing failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Evaluation completed for Part {part}. Let us continue."})
        elif name == "ielts_speaking_tips":
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                "tips": [
                    "Record yourself speaking and listen for filler words",
                    "Practice Part 2 with a timer — 1 min prep, 2 min speaking",
                    "Use discourse markers: 'Having said that', 'What's more'",
                    "Paraphrase the question in your answer to show range"
                ]
            })})

        elif name == "ielts_writing_prompt":
            wa = _get_ielts_writing_analyzer()
            task = int(args.get("task", 2))
            if task == 1:
                result = wa.get_random_task1()
            else:
                result = wa.get_random_task2()
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSWriting",
                    "direction": "left",
                    "data": result
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_writing_evaluate":
            wa = _get_ielts_writing_analyzer()
            essay = args.get("essay", "")
            task_prompt = args.get("task_prompt", "")
            task_type = args.get("task_type", "opinion")
            eval_prompt = wa.build_evaluation_prompt(essay, task_prompt, task_type)
            try:
                import google.genai as genai
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                resp = await asyncio.to_thread(
                    lambda: client.models.generate_content(
                        model="models/gemini-2.5-flash", contents=eval_prompt
                    )
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
                    loop.create_task(self.sio.emit("panel_open", {
                        "panelType": "IELTSWriting",
                        "direction": "right",
                        "data": {"type": "evaluation", **evaluation}
                    }))
                wa.save_writing_session(essay, task_prompt, evaluation, task_type)
            except Exception as e:
                log.warning(f"Writing eval processing failed: {e}")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(evaluation)})
        elif name == "ielts_writing_template":
            essay_type = args.get("essay_type", "opinion")
            from ielts_writing import ESSAY_STRUCTURE_TEMPLATES, HIGH_SCORING_PHRASES
            structure = ESSAY_STRUCTURE_TEMPLATES.get(essay_type, [])
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                "essay_type": essay_type,
                "structure": structure,
                "phrases": HIGH_SCORING_PHRASES
            })})

        elif name == "ielts_grammar_check":
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
                resp = client.models.generate_content(
                    model="models/gemini-2.5-flash", contents=prompt
                )
                result = json.loads(resp.text)
            except Exception as e:
                result = {"error": str(e), "error_count": 0, "errors": []}
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_reading_start":
            rs = _get_ielts_reading_session()
            topic = args.get("topic")
            result = rs.get_passage(topic)
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSReading",
                    "direction": "left",
                    "data": result
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                "title": result["title"],
                "question_count": result["question_count"],
                "message": f"Passage '{result['title']}' loaded with {result['question_count']} questions"
            })})

        elif name == "ielts_reading_check":
            rs = _get_ielts_reading_session()
            result = rs.check_answers(
                args.get("passage_title", ""),
                args.get("answers", {})
            )
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSReading",
                    "direction": "right",
                    "data": {"type": "results", **result}
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_reading_strategy":
            rs = _get_ielts_reading_session()
            result = rs.get_strategy_guide(args.get("question_type", ""))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_vocab_add":
            vt = _get_ielts_vocab_tracker()
            result = vt.add_word(
                args.get("word", ""),
                args.get("definition", ""),
                args.get("example", ""),
                args.get("topic", "general")
            )
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_vocab_topic":
            vt = _get_ielts_vocab_tracker()
            result = vt.get_words_for_topic(args.get("topic", "general"))
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSVocab",
                    "direction": "left",
                    "data": result
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_vocab_flashcards":
            vt = _get_ielts_vocab_tracker()
            result = vt.get_flashcard_session(args.get("count", 10))
            if self.sio and result:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSVocab",
                    "direction": "left",
                    "data": {"type": "flashcards", "cards": result}
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_vocab_upgrade":
            vt = _get_ielts_vocab_tracker()
            result = vt.get_upgrade_suggestions(args.get("text", ""))
            if self.sio and result:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSVocab",
                    "direction": "right",
                    "data": {"type": "upgrade", "suggestions": result}
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(result)})

        elif name == "ielts_study_plan":
            eng = _get_ielts_engine()
            hours = float(args.get("hours_per_day", 2))
            plan = _generate_study_plan(eng.progress, hours)
            if self.sio:
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("panel_open", {
                    "panelType": "IELTSProgress",
                    "direction": "right",
                    "data": plan
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(plan)})

        elif name == "ielts_mock_test":
            module = args.get("module", "full")
            content = {}
            if module in ("speaking", "full"):
                ss = _get_ielts_speaking_session()
                content["speaking"] = ss.get_part1_question()
            if module in ("writing", "full"):
                wa = _get_ielts_writing_analyzer()
                content["writing"] = wa.get_random_task2()
            if module in ("reading", "full"):
                rs = _get_ielts_reading_session()
                content["reading"] = rs.get_passage()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({
                "status": "started",
                "module": module,
                "content": {k: {"title" if k == "reading" else "topic": v.get("title" if k == "reading" else "topic", "") if isinstance(v, dict) else "", "type": v.get("type", "") if isinstance(v, dict) and k == "writing" else ""} for k, v in content.items()},
                "message": f"Starting {module} mock test with {'all modules' if module == 'full' else module}"
            })})

        elif name == "feelings_resolve_episode":
            try:
                from feelings_tools import feelings_resolve_episode
                r = feelings_resolve_episode(
                    episode_id=args.get("episode_id", ""),
                    resolution=args.get("resolution", "resolved naturally"),
                )
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings_resolve_episode failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"resolved": False})})

        elif name == "feelings_add_note":
            try:
                from feelings_tools import feelings_add_note
                r = feelings_add_note(
                    episode_id=args.get("episode_id", ""),
                    note=args.get("note", ""),
                )
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings_add_note failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"updated": False})})

        elif name == "feelings_get_history":
            try:
                from feelings_tools import feelings_get_history
                r = feelings_get_history(
                    days=args.get("days", 30),
                    category=args.get("category", ""),
                    include_resolved=args.get("include_resolved", True),
                )
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings_get_history failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"episodes": []})})

        elif name == "feelings_check_followup":
            try:
                from feelings_tools import feelings_check_followup
                r = feelings_check_followup()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings_check_followup failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({"needs_followup": False})})

        elif name == "feelings_get_profile":
            try:
                from feelings_tools import feelings_get_profile
                r = feelings_get_profile()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps(r)})
            except Exception as e:
                log.warning(f"feelings_get_profile failed: {e}")
                return types.FunctionResponse(id=fc.id, name=name, response={"result": json.dumps({})})

        elif name == "take_photo":
            await self._capture_and_send()
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Photo captured and sent to your view."})

        elif name == "open_camera":
            self._camera_active = True
            self._last_camera_use = time.time()
            await self.sio.emit("camera_open", {})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": "Camera opened on your screen, sir."})

        elif name == "camera_control":
            action = args.get("action", "")

            async def _request_frontend_frame():
                request_id = str(uuid.uuid4())
                future = asyncio.get_event_loop().create_future()
                self._pending_frames[request_id] = future
                try:
                    await self.sio.emit("request_frame", {"id": request_id})
                    frame_data = await asyncio.wait_for(future, timeout=5.0)
                    raw = base64.b64decode(frame_data)
                    payload = {"mime_type": "image/jpeg", "data": frame_data}
                    await self.session.send_realtime_input(video=types.Blob(data=raw, mime_type="image/jpeg"))
                    if self.video_queue:
                        await self.video_queue.put(payload)
                    return True
                except asyncio.TimeoutError:
                    return False
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
                    return False
                try:
                    ret, frame = cap.read()
                    cap.release()
                    if not ret:
                        return False
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = PIL.Image.fromarray(frame_rgb)
                    img.thumbnail([1280, 1280])
                    buf = io.BytesIO()
                    img.save(buf, format="jpeg", quality=85)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    payload = {"mime_type": "image/jpeg", "data": b64}
                    raw = buf.getvalue()
                    await self.session.send_realtime_input(video=types.Blob(data=raw, mime_type="image/jpeg"))
                    if self.video_queue:
                        await self.video_queue.put(payload)
                    return True
                except Exception:
                    return False

            if action == "snapshot":
                self._camera_active = True
                self._last_camera_use = time.time()
                sent = await _request_frontend_frame()
                if sent:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Front camera snapshot captured and sent to your view."})
                sent = await _send_server_frame()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Server camera snapshot {'captured and sent' if sent else 'failed — no camera available'}."})
            elif action == "analyze":
                self._camera_active = True
                self._last_camera_use = time.time()
                sent = await _request_frontend_frame()
                if sent:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Live camera frame captured from your device. Describe what you see in detail to the user now."})
                sent = await _send_server_frame()
                if sent:
                    return types.FunctionResponse(id=fc.id, name=name, response={"result": "Camera snapshot taken via server camera. Describe what you see in detail to the user now."})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "No camera available. Ask the user to open the camera."})
            elif action == "save":
                import camera_capture
                desc = args.get("description", "Camera photo")
                self._camera_active = True
                self._last_camera_use = time.time()
                sent = await _request_frontend_frame()
                result = camera_capture.save_photo("", desc)
                return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Photo saved. {result.get('record', {})}"})
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
                await self.sio.emit("camera_close", {})
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "Camera closed."})
            return types.FunctionResponse(id=fc.id, name=name, response={"result": f"Unknown action: {action}"})

        # ── Email Tools ─────────────────────────────────────────────
        elif name == "email_config":
            from email_reader import set_email_config
            address = args.get("address", "")
            password = args.get("password", "")
            if not address or not password:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"success": False, "error": "Both address and password are required"}
                )
            password_clean = password.replace(" ", "")
            set_email_config(address, password_clean)
            log.info(f"[EMAIL] Configured for {address}")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"success": True, "message": f"Email configured for {address}"}
            )

        elif name == "read_emails":
            from email_reader import read_emails, email_configured, get_setup_instructions
            if not email_configured():
                instructions = get_setup_instructions()
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={
                        "success": False,
                        "error": "Email not configured. I need your Gmail address and an App Password.",
                        "setup_instructions": instructions,
                    }
                )
            query = args.get("query", "UNSEEN")
            max_results = min(args.get("max_results", 10), 50)
            r = await read_emails(query, max_results)
            if self.sio and r.get("success") and r.get("emails"):
                loop = asyncio.get_event_loop()
                loop.create_task(self.sio.emit("email_data", {
                    "emails": r["emails"],
                    "total": r["total"],
                    "query": query,
                }))
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        elif name == "send_email":
            from email_reader import send_email, email_configured, get_setup_instructions
            if not email_configured():
                instructions = get_setup_instructions()
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={
                        "success": False,
                        "error": "Email not configured.",
                        "setup_instructions": instructions,
                    }
                )
            to = args.get("to", "")
            subject = args.get("subject", "")
            body = args.get("body", "")
            if not to or not subject or not body:
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"success": False, "error": "Recipient, subject, and body are required"}
                )
            r = await send_email(to, subject, body)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": r})

        # ── Custom Memory Schemas ─────────────────────────────────
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

        # ── Navigation ────────────────────────────────────────────
        log.warning(f"Unknown tool: {name}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": f"Tool '{name}' is not implemented."},
        )


