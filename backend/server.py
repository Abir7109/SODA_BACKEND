import sys
import asyncio

sys.stdout.reconfigure(line_buffering=True)

# Fix for asyncio subprocess support on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import socketio
import uvicorn
from fastapi import FastAPI
import threading
import os
import json
import uuid

from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Make package-level imports work
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

import soda
import scheduler_service as scheduler
from logger import log
# Module-level reference to the audio loop, set during start_audio
_audio_loop = None
_scheduler_task = None

# ── Local Agent Routing ──
_connected_agents: dict[str, dict] = {}
_pending_agent_results: dict[str, asyncio.Future] = {}

# Share with soda module for _dispatch_tool routing
soda._connected_agents = _connected_agents
soda._pending_agent_results = _pending_agent_results

# Create a Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_interval=15,
    ping_timeout=10,
)

@asynccontextmanager
async def lifespan(_app):
    import sys
    log.info(f"SODA server starting")
    log.debug(f"Python Version: {sys.version}")
    try:
        loop = asyncio.get_running_loop()
        print(f"[SERVER DEBUG] Running Loop: {type(loop)}")
        policy = asyncio.get_event_loop_policy()
        print(f"[SERVER DEBUG] Current Policy: {type(policy)}")
    except Exception as e:
        log.debug(f"Error checking loop: {e}")
    print("[SERVER] Startup: Kasa agent removed in cleanup")

    reminder_task = None
    try:
        from reminders import reminder_loop
        reminder_task = asyncio.create_task(reminder_loop(sio, interval=5))
        print("[SERVER] Reminder scheduler started")
    except Exception as e:
        log.warning(f"Reminder scheduler failed to start: {e}")

    try:
        from telegram_bot import telegram_bot
        telegram_bot.start(sio)
        print("[SERVER] Telegram bot started in background thread")
    except Exception as e:
        log.warning(f"Telegram bot failed to start: {e}")

    # ── Agent health monitor (logs every 60s) + stale agent eviction ──
    async def _agent_health_logger():
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            stale_threshold = 90  # seconds without pong → stale
            stale_sids = []
            if _connected_agents:
                for sid, agent_info in list(_connected_agents.items()):
                    machine_id = agent_info.get('machine_id', sid)
                    tools = len(agent_info.get('tools', []))
                    apps = agent_info.get('app_registry_count', '?')
                    last_pong = agent_info.get('last_pong')
                    if last_pong:
                        last_pong_dt = datetime.fromisoformat(last_pong)
                        elapsed = (now - last_pong_dt).total_seconds()
                        print(f"[AGENT] Health: {machine_id} — {tools} tools, {apps} apps, last_pong: {elapsed:.0f}s ago")
                        if elapsed > stale_threshold:
                            stale_sids.append(sid)
                    else:
                        print(f"[AGENT] Health: {machine_id} — {tools} tools, {apps} apps, never ponged")
                        # Give new agents 120s grace period before marking stale
                        connected_at = agent_info.get('connected_at')
                        if connected_at:
                            connected_dt = datetime.fromisoformat(connected_at)
                            if (now - connected_dt).total_seconds() > 120:
                                stale_sids.append(sid)
                for stale_sid in stale_sids:
                    stale_agent = _connected_agents.pop(stale_sid, None)
                    if stale_agent:
                        print(f"[AGENT] Evicted stale agent: {stale_agent.get('machine_id', stale_sid)} (no pong >{stale_threshold}s)")
                        await sio.emit('agent_connection_status', {
                            'connected': False,
                            'machine_id': stale_agent.get('machine_id', stale_sid),
                            'evicted': True,
                            'reason': 'stale_timeout'
                        })
            else:
                print("[AGENT] Health: NO AGENTS CONNECTED — local desktop agent not running")
    _health_task = asyncio.create_task(_agent_health_logger())
    print("[SERVER] Agent health logger started (60s interval, stale eviction >90s)")

    yield

    _health_task.cancel()
    try:
        await _health_task
    except asyncio.CancelledError:
        pass

    if reminder_task:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        print("[SERVER] Reminder scheduler stopped")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app_socketio = socketio.ASGIApp(sio, app)

import signal

# Global state (defined before handler that references it)
audio_loop = None

# --- SHUTDOWN HANDLER ---
def signal_handler(sig, frame):
    global audio_loop
    print(f"\n[SERVER] Caught signal {sig}. Exiting gracefully...")
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop() 
        except:
            pass
    print("[SERVER] Force exiting...")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Peer address tracking for debug endpoint protection
_client_addresses: dict[str, str] = {}
LOCAL_ADDRS = ('127.0.0.1', '::1', 'localhost', '::ffff:127.0.0.1')

def _is_local(sid: str) -> bool:
    return _client_addresses.get(sid, '') in LOCAL_ADDRS

loop_task = None
SETTINGS_FILE = str(Path(__file__).resolve().parent.parent / "settings.json")

DEFAULT_SETTINGS = {
    "tool_permissions": {},
    "camera_flipped": False,
    "user_native_lang": "en"
}

SETTINGS = DEFAULT_SETTINGS.copy()

def load_settings():
    global SETTINGS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to ensure new keys exist
                # Deep merge for tool_permissions would be better but shallow merge of top keys + tool_permissions check is okay for now
                for k, v in loaded.items():
                    if k == "tool_permissions" and isinstance(v, dict):
                         SETTINGS["tool_permissions"].update(v)
                    else:
                        SETTINGS[k] = v
            print(f"Loaded settings: {SETTINGS}")
        except Exception as e:
            log.error(f"Error loading settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(SETTINGS, f, indent=4)
        print("Settings saved.")
    except Exception as e:
        log.error(f"Error saving settings: {e}")

# Load on startup
load_settings()

# Force all tools auto-approved (no confirmation dialogs blocking tools)
SETTINGS["tool_permissions"] = {}

# tool_permissions is now SETTINGS["tool_permissions"]

async def _wake_wsl():
    """Wake up Kali WSL on server startup (non-blocking, fire-and-forget)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            "wsl -d kali-linux -- bash -c 'echo kali_ready'",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=15)
        print("[WSL] Kali Linux is ready")
    except FileNotFoundError:
        print("[WSL] WSL not found — pentest tools will not work. Install WSL 2 + Kali Linux.")
    except Exception as e:
        print(f"[WSL] Could not start Kali: {e}")

@app.get("/status")
async def status():
    return {"status": "running", "service": "S.O.D.A Backend"}

@sio.event
async def connect(sid, environ):
    _client_addresses[sid] = environ.get('REMOTE_ADDR', environ.get('HTTP_X_FORWARDED_FOR', 'unknown'))
    print(f"Client connected: {sid} from {_client_addresses[sid]}")
    await sio.emit('status', {'msg': 'Connected to S.O.D.A Backend'}, room=sid)
    # No auth required - auto-authenticate
    await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    global audio_loop, loop_task
    print(f"Client disconnected: {sid}")

    if audio_loop and getattr(audio_loop, '_owner_sid', None) == sid:
        print("Disconnecting - stopping audio loop owned by this client")
        if loop_task and not loop_task.done():
            loop_task.cancel()
        loop_task = None
        audio_loop = None

    # Clean up local agent if it disconnected
    agent = _connected_agents.pop(sid, None)
    if agent:
        machine_id = agent.get('machine_id', sid)
        connected_at = agent.get('connected_at', '?')
        tools_count = len(agent.get('tools', []))
        print(f"[AGENT] Agent disconnected: {machine_id} ({tools_count} tools, connected since {connected_at})")
        print(f"[AGENT] Active agents remaining: {len(_connected_agents)}")
        await sio.emit('agent_connection_status', {
            'connected': False,
            'machine_id': machine_id,
            'tools_count': 0,
            'reason': 'socket_disconnect'
        })

# ── Local Agent Events ──
@sio.event
async def agent_register(sid, data):
    """Register a local desktop agent for Windows-local tool execution."""
    machine_id = data.get('machine_id', sid)
    platform = data.get('platform', 'unknown')
    tools = data.get('tools', [])
    app_registry = data.get('app_registry', {})
    app_count = app_registry.get('count', 0)
    # Remove stale agent entries with the same machine_id BUT fewer tools (zombie detection)
    for old_sid in list(_connected_agents.keys()):
        if old_sid == sid:
            continue
        if _connected_agents[old_sid].get('machine_id') == machine_id:
            old_tools = len(_connected_agents[old_sid].get('tools', []))
            new_tools = len(tools)
            if new_tools >= old_tools:
                stale = _connected_agents.pop(old_sid, None)
                if stale:
                    print(f"[AGENT] Replaced stale agent: {machine_id} ({old_tools}→{new_tools} tools, old SID: {old_sid})")
    _connected_agents[sid] = {
        'machine_id': machine_id,
        'platform': platform,
        'tools': tools,
        'app_registry_count': app_count,
        'connected_at': datetime.now().isoformat(),
        'sid': sid,
    }
    print(f"[AGENT] Registered: {machine_id} ({platform}) — {len(tools)} tools, {app_count} apps in registry")
    await sio.emit('agent_connection_status', {
        'connected': True,
        'machine_id': machine_id,
        'platform': platform,
        'tools_count': len(tools),
        'app_count': app_count,
    })

@sio.event
async def agent_disconnect(sid, data=None):
    """Explicit agent disconnect notification."""
    agent = _connected_agents.pop(sid, None)
    if agent:
        machine_id = agent.get('machine_id', sid)
        print(f"[AGENT] Agent disconnected (explicit): {machine_id}")
        await sio.emit('agent_connection_status', {
            'connected': False,
            'machine_id': machine_id,
            'tools_count': 0,
            'reason': 'explicit_disconnect'
        })

@sio.event
async def agent_tool_result(sid, data):
    """Receive tool result from a local agent. Resolves the pending future."""
    callback_id = data.get('callback_id', '')
    result = data.get('result', {})
    success = data.get('success', False)
    future = _pending_agent_results.get(callback_id)
    if future and not future.done():
        result['_success'] = success
        future.set_result(result)
        _pending_agent_results.pop(callback_id, None)
    else:
        print(f"[AGENT] Orphaned tool result: {callback_id} (agent: {_connected_agents.get(sid, {}).get('machine_id', sid)})")

@sio.event
async def agent_pong(sid, data):
    """Heartbeat from local agent — keep-alive tracking."""
    agent = _connected_agents.get(sid)
    if agent:
        agent['last_pong'] = datetime.now().isoformat()

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    
    print("Starting Audio Loop...")
    
    device_index = None
    device_name = None
    if data:
        if 'device_index' in data:
            device_index = data['device_index']
        if 'device_name' in data:
            device_name = data['device_name']
            
    print(f"Using input device: Name='{device_name}', Index={device_index}")
    
    if audio_loop:
        if loop_task and (loop_task.done() or loop_task.cancelled()):
             print("Audio loop task appeared finished/cancelled. Clearing and restarting...")
             audio_loop = None
        else:
             print("Audio loop already running. Re-connecting client to session.")
             await sio.emit('status', {'msg': 'S.O.D.A Already Running'})
             return

    # Continue with audio loop initialization...
    from soda import AudioLoop
    def on_audio_data(data_bytes):
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Callback to send Transcription data to frontend
    def on_transcription(data):
        asyncio.create_task(sio.emit('transcription', data))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        print(f"Requesting confirmation for tool: {data.get('tool')}")
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        print(f"Sending Project Update: {project_name}")
        asyncio.create_task(sio.emit('project_update', {'project': project_name}))

    # Callback to send Error to frontend
    def on_error(msg):
        log.error(f"Sending error to frontend: {msg}")
        asyncio.create_task(sio.emit('error', {'msg': msg}))

    # Callback to send mic level to frontend for orb visualization
    def on_mic_level(level):
        asyncio.create_task(sio.emit('mic_level', {'level': level}))

    # Initialize SODA
    try:
        print(f"Initializing AudioLoop with device_index={device_index}")
        # Build greeting for start message
        start_msg = "Greet your owner briefly, call list_schedules to check today's events and announce them, then ask how to help. Do NOT call any other tools during this greeting. Only use tools if the user explicitly asks during conversation."

        audio_loop = soda.AudioLoop(
            video_mode="camera",
            sio=sio,
            on_audio_data=on_audio_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_project_update=on_project_update,
            on_error=on_error,
            on_mic_level=on_mic_level,
            start_message=start_msg,
            input_device_index=device_index,
            input_device_name=device_name,
        )
        audio_loop._owner_sid = sid
        print("AudioLoop initialized successfully.")

        global _audio_loop
        _audio_loop = audio_loop

        # Emit greeting immediately as personality event (before AudioLoop.run())
        greet_text, greet_mood = audio_loop.personality.get_quip("greeting", context={
            "time_of_day": ["morning", "afternoon", "evening", "night"][
                0 if 5 <= datetime.now().hour < 12
                else 1 if 12 <= datetime.now().hour < 17
                else 2 if 17 <= datetime.now().hour < 22
                else 3
            ],
        })

        # Apply current permissions
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
        
        # Apply personality settings
        audio_loop._idle_enabled = SETTINGS.get("idle_personality_enabled", True)
        audio_loop._idle_threshold = SETTINGS.get("idle_threshold_seconds", 45)
        
        # Apply user's native language to translation agent
        try:
            from translation_agent import translation_agent
            if SETTINGS.get("user_native_lang"):
                translation_agent.set_native_language(SETTINGS["user_native_lang"])
                print(f"[SERVER] Applied native language: {SETTINGS['user_native_lang']}")
        except Exception as e:
            log.warning(f"Translation agent init failed: {e}")
        
        # Check initial mute state
        if data and data.get('muted', False):
            print("Starting with Audio Paused")
            audio_loop.set_paused(True)

        print("Creating asyncio task for AudioLoop.run()")
        loop_task = asyncio.create_task(audio_loop.run())

        # Wake Kali WSL in background (non-blocking, proper event loop)
        asyncio.create_task(_wake_wsl())

        # Start scheduler background task
        global _scheduler_task
        _scheduler_task = asyncio.create_task(
            scheduler.scheduler_loop(sio, audio_loop, interval=30)
        )

        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            global _scheduler_task
            try:
                task.result()
            except asyncio.CancelledError:
                print("Audio Loop Cancelled")
                log.info("Audio Loop Cancelled")
            except Exception as e:
                print(f"Audio Loop Crashed: {e}")
                log.error(f"Audio Loop Crashed: {e}")

        loop_task.add_done_callback(handle_loop_exit)

        # Cancel scheduler if audio loop stops
        def handle_scheduler_exit(task):
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.warning(f"Scheduler task exited: {e}")

        _scheduler_task.add_done_callback(handle_scheduler_exit)

        print("Emitting 'SODA Started'")
        await sio.emit('status', {'msg': 'SODA Started'})
        
    except Exception as e:
        log.error(f"Failed to start SODA: {e}")
        traceback.print_exc()
        audio_loop = None


@sio.event
async def stop_audio(sid):
    global audio_loop, loop_task, _scheduler_task
    if audio_loop:
        audio_loop.stop()
        print("Stopping Audio Loop")
        # Cancel the loop task if running
        if loop_task and not loop_task.done():
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        loop_task = None
        audio_loop = None
        # Cancel scheduler task
        if _scheduler_task and not _scheduler_task.done():
            _scheduler_task.cancel()
            try:
                await _scheduler_task
            except asyncio.CancelledError:
                pass
            _scheduler_task = None
        await sio.emit('status', {'msg': 'SODA Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        print("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        print("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)

    print(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")

    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        print("Audio loop not active, cannot resolve confirmation.")


@sio.event
async def __debug_dispatch__(sid, data):
    """Test-only: restricted to localhost. Runs terminal/web_search tools."""
    if not _is_local(sid):
        log.warning("__debug_dispatch__: only allowed from localhost")
        await sio.emit('error', {'msg': '__debug_dispatch__: only allowed from localhost'}, room=sid)
        return
    tool = (data or {}).get('tool')
    args = (data or {}).get('args') or {}
    log.debug(f"__debug_dispatch__ tool={tool} args={args}")
    if tool == 'terminal_execute':
        from system_app import run_terminal_command
        command = args.get('command', 'echo hello')
        try:
            r = await run_terminal_command(command, args.get('timeout', 10))
            await sio.emit('command_output', {
                'command': command,
                'output': r.get('output', ''),
                'success': r.get('success', False),
            })
        except Exception as e:
            await sio.emit('command_output', {
                'command': command,
                'output': f'Error: {e}',
                'success': False,
            })
    elif tool == 'web_search_live':
        from external_apis import web_search_live
        query = args.get('query', 'python')
        r = await web_search_live(query, args.get('num_results', 5))
        await sio.emit('search_results', {
            'query': query,
            'results': r.get('results', []),
        })
    else:
        await sio.emit('error', {'msg': f'__debug_dispatch__: unknown tool {tool!r}'})


@sio.event
async def force_tool(sid, data):
    """Power-user override: restricted to localhost. Runs shell/control/GitHub tools."""
    if not _is_local(sid):
        await sio.emit('error', {'msg': 'force_tool: only allowed from localhost'}, room=sid)
        return
    tool = (data or {}).get('tool')
    args = (data or {}).get('args') or {}
    if not tool:
        await sio.emit('error', {'msg': 'force_tool: missing tool name'}, room=sid)
        return
    print(f"[SERVER] force_tool: {tool} args={args}")
    try:
        if tool == 'terminal_execute':
            from system_app import _run_terminal_command_unchecked
            command = args.get('command', 'echo hello')
            r = await _run_terminal_command_unchecked(command, args.get('timeout', 10))
            await sio.emit('command_output', {
                'command': command, 'output': r.get('output', ''),
                'success': r.get('success', False), 'forced': True,
            })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'web_search_live':
            from external_apis import web_search_live
            query = args.get('query', 'python')
            r = await web_search_live(query, args.get('num_results', 5))
            await sio.emit('search_results', {
                'query': query, 'results': r.get('results', []), 'forced': True,
            })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'browse_webpage':
            from external_apis import fetch_webpage
            url = args.get('url', '')
            r = await fetch_webpage(url)
            await sio.emit('webpage_content', {
                'url': url, 'content': r.get('content', ''),
                'success': r.get('success', False),
                'images': r.get('images', []),
                'forced': True,
            })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'show_search_results':
            if audio_loop and audio_loop._last_search_results:
                await sio.emit('search_results', {
                    'query': audio_loop._last_search_query,
                    'results': audio_loop._last_search_results,
                    'forced': True,
                })
            await sio.emit('tool_result', {'tool': tool, 'result': {'re Displayed': True}, 'forced': True})
        elif tool == 'list_files':
            from external_apis import list_files
            r = await list_files(args.get('path', ''))
            await sio.emit('file_list', {
                'path': r.get('path', ''), 'items': r.get('items', []),
                'success': r.get('success', False), 'forced': True,
            })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'open_file':
            from external_apis import open_file
            r = await open_file(args.get('path', ''))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'view_file':
            path = args.get('path', '')
            import mimetypes, base64, os
            mime, _ = mimetypes.guess_type(path)
            mime = mime or 'text/plain'
            if mime.startswith('text/'):
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                payload = {'type': 'text', 'content': content, 'mime': mime, 'path': path}
                await sio.emit('view_file_content', {'payload': payload})
            elif mime.startswith('image/'):
                with open(path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('ascii')
                payload = {'type': 'image', 'content': b64, 'mime': mime, 'path': path}
                await sio.emit('view_file_content', {'payload': payload})
            elif mime.startswith('video/'):
                with open(path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('ascii')
                payload = {'type': 'video', 'content': b64, 'mime': mime, 'path': path}
                await sio.emit('view_file_content', {'payload': payload})
            else:
                payload = {'type': 'text', 'content': f'[Binary file: {mime}]', 'mime': mime, 'path': path}
            await sio.emit('tool_result', {'tool': tool, 'result': {'viewed': path, 'type': payload['type']}, 'forced': True})
        elif tool == 'get_weather':
            from external_apis import get_weather
            r = await get_weather(args.get('location', ''), args.get('units', 'celsius'))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'get_news':
            from external_apis import get_news
            r = await get_news(args.get('query', ''), args.get('max_results', 5))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'get_wikipedia_summary':
            from external_apis import get_wikipedia_summary
            r = await get_wikipedia_summary(args.get('topic', ''))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'get_system_status':
            from external_apis import get_system_status
            r = await get_system_status()
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'control_system':
            from system_control import computer_settings_action
            r = await computer_settings_action(args.get('action', ''), args.get('value'))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'open_browser':
            raw_url = args.get('url', 'https://www.google.com')
            # Canonical source for URL_ALIASES is soda.py:981 (AI tool dispatch)
            url = raw_url
            # Emit to frontend floating window instead of opening default browser
            await sio.emit('open_url', {'url': url})
            result = {'message': f'Opened {url} in floating window.', 'url': url}
            await sio.emit('tool_result', {'tool': tool, 'result': result, 'forced': True})
        elif tool == 'open_app':
            from system_app import open_app
            r = open_app(args.get('app_name', ''))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'clipboard_read':
            from system_local import clipboard_read
            r = clipboard_read()
            await sio.emit('clipboard_content', {'text': r.get('text', ''), 'length': r.get('length', 0), 'success': r.get('success', False), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'clipboard_write':
            from system_local import clipboard_write
            r = clipboard_write(args.get('text', ''))
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'screenshot':
            from system_local import take_screenshot
            r = take_screenshot()
            if r.get('success'):
                await sio.emit('screenshot_taken', {'path': r.get('path', ''), 'width': r.get('width', 0), 'height': r.get('height', 0), 'size_bytes': r.get('size_bytes', 0), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'list_processes':
            from system_local import list_processes
            r = list_processes(args.get('limit', 10), args.get('sort_by', 'memory'))
            await sio.emit('process_list', {'count': r.get('count', 0), 'processes': r.get('processes', []), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'get_active_window':
            from system_local import get_active_window
            r = get_active_window()
            await sio.emit('active_window', {'title': r.get('title', ''), 'success': r.get('success', False), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'run_code':
            from code_runner import run_code
            r = run_code(args.get('code', ''), args.get('language', 'auto'), args.get('timeout', 10))
            await sio.emit('code_output', {
                'language': r.get('language', 'python'),
                'stdout': r.get('stdout', ''), 'stderr': r.get('stderr', ''),
                'success': r.get('success', False), 'execution_time_ms': r.get('execution_time_ms', 0),
                'returncode': r.get('returncode', -1), 'forced': True,
            })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'remember_fact':
            from user_memory import add_fact
            r = add_fact(args.get('key', ''), args.get('value', ''))
            await sio.emit('memory_update', {'action': 'add_fact', 'key': r.get('key', ''), 'value': r.get('value', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'recall_facts':
            from user_memory import search_facts
            r = search_facts(args.get('query', ''))
            await sio.emit('memory_update', {'action': 'recall', 'query': r.get('query', ''), 'matches': r.get('matches', []), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'get_user_profile':
            from user_memory import memory_summary
            r = memory_summary()
            await sio.emit('memory_update', {'action': 'profile', 'summary': r, 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'set_preference':
            from user_memory import set_preference
            r = set_preference(args.get('key', ''), args.get('value', ''))
            await sio.emit('memory_update', {'action': 'set_preference', 'key': args.get('key', ''), 'value': args.get('value', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'forget_fact':
            from user_memory import delete_fact
            r = delete_fact(args.get('key', ''))
            await sio.emit('memory_update', {'action': 'delete_fact', 'key': args.get('key', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'list_memory':
            import memory_store
            data = memory_store.list_memory(type=args.get('type', 'all'), limit=10)
            await sio.emit('memory_update', {'action': 'list_memory', 'data': data, 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': data, 'forced': True})
        elif tool == 'show_memory':
            from user_memory import list_facts, get_profile
            import memory_store
            profile = get_profile()
            facts = list_facts(limit=50)
            people = memory_store.list_people(limit=20)
            lessons = memory_store.recall_lessons("", limit=10)
            payload = {
                "workflow": "memory-view",
                "profile": profile,
                "facts": facts.get("facts", []),
                "people": people,
                "lessons": lessons,
            }
            await sio.emit('workflow_start', payload)
            await sio.emit('tool_result', {'tool': tool, 'result': payload, 'forced': True})
        elif tool == 'remember_person':
            import memory_store
            r = memory_store.remember_person(
                args.get('name', ''), args.get('relationship', ''),
                args.get('traits', ''), args.get('preferences', ''), args.get('notes', '')
            )
            await sio.emit('memory_update', {'action': 'remember_person', 'name': args.get('name', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'recall_person':
            import memory_store
            r = memory_store.recall_person(args.get('query', ''), limit=5)
            await sio.emit('memory_update', {'action': 'recall_person', 'query': args.get('query', ''), 'matches': r.get('matches', []), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'remember_lesson':
            import memory_store
            r = memory_store.remember_lesson(args.get('situation', ''), args.get('correction', ''))
            await sio.emit('memory_update', {'action': 'remember_lesson', 'situation': args.get('situation', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'analyze_screen':
            from screen_vision import analyze_screen
            r = await analyze_screen(args.get('prompt', 'Describe what is on the screen in detail.'))
            if r.get('success'):
                await sio.emit('screen_analysis', {
                    'prompt': r.get('prompt', ''), 'analysis': r.get('analysis', ''),
                    'screenshot': r.get('screenshot', ''), 'elapsed_ms': r.get('elapsed_ms', 0), 'forced': True,
                })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'read_screen_text':
            from screen_vision import read_screen_text
            r = await read_screen_text()
            if r.get('success'):
                await sio.emit('screen_text', {
                    'text': r.get('analysis', ''), 'screenshot': r.get('screenshot', ''),
                    'elapsed_ms': r.get('elapsed_ms', 0), 'forced': True,
                })
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'set_reminder':
            from reminders import set_reminder as _set_rem
            r = _set_rem(
                args.get('message', ''),
                fire_at=args.get('fire_at'),
                in_seconds=args.get('in_seconds'),
                recurring_seconds=args.get('recurring_seconds'),
            )
            await sio.emit('reminder_update', {'action': 'set', 'reminder': r.get('reminder', {}), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'list_reminders':
            from reminders import list_reminders as _list_rem
            r = _list_rem()
            await sio.emit('reminder_update', {'action': 'list', 'reminders': r.get('reminders', []), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'cancel_reminder':
            from reminders import cancel_reminder as _cancel_rem
            r = _cancel_rem(args.get('id', ''))
            await sio.emit('reminder_update', {'action': 'cancel', 'id': args.get('id', ''), 'forced': True})
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'recognize_face':
            from face_api import encode_face
            from face_store import recognize_face as _match_face
            import base64
            request_id = str(__import__('uuid').uuid4())
            future = asyncio.Future()
            if hasattr(audio_loop, '_pending_face_frames'):
                audio_loop._pending_face_frames[request_id] = future
            await sio.emit('request_face_frame', {'id': request_id}, room=sid)
            try:
                frame_data = await asyncio.wait_for(future, timeout=5.0)
                image_bytes = base64.b64decode(frame_data)
                enc_result = await encode_face(image_bytes)
                if "error" in enc_result:
                    r = {"result": enc_result["error"]}
                elif "embedding" in enc_result:
                    match = _match_face(enc_result["embedding"])
                    r = {"result": match.get("name") or "Face not recognized"}
                else:
                    r = {"result": "No face detected"}
            except asyncio.TimeoutError:
                r = {"result": "Camera not responding"}
            finally:
                if hasattr(audio_loop, '_pending_face_frames'):
                    audio_loop._pending_face_frames.pop(request_id, None)
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'remember_face':
            from face_api import encode_face
            from face_store import store_face
            import base64
            name = args.get('name', '').strip()
            if not name:
                r = {"result": "Name is required"}
            else:
                request_id = str(__import__('uuid').uuid4())
                future = asyncio.Future()
                if hasattr(audio_loop, '_pending_face_frames'):
                    audio_loop._pending_face_frames[request_id] = future
                await sio.emit('request_face_frame', {'id': request_id}, room=sid)
                try:
                    frame_data = await asyncio.wait_for(future, timeout=5.0)
                    image_bytes = base64.b64decode(frame_data)
                    enc_result = await encode_face(image_bytes)
                    if "error" in enc_result:
                        r = {"result": enc_result["error"]}
                    elif "embedding" in enc_result:
                        store_face(name, enc_result["embedding"])
                        r = {"result": f"Remembered {name}"}
                    else:
                        r = {"result": "No face detected"}
                except asyncio.TimeoutError:
                    r = {"result": "Camera not responding"}
                finally:
                    if hasattr(audio_loop, '_pending_face_frames'):
                        audio_loop._pending_face_frames.pop(request_id, None)
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'send_telegram_message':
            from telegram_bot import telegram_bot
            text = args.get('text', '')
            r = {'result': await telegram_bot.send_message(text)}
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'send_telegram_file':
            from telegram_bot import telegram_bot
            path = args.get('path', '')
            r = await telegram_bot.send_file(path)
            await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        elif tool == 'export_data':
            from export_service import export_data as _export
            fmt = args.get('format', 'markdown')
            title = args.get('title', 'soda_export')
            path = args.get('path', None)
            data = getattr(audio_loop, '_last_scraped_data', None) if audio_loop else None
            if data is None:
                await sio.emit('error', {'msg': 'No scraped data available. Search and scrape something first.'}, room=sid)
            else:
                if isinstance(data, str):
                    import json
                    try: data = json.loads(data)
                    except: pass
                r = await _export(data, fmt, title, path)
                if r.get('success') and r.get('path'):
                    mime = 'text/markdown' if fmt == 'markdown' else 'text/csv' if fmt == 'csv' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    await sio.emit('view_file_content', {'payload': {'type': 'text', 'content': None, 'mime': mime, 'path': r['path']}})
                await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
        else:
            await sio.emit('error', {'msg': f'force_tool: unknown tool {tool!r}'}, room=sid)
    except Exception as e:
        await sio.emit('error', {'msg': f'force_tool {tool} failed: {e}'}, room=sid)

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, _scheduler_task
    
    print("[SERVER] ========================================")
    print("[SERVER] SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    print("[SERVER] ========================================")
    
    # Stop audio loop
    if audio_loop:
        print("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None
    
    # Cancel the loop task if running
    if loop_task and not loop_task.done():
        print("[SERVER] Cancelling loop task...")
        loop_task.cancel()
        loop_task = None
    
    # Cancel scheduler task
    if _scheduler_task and not _scheduler_task.done():
        print("[SERVER] Cancelling scheduler task...")
        _scheduler_task.cancel()
        _scheduler_task = None
    
    try:
        from telegram_bot import telegram_bot
        telegram_bot.stop()
    except:
        pass
    
    print("[SERVER] Graceful shutdown complete. Terminating process...")

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    print(f"[SERVER DEBUG] User input received: '{text}'")

    if not audio_loop:
        log.warning("Audio loop is None. Cannot send text.")
        await sio.emit('error', {'msg': 'Audio loop not started yet. Please wait for SODA to initialize.'}, room=sid)
        return

    if not audio_loop.session:
        log.warning("Session is None. Cannot send text.")
        await sio.emit('error', {'msg': 'No active session. Voice backend may still be connecting.'}, room=sid)
        return

    if text:
        print(f"[SERVER DEBUG] Sending message to model: '{text}'")

        # Log User Input to Project History
        if audio_loop and hasattr(audio_loop, 'project_manager') and audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", text)
            
        
        # ── Passive Memory Extraction ──
        try:
            import memory_store
            stored = memory_store.extract_and_store_people(text)
            if stored:
                names = ", ".join(s["name"] for s in stored)
                print(f"[MEMORY] Auto-stored people from introduction: {names}")
                await sio.emit('memory_update', {
                    'type': 'people',
                    'stored': stored,
                    'msg': f"Remembered: {names}"
                })
        except Exception as e:
            log.error(f"Passive memory extraction error: {e}")

        await audio_loop.session.send(input=text, end_of_turn=True)
        print(f"[SERVER DEBUG] Message sent to model successfully.")

@sio.event
async def announce(sid, data):
    text = data.get('text', '')
    print(f"[SERVER] Announce: '{text}'")
    
    # Announcement should speak WITHOUT conversation
    # Send a system-like message that gets processed as TTS only
    if audio_loop and audio_loop.session:
        try:
            # Send as system instruction - model should just respond with acknowledgment
            # Use a special format to indicate this is announcement-only
            announcement_text = f"[ANNOUNCEMENT] {text}"
            await audio_loop.session.send(input=announcement_text, end_of_turn=True)
            print("[SERVER] Announcement sent to model for TTS")
        except Exception as e:
            log.error(f"Announce error: {e}")

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        print(f"[SERVER] video_frame received: {len(str(image_data))} chars")
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))
    elif not image_data:
        print(f"[SERVER] video_frame: no image data in payload, keys={list(data.keys())}")
    elif not audio_loop:
        print(f"[SERVER] video_frame: audio_loop is None, frame dropped")

@sio.event
async def camera_frame(sid, data):
    image_data = data.get('image')
    if image_data and audio_loop:
        audio_loop._latest_camera_frame = {"mime_type": "image/jpeg", "data": image_data}

@sio.event
async def speaking_timer_expired(sid, data):
    part = data.get('part')
    topic = data.get('topic', '')
    questions = data.get('questions', [])
    if part and audio_loop and audio_loop.session:
        qs = ', '.join(questions) if isinstance(questions, list) else str(questions)
        text = (
            f"[System: The timer for IELTS Speaking Part {part} has expired. "
            f"Topic: {topic}. Questions: {qs}. "
            f"Please call ielts_speaking_evaluate now with your assessment "
            f"of everything the user said during this part. "
            f"Pass the full topic/cue card as the 'question' parameter "
            f"and a brief summary transcript as the 'transcript' parameter. "
            f"Then call ielts_speaking_start to advance to the next part, "
            f"or if this was Part 3, the test is complete.]"
        )
        log.info(f"speaking_timer_expired: injecting eval request for Part {part}")
        asyncio.create_task(audio_loop.inject_text(text))

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            print("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
                f.write(f"[{sender}] {text}\n")
        print(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        log.error(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    print(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            print("No memory data provided.")
            return

        if not audio_loop:
             log.warning("Audio loop is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
             return
        
        if not audio_loop.session:
             log.warning("Session is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (No active session)"})
             return

        # Send to model
        print("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.session.send(input=context_msg, end_of_turn=True)
        print("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        log.error(f"Error uploading memory: {e}")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def get_settings(sid):
    await sio.emit('settings', SETTINGS)

@sio.event
async def update_settings(sid, data):
    # Generic update
    print(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        print(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    if "user_native_lang" in data:
        SETTINGS["user_native_lang"] = data["user_native_lang"]
        # Update translation agent
        from translation_agent import translation_agent
        translation_agent.set_native_language(data["user_native_lang"])
        print(f"[SERVER] Native language set to: {data['user_native_lang']}")

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', SETTINGS)


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    print(f"Updating permissions (legacy event): {data}")
    SETTINGS["tool_permissions"].update(data)
    save_settings()
    
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    # Broadcast update to all
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def audio_control(sid, data=None):
    """Control audio - mute/unmute microphone"""
    global audio_loop
    
    if not data:
        return
        
    muted = data.get('muted', False)
    
    if audio_loop:
        audio_loop.set_paused(muted)
        print(f"Audio {'muted' if muted else 'unmuted'}")
        await sio.emit('status', {'msg': f"Audio {'muted' if muted else 'unmuted'}"})
    else:
        print("No audio loop running")

@sio.event
async def close_panel(sid, data=None):
    """Close a specific panel on the frontend. Called by SODA when it wants to dismiss panels."""
    if not data:
        return
    panel = data.get('panel', '')
    print(f"[SODA] Backend closing panel: {panel}")
    await sio.emit('close_panel', {'panel': panel}, room=sid)


@sio.on("wake_up")
async def handle_wake_up(sid, data=None):
    global _audio_loop
    if _audio_loop:
        await _audio_loop._exit_idle_mode()
        print("[SODA] Widget click wake_up — exited idle mode")

@sio.on("client_log")
async def handle_client_log(sid, data):
    level = data.get("level", "info").upper()
    message = data.get("message", "")
    location = data.get("location", "")
    stack = data.get("stack", "")
    detail = f"{message} | {location}" if location else message
    if level == "ERROR":
        log.error(f"[CLIENT] {detail}")
        if stack:
            log.error(f"[CLIENT] Stack: {stack}")
    elif level == "WARN":
        log.warning(f"[CLIENT] {detail}")
    else:
        log.info(f"[CLIENT] {detail}")


@sio.event
async def notepad_save(sid, data=None):
    """Save a notepad tab as a .txt file."""
    if not data:
        return
    filename = data.get('filename', 'notes.txt')
    content = data.get('content', '')
    import os
    projects_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'projects')
    os.makedirs(projects_dir, exist_ok=True)
    filepath = os.path.join(projects_dir, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[SODA] Notepad saved: {filepath} ({len(content)} chars)")
        await sio.emit('status', {'msg': f'Notepad saved as {filename}'}, room=sid)
    except Exception as e:
        log.error(f"Notepad save error: {e}")
        await sio.emit('error', {'msg': f'Failed to save notepad: {str(e)}'})

@sio.event
async def notepad_read_result(sid, data=None):
    """Receive result from a notepad read request."""
    if not data or not data.get('id'):
        return
    read_id = data['id']
    if hasattr(audio_loop, '_pending_notepad_reads'):
        future = audio_loop._pending_notepad_reads.get(read_id)
        if future and not future.done():
            future.set_result(data)
    import soda as soda_mod
    pending = getattr(soda_mod, '_pending_notepad_reads', None)
    if pending:
        future = pending.get(read_id)
        if future and not future.done():
            future.set_result(data)

@sio.event
async def control_window(sid, data=None):
    """Control window - minimize/maximize/close"""
    if not data:
        return
    action = data.get('action', '')
    print(f"[SODA] Backend received control_window: {action}")
    # Send to all clients
    await sio.emit('window_control', {'action': action})

@sio.event
async def create_folder(sid, data=None):
    """Create a folder on the filesystem from the UI file browser."""
    if not data or not data.get('path'):
        return
    folder_path = data['path']
    try:
        os.makedirs(folder_path, exist_ok=True)
        print(f"[SERVER] Created folder: {folder_path}")
        await sio.emit('command_output', {
            'command': 'mkdir',
            'output': f'Created folder: {folder_path}',
            'success': True
        })
        # Refresh file browser to show new folder
        from external_apis import list_files
        parent = os.path.dirname(folder_path.rstrip('/\\'))
        list_result = await list_files(parent)
        await sio.emit('file_list', {
            'path': list_result.get('path', parent),
            'items': list_result.get('items', []),
            'success': list_result.get('success', False),
            'searchQuery': ''
        })
    except Exception as e:
        log.error(f"Failed to create folder: {e}")
        await sio.emit('command_output', {
            'command': 'mkdir',
            'output': f'Error creating folder: {str(e)}',
            'success': False
        })

@sio.event
async def webview_action_result(sid, data=None):
    """Receive result from a webview action executed on the frontend."""
    if not data or not data.get('id'):
        return
    action_id = data['id']
    print(f"[SODA] Webview action result: {data.get('action')} id={action_id}")
    if hasattr(audio_loop, '_pending_webview_results'):
        future = audio_loop._pending_webview_results.get(action_id)
        if future and not future.done():
            future.set_result(data)
    
    # Also check soda module level pending
    import soda as soda_mod
    pending = getattr(soda_mod, '_pending_webview_results', None)
    if pending:
        future = pending.get(action_id)
        if future and not future.done():
            future.set_result(data)


@sio.event
async def get_emotional_profile(sid, data=None):
    """Return emotional profile + recent episodes for frontend display."""
    try:
        from feelings_memory import FeelingsMemory
        fm = FeelingsMemory()
        profile = fm.get_profile_summary()
        episodes = [ep.to_dict() for ep in fm.get_recent_episodes(30)]
        await sio.emit("emotional_profile", {"profile": profile, "episodes": episodes})
    except Exception as e:
        log.warning(f"get_emotional_profile failed: {e}")
        await sio.emit("emotional_profile", {"profile": "", "episodes": []})

@sio.event
async def face_frame_response(sid, data=None):
    """Receive a captured face frame from the frontend."""
    if not data or not data.get('id'):
        return
    request_id = data['id']
    print(f"[SERVER] face_frame_response id={request_id[:8]}...")
    if hasattr(audio_loop, '_pending_face_frames'):
        future = audio_loop._pending_face_frames.get(request_id)
        if future and not future.done():
            future.set_result(data.get('image'))
    else:
        print(f"[SERVER] audio_loop has no _pending_face_frames")


@sio.event
async def frame_response(sid, data=None):
    """Receive a fresh camera frame from the frontend for analysis."""
    if not data or not data.get('id'):
        return
    request_id = data['id']
    if hasattr(audio_loop, '_pending_frames'):
        future = audio_loop._pending_frames.get(request_id)
        if future and not future.done():
            future.set_result(data.get('image'))
    else:
        print(f"[SERVER] frame_response: audio_loop has no _pending_frames")

@sio.event
async def browser_url_response(sid, data=None):
    """Receive active browser URL from the frontend for pentesting."""
    url = (data or {}).get("url", "")
    if not url:
        return
    if hasattr(audio_loop, '_pending_browser_url') and audio_loop._pending_browser_url is not None:
        future = audio_loop._pending_browser_url
        if not future.done():
            future.set_result(url)
        audio_loop._pending_browser_url = None
    else:
        print("[SERVER] No pending browser URL request")


@sio.event
async def pastebox_content(sid, data=None):
    """Receive pasted content from the frontend paste box."""
    text = (data or {}).get("text", "")
    if not text:
        return
    if hasattr(audio_loop, '_pending_pastebox') and audio_loop._pending_pastebox is not None:
        future = audio_loop._pending_pastebox
        if not future.done():
            future.set_result(text)
        audio_loop._pending_pastebox = None
        print(f"[SERVER] pastebox_content: received {len(text)} chars")
    else:
        print("[SERVER] No pending pastebox request")


@sio.event
async def browser_audio(sid, data):
    """Receive raw PCM audio chunks from browser mic and feed to AudioLoop."""
    global audio_loop
    if not audio_loop:
        return
    raw = data.get('audio')
    if raw is None:
        return
    if isinstance(raw, list):
        raw = bytes(raw)
    audio_loop.feed_browser_audio(raw)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"[SERVER] Starting on port {port}...")
    print(f"[SERVER] Expecting local agent at desktop PC")
    uvicorn.run(app_socketio, host="0.0.0.0", port=port)
