import sys
import asyncio
import base64
import traceback

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
_daily_brief_task = None

# ── Local Agent Routing ──
_connected_agents: dict[str, dict] = {}
_pending_agent_results: dict[str, asyncio.Future] = {}
_mobile_authed: dict[str, bool] = {}

# Share with soda module for _dispatch_tool routing
soda._connected_agents = _connected_agents
soda._pending_agent_results = _pending_agent_results

# Engine.IO payload decode limit — patch Payload.decode to truncate instead of raising
# The class-attr patch (max_decode_packets) works but engineio catches the ValueError
# internally and prints the full traceback before our ASGI middleware sees it.
import engineio.payload as _eio_payload
_eio_payload.Payload.max_decode_packets = 512
_original_decode = _eio_payload.Payload.decode
def _safe_decode(self, encoded_payload):
    self.packets = []
    if len(encoded_payload) == 0:
        return
    import urllib.parse
    if encoded_payload.startswith('d='):
        encoded_payload = urllib.parse.parse_qs(encoded_payload)['d'][0]
    encoded_packets = encoded_payload.split('\x1e')
    if len(encoded_packets) > self.max_decode_packets:
        encoded_packets = encoded_packets[-self.max_decode_packets:]
    import engineio.packet as _pkt
    self.packets = [_pkt.Packet(encoded_packet=ep) for ep in encoded_packets]
_eio_payload.Payload.decode = _safe_decode

# Create a Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_interval=25,
    ping_timeout=20,
)

@asynccontextmanager
async def lifespan(_app):
    import sys
    log.info(f"SODA server starting")
    log.debug(f"Python Version: {sys.version}")
    try:
        loop = asyncio.get_running_loop()
        log.debug(f"[SERVER DEBUG] Running Loop: {type(loop)}")
        policy = asyncio.get_event_loop_policy()
        log.debug(f"[SERVER DEBUG] Current Policy: {type(policy)}")
    except Exception as e:
        log.debug(f"Error checking loop: {e}")
    log.info("[SERVER] Startup: Kasa agent removed in cleanup")

    reminder_task = None
    try:
        from reminders import reminder_loop
        reminder_task = asyncio.create_task(reminder_loop(sio, interval=5))
        log.info("[SERVER] Reminder scheduler started")
    except Exception as e:
        log.warning(f"Reminder scheduler failed to start: {e}")

    # ── Agent health monitor (logs every 60s) + stale agent eviction ──
    async def _agent_health_logger():
        async def _stale_or_ping(sid, agent_info, reason):
            """First sighting of a stale agent: ask it to re-register instead of
            popping it (an agent only registers on socket connect, so a silent pop
            leaves it registered-but-unroutable forever). Second sighting: evict."""
            if agent_info.get('_stale_pinged'):
                return True
            agent_info['_stale_pinged'] = True
            log.info(f"[AGENT] {agent_info.get('machine_id', sid)} {reason} — sending agent_ping (re-register)")
            try:
                await sio.emit('agent_ping', {'ts': datetime.now().isoformat()}, to=sid)
            except Exception as e:
                log.warning(f"[AGENT] agent_ping to {sid} failed: {e}")
            return False

        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            stale_threshold = 90  # seconds without pong → stale
            stale_sids = []
            # Log bridge status summary
            agent_count = len(_connected_agents)
            agent_names = [a.get('machine_id', '?') for a in _connected_agents.values()]
            log.debug(f"[BRIDGE STATUS] Agents connected: {agent_count} ({', '.join(agent_names) if agent_names else 'none'})")
            if _connected_agents:
                for sid, agent_info in list(_connected_agents.items()):
                    machine_id = agent_info.get('machine_id', sid)
                    tools = len(agent_info.get('tools', []))
                    apps = agent_info.get('app_registry_count', '?')
                    last_pong = agent_info.get('last_pong')
                    if last_pong:
                        last_pong_dt = datetime.fromisoformat(last_pong)
                        elapsed = (now - last_pong_dt).total_seconds()
                        log.debug(f"[AGENT] Health: {machine_id} — {tools} tools, {apps} apps, last_pong: {elapsed:.0f}s ago")
                        if elapsed > stale_threshold:
                            if await _stale_or_ping(sid, agent_info, f'no pong >{stale_threshold}s'):
                                stale_sids.append(sid)
                    else:
                        log.debug(f"[AGENT] Health: {machine_id} — {tools} tools, {apps} apps, never ponged")
                        # Give new agents 120s grace period before marking stale
                        connected_at = agent_info.get('connected_at')
                        if connected_at:
                            connected_dt = datetime.fromisoformat(connected_at)
                            if (now - connected_dt).total_seconds() > 120:
                                if await _stale_or_ping(sid, agent_info, 'never ponged >120s'):
                                    stale_sids.append(sid)
                for stale_sid in stale_sids:
                    stale_agent = _connected_agents.pop(stale_sid, None)
                    if stale_agent:
                        log.info(f"[AGENT] Evicted stale agent: {stale_agent.get('machine_id', stale_sid)} (no pong >{stale_threshold}s)")
                        await sio.emit('agent_connection_status', {
                            'connected': False,
                            'machine_id': stale_agent.get('machine_id', stale_sid),
                            'evicted': True,
                            'reason': 'stale_timeout'
                        })
            else:
                log.debug("[AGENT] Health: NO AGENTS CONNECTED — local desktop agent not running")
    _health_task = asyncio.create_task(_agent_health_logger())
    log.info("[SERVER] Agent health logger started (60s interval, stale eviction >90s)")

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
        log.info("[SERVER] Reminder scheduler stopped")

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
    log.warning(f"Caught signal {sig}. Exiting gracefully...")
    if audio_loop:
        try:
            log.warning("Stopping Audio Loop...")
            audio_loop.stop()
        except:
            pass
    log.warning("Force exiting...")
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
            log.info(f"Loaded settings: {SETTINGS}")
        except Exception as e:
            log.error(f"Error loading settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(SETTINGS, f, indent=4)
        log.info("Settings saved.")
    except Exception as e:
        log.error(f"Error saving settings: {e}")

# Load on startup
load_settings()

async def _wake_wsl():
    """Wake up Kali WSL on server startup (non-blocking, fire-and-forget)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            "wsl -d kali-linux -- bash -c 'echo kali_ready'",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=15)
        log.info("[WSL] Kali Linux is ready")
    except FileNotFoundError:
        log.info("[WSL] WSL not found — pentest tools will not work. Install WSL 2 + Kali Linux.")
    except Exception as e:
        log.info(f"[WSL] Could not start Kali: {e}")

@app.get("/")
async def root():
    return {"status": "running", "service": "S.O.D.A Backend"}

@app.get("/status")
@app.head("/status")
async def status():
    return {"status": "running", "service": "S.O.D.A Backend"}

# ── Project Registry HTTP API ──

@app.post("/api/projects/register")
async def http_register_project(data: dict):
    import project_registry
    name = data.get("name", "")
    endpoint = data.get("endpoint", "")
    if not name or not endpoint:
        return {"success": False, "error": "name and endpoint required"}
    r = project_registry.register(name=name, endpoint=endpoint)
    return {"success": True, "project": r}

@app.get("/api/projects")
async def http_list_projects():
    import project_registry
    return {"success": True, "projects": project_registry.list_projects()}

@app.post("/api/projects/{project_id}/query")
async def http_query_project(project_id: str):
    import project_registry
    r = await project_registry.query(project_id=project_id)
    return r

@app.post("/api/projects/{project_id}/remove")
async def http_remove_project(project_id: str):
    import project_registry
    r = project_registry.remove(project_id=project_id)
    return r

@sio.event
async def connect(sid, environ):
    _client_addresses[sid] = environ.get('REMOTE_ADDR', environ.get('HTTP_X_FORWARDED_FOR', 'unknown'))
    log.info(f"Client connected: {sid} from {_client_addresses[sid]}")
    await sio.emit('status', {'msg': 'Connected to S.O.D.A Backend'}, room=sid)
    # No auth required - auto-authenticate
    await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    global audio_loop, loop_task
    log.info(f"Client disconnected: {sid}")
    _mobile_authed.pop(sid, None)

    if audio_loop and getattr(audio_loop, '_owner_sid', None) == sid:
        log.info("Disconnecting - stopping audio loop owned by this client")
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
        agent_type = agent.get('agent_type', 'desktop')
        log.info(f"[AGENT] Agent disconnected: {machine_id} (type={agent_type}, {tools_count} tools, connected since {connected_at})")
        log.info(f"[AGENT] Active agents remaining: {len(_connected_agents)}")
        await sio.emit('agent_connection_status', {
            'connected': False,
            'machine_id': machine_id,
            'tools_count': 0,
            'reason': 'socket_disconnect'
        })

# ── Local Agent Events ──
@sio.event
async def agent_register(sid, data):
    """Register a local desktop agent or Android agent for remote tool execution."""
    agent_type = data.get('agent_type', 'desktop')
    machine_id = data.get('machine_id', sid)
    platform = data.get('platform', 'unknown')
    tools = data.get('tools', [])
    app_registry = data.get('app_registry', {})
    app_count = app_registry.get('count', 0)

    # Fail-closed only when the server is actually configured with a token;
    # an unset AGENT_TOKEN keeps the historical open behaviour.
    expected_token = os.getenv('AGENT_TOKEN', '').strip()
    if expected_token and data.get('token', '') != expected_token:
        log.warning(f"[AGENT] Rejected registration from {machine_id}: AGENT_TOKEN mismatch")
        await sio.emit('agent_connection_status', {
            'connected': False,
            'machine_id': machine_id,
            'tools_count': 0,
            'reason': 'auth_failed',
        }, room=sid)
        return

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
                    log.info(f"[AGENT] Replaced stale agent: {machine_id} ({old_tools}→{new_tools} tools, old SID: {old_sid})")
    _connected_agents[sid] = {
        'agent_type': 'desktop',
        'machine_id': machine_id,
        'platform': platform,
        'tools': tools,
        'app_registry_count': app_count,
        'connected_at': datetime.now().isoformat(),
        'sid': sid,
    }
    log.info(f"[AGENT] ✅ Registered: {machine_id} ({platform}) — {len(tools)} tools, {app_count} apps in registry")
    log.info(f"[AGENT]    SID: {sid}")
    log.info(f"[AGENT]    Available tools: {', '.join(tools[:10])}{'...' if len(tools) > 10 else ''}")
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
        agent_type = agent.get('agent_type', 'desktop')
        log.info(f"[AGENT] Agent disconnected (explicit): {machine_id} (type={agent_type})")
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
        log.info(f"[AGENT] Orphaned tool result: {callback_id} (agent: {_connected_agents.get(sid, {}).get('machine_id', sid)})")

@sio.event
async def agent_pong(sid, data):
    """Heartbeat from local agent — keep-alive tracking."""
    agent = _connected_agents.get(sid)
    if agent:
        agent['last_pong'] = datetime.now().isoformat()

@sio.event
async def agent_push(sid, data):
    """Agent-initiated push — agent sends updates without being asked."""
    agent_info = _connected_agents.get(sid)
    if not agent_info:
        log.info(f"[AGENT_PUSH] Unknown agent {sid}, ignoring")
        return
    push_type = data.get("type", "unknown")
    task_id = data.get("task_id", "")
    text = data.get("text", "")
    log.info(f"[AGENT_PUSH] type={push_type} task={task_id} from={agent_info.get('machine_id', sid)}")

    if not audio_loop:
        log.info("[AGENT_PUSH] audio_loop not initialized")
        return

    # Handle OpenCode-specific updates
    if push_type in ("opencode_output", "opencode_complete", "opencode_error"):
        try:
            from opencode_monitor import update_task, get_task
            if push_type == "opencode_output":
                update_task(task_id, output_line=text)
            elif push_type == "opencode_complete":
                update_task(task_id, status="completed", exit_code=0)
                task = get_task(task_id)
                if task:
                    from notebook import save_task
                    await save_task(task_id, task.folder, task.prompt, "completed",
                                  output_summary=task.summary())
            elif push_type == "opencode_error":
                update_task(task_id, status="failed", error=text)
                task = get_task(task_id)
                if task:
                    from notebook import save_task
                    await save_task(task_id, task.folder, task.prompt, "failed",
                                  error=text, output_summary=task.summary())
        except Exception as e:
            log.info(f"[AGENT_PUSH] Error handling {push_type}: {e}")

    # Inject into SODA's Gemini session for voice response
    formatted = f"[Agent update: {push_type}] {text}"
    await audio_loop.inject_text(formatted)

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task, _daily_brief_task
    
    log.info("Starting Audio Loop...")

    agent_type = (data or {}).get('agent_type', 'desktop')
    
    device_index = None
    device_name = None
    # Auto-detect Render (no physical mic) — use browser mic only
    mic_source = 'remote' if os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID') else 'local'
    if data:
        if 'device_index' in data:
            device_index = data['device_index']
        if 'device_name' in data:
            device_name = data['device_name']
    log.info(f"Using input device: Name='{device_name}', Index={device_index}, mic_source={mic_source}")
    
    if audio_loop:
        if loop_task and (loop_task.done() or loop_task.cancelled()):
             log.info("Audio loop task appeared finished/cancelled. Clearing and restarting...")
             audio_loop = None
        else:
             log.info("Audio loop already running. Re-connecting client to session.")
             await sio.emit('status', {'msg': 'S.O.D.A Already Running'})
             return

    # Continue with audio loop initialization...
    from soda import AudioLoop
    def on_audio_data(data_bytes):
        b64 = base64.b64encode(data_bytes).decode('ascii')
        try:
            asyncio.create_task(sio.emit('audio_data', {'data': b64}))
        except Exception as e:
            log.error(f"[AUDIO EMIT ERROR] {e}")

    # Callback to send Transcription data to frontend
    def on_transcription(data):
        asyncio.create_task(sio.emit('transcription', data))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        log.info(f"Requesting confirmation for tool: {data.get('tool')}")
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        log.info(f"Sending Project Update: {project_name}")
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
        log.info(f"Initializing AudioLoop with device_index={device_index}")
        audio_loop = soda.AudioLoop(
            video_mode="none",
            sio=sio,
            on_audio_data=on_audio_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_project_update=on_project_update,
            on_error=on_error,
            on_mic_level=on_mic_level,
            start_message="",
            input_device_index=device_index,
            input_device_name=device_name,
            mic_source=mic_source,
        )
        audio_loop._owner_sid = sid
        log.info("AudioLoop initialized successfully.")

        # Build greeting for start message — reference the previous session when known
        start_msg = ("Greet your owner warmly and funnily in ONE short sentence. "
                     "Read his expression from the camera snapshot to gauge his mood, then say something that matches. "
                     "Keep it tight - one sentence, warm, and genuinely funny. "
                     "Do NOT call any tools during the greeting. Just greet, then stop and listen.")
        prev = audio_loop._exchange_history
        if prev:
            lines = []
            for e in prev[-8:]:
                if e.get("user"):
                    lines.append(f"Sir: {str(e['user'])[:200]}")
                if e.get("model"):
                    lines.append(f"SODA: {str(e['model'])[:200]}")
            if lines:
                start_msg += ("\n\nPREVIOUS SESSION — you are waking up after an earlier session. "
                              "Below is what you two last said. Your greeting must naturally reference this "
                              "(e.g. 'back on it — we were talking about X'), then stop and listen. "
                              "Keep it ONE sentence total:\n" + "\n".join(lines[-12:]))
        audio_loop.start_message = start_msg

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
                log.info(f"[SERVER] Applied native language: {SETTINGS['user_native_lang']}")
        except Exception as e:
            log.warning(f"Translation agent init failed: {e}")
        
        # Check initial mute state
        if data and data.get('muted', False):
            log.info("Starting with Audio Paused")
            audio_loop.set_paused(True)

        log.info("Creating asyncio task for AudioLoop.run()")
        loop_task = asyncio.create_task(audio_loop.run())

        # Wake Kali WSL in background (non-blocking, proper event loop)
        asyncio.create_task(_wake_wsl())

        # Start scheduler background task
        global _scheduler_task
        _scheduler_task = asyncio.create_task(
            scheduler.scheduler_loop(sio, audio_loop, interval=30)
        )

        # Start daily routine auto-brief background task (09:00 / 13:00 / 22:00)
        import daily_routine
        if _daily_brief_task and not _daily_brief_task.done():
            _daily_brief_task.cancel()
        _daily_brief_task = asyncio.create_task(
            daily_routine.daily_brief_loop(sio, audio_loop, interval=30)
        )

        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            global _scheduler_task
            try:
                task.result()
            except asyncio.CancelledError:
                log.info("Audio Loop Cancelled")
            except Exception as e:
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

        log.info("Emitting 'SODA Started'")
        await sio.emit('status', {'msg': 'SODA Started'})
        
    except Exception as e:
        log.error(f"Failed to start SODA: {e}")
        traceback.print_exc()
        audio_loop = None


@sio.event
async def stop_audio(sid):
    global audio_loop, loop_task, _scheduler_task, _daily_brief_task
    if audio_loop:
        audio_loop.stop()
        log.info("Stopping Audio Loop")
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
        # Cancel the daily-brief loop — it holds a reference to the dead audio_loop
        if _daily_brief_task and not _daily_brief_task.done():
            _daily_brief_task.cancel()
            try:
                await _daily_brief_task
            except asyncio.CancelledError:
                pass
            _daily_brief_task = None
        await sio.emit('status', {'msg': 'SODA Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        log.info("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        log.info("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)

    log.debug(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")

    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        log.info("Audio loop not active, cannot resolve confirmation.")


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
    elif tool == 'web_search_live' or tool == 'agent_search':
        from agents.web_search_agent import WebSearchAgent
        agent = WebSearchAgent()
        query = args.get('query', 'python')
        r = await agent.execute(query=query, num_results=args.get('num_results', 5))
        await sio.emit('search_results', {
            'query': query,
            'results': r.get('results', []),
        })
    else:
        await sio.emit('error', {'msg': f'__debug_dispatch__: unknown tool {tool!r}'})


async def _run_tool_and_emit(tool, args, source='force_tool'):
    """Dispatch a tool locally and emit the frontend events that tool needs.

    Shared by force_tool (localhost) and mobile_force_tool (remote app).
    """
    log.info(f"[SERVER] {source}: {tool} args={args}")
    try:
        from tool_dispatch import dispatch_local_tool
        r = await dispatch_local_tool(tool, args, sio=sio, audio_loop=audio_loop)
        # Emit frontend-specific events for tools that need them
        if tool == 'terminal_execute':
            await sio.emit('command_output', {
                'command': args.get('command', ''), 'output': r.get('output', ''),
                'success': r.get('success', False), 'forced': True,
            })
        elif tool in ('web_search_live', 'agent_search') and r.get('results'):
            await sio.emit('search_results', {
                'query': args.get('query', ''), 'results': r.get('results', []), 'forced': True,
            })
        elif tool == 'screenshot' and r.get('success'):
            await sio.emit('screenshot_taken', {
                'path': r.get('path', ''), 'width': r.get('width', 0),
                'height': r.get('height', 0), 'size_bytes': r.get('size_bytes', 0), 'forced': True,
            })
        elif tool == 'list_processes':
            await sio.emit('process_list', {
                'count': r.get('count', 0), 'processes': r.get('processes', []), 'forced': True,
            })
        elif tool == 'get_active_window':
            await sio.emit('active_window', {
                'title': r.get('title', ''), 'success': r.get('success', False), 'forced': True,
            })
        elif tool == 'run_code':
            await sio.emit('code_output', {
                'language': r.get('language', 'python'),
                'stdout': r.get('stdout', ''), 'stderr': r.get('stderr', ''),
                'success': r.get('success', False), 'execution_time_ms': r.get('execution_time_ms', 0),
                'returncode': r.get('returncode', -1), 'forced': True,
            })
        elif tool in ('remember_fact', 'recall_facts', 'get_user_profile', 'set_preference',
                       'forget_fact', 'list_memory', 'show_memory', 'remember_person',
                       'recall_person', 'remember_lesson'):
            await sio.emit('memory_update', {'action': tool, 'data': r, 'forced': True})
        elif tool == 'analyze_screen' and r.get('success'):
            await sio.emit('screen_analysis', {
                'prompt': r.get('prompt', ''), 'analysis': r.get('analysis', ''),
                'screenshot': r.get('screenshot', ''), 'elapsed_ms': r.get('elapsed_ms', 0), 'forced': True,
            })
        elif tool == 'read_screen_text' and r.get('success'):
            await sio.emit('screen_text', {
                'text': r.get('analysis', ''), 'screenshot': r.get('screenshot', ''),
                'elapsed_ms': r.get('elapsed_ms', 0), 'forced': True,
            })
        elif tool in ('set_reminder', 'list_reminders', 'cancel_reminder'):
            await sio.emit('reminder_update', {'action': tool, 'data': r, 'forced': True})
        elif tool == 'list_files' and isinstance(r, dict):
            await sio.emit('file_list', {
                'path': r.get('path', args.get('path', '')), 'items': r.get('items', []),
                'success': r.get('success', False),
            })
        await sio.emit('tool_result', {'tool': tool, 'result': r, 'forced': True})
    except Exception as e:
        log.exception(f"{source} {tool} failed")
        await sio.emit('error', {'msg': f'{source} {tool} failed: {e}'})


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
    await _run_tool_and_emit(tool, args, 'force_tool')


# ── Mobile remote (soda-remote) ──────────────────────────────────
# Fail-closed: without MOBILE_SECRET set on the server, no phone can control
# this machine. mobile_force_tool reaches terminal_execute, so an open
# endpoint here would be remote code execution.
@sio.event
async def mobile_auth(sid, data):
    secret = (data or {}).get('secret', '')
    expected = os.getenv('MOBILE_SECRET', '').strip()
    ok = bool(expected) and secret == expected
    _mobile_authed[sid] = ok
    if ok:
        log.info("[MOBILE] Remote authenticated")
    else:
        log.warning("[MOBILE] Rejected remote auth (MOBILE_SECRET %s)",
                    "not configured" if not expected else "mismatch")
    await sio.emit('auth_status', {
        'authenticated': ok,
        **({} if ok else {'error': 'MOBILE_SECRET not configured on server' if not expected
                           else 'Invalid secret'}),
    }, room=sid)


@sio.event
async def mobile_force_tool(sid, data):
    if not _mobile_authed.get(sid):
        await sio.emit('auth_status', {'authenticated': False, 'error': 'Not authenticated'}, room=sid)
        return
    tool = (data or {}).get('tool')
    args = (data or {}).get('args') or {}
    if not tool:
        return
    await _run_tool_and_emit(tool, args, 'mobile_force_tool')


@sio.event
async def mobile_voice_command(sid, data):
    """PCM uplink from the phone — same path the browser mic uses."""
    if not _mobile_authed.get(sid):
        return
    if not audio_loop:
        await sio.emit('error', {'msg': 'Voice backend not started yet'}, room=sid)
        return
    raw = (data or {}).get('audio')
    if raw is None:
        return
    if isinstance(raw, list):
        raw = bytes(raw)
    elif isinstance(raw, str):
        try:
            raw = base64.b64decode(raw)
        except Exception:
            return
    audio_loop.feed_browser_audio(raw)

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, _scheduler_task, _daily_brief_task
    
    log.warning("========================================")
    log.warning("SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    log.warning("========================================")
    
    # Stop audio loop
    if audio_loop:
        log.warning("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None
    
    # Cancel the loop task if running
    if loop_task and not loop_task.done():
        log.info("[SERVER] Cancelling loop task...")
        loop_task.cancel()
        loop_task = None
    
    # Cancel scheduler task
    if _scheduler_task and not _scheduler_task.done():
        log.info("[SERVER] Cancelling scheduler task...")
        _scheduler_task.cancel()
        _scheduler_task = None

    if _daily_brief_task and not _daily_brief_task.done():
        log.info("[SERVER] Cancelling daily brief task...")
        _daily_brief_task.cancel()
        _daily_brief_task = None
    
    log.info("[SERVER] Graceful shutdown complete. Terminating process...")
    # Nothing else exits the process — without this the handler was a no-op.
    await asyncio.sleep(0.2)
    os._exit(0)

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    log.debug(f"[SERVER DEBUG] User input received: '{text}'")

    if not audio_loop:
        log.warning("Audio loop is None. Cannot send text.")
        await sio.emit('error', {'msg': 'Audio loop not started yet. Please wait for SODA to initialize.'}, room=sid)
        return

    if not audio_loop.session:
        log.warning("Session is None. Cannot send text.")
        await sio.emit('error', {'msg': 'No active session. Voice backend may still be connecting.'}, room=sid)
        return

    if text:
        log.debug(f"[SERVER DEBUG] Sending message to model: '{text}'")

        # Log User Input to Project History
        if audio_loop and hasattr(audio_loop, 'project_manager') and audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", text)
            
        
        # ── Passive Memory Extraction ──
        try:
            import memory_store
            stored = memory_store.extract_and_store_people(text)
            if stored:
                names = ", ".join(s["name"] for s in stored)
                log.info(f"[MEMORY] Auto-stored people from introduction: {names}")
                await sio.emit('memory_update', {
                    'type': 'people',
                    'stored': stored,
                    'msg': f"Remembered: {names}"
                })
        except Exception as e:
            log.error(f"Passive memory extraction error: {e}")

        await audio_loop.session.send_realtime_input(text=text)
        log.debug(f"[SERVER DEBUG] Message sent to model successfully.")

@sio.event
async def announce(sid, data):
    text = data.get('text', '')
    log.info(f"[SERVER] Announce: '{text}'")
    
    # Announcement should speak WITHOUT conversation
    # Send a system-like message that gets processed as TTS only
    if audio_loop and audio_loop.session:
        try:
            # Send as system instruction - model should just respond with acknowledgment
            # Use a special format to indicate this is announcement-only
            announcement_text = f"[ANNOUNCEMENT] {text}"
            await audio_loop.session.send_realtime_input(text=announcement_text)
            log.info("[SERVER] Announcement sent to model for TTS")
        except Exception as e:
            log.error(f"Announce error: {e}")

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        log.debug(f"[SERVER] video_frame received: {len(str(image_data))} chars")
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))
    elif not image_data:
        log.debug(f"[SERVER] video_frame: no image data in payload, keys={list(data.keys())}")
    elif not audio_loop:
        log.debug(f"[SERVER] video_frame: audio_loop is None, frame dropped")

@sio.event
async def camera_frame(sid, data):
    """Live frames from the full-screen camera view — forward to Gemini via send_frame."""
    image_data = data.get('image')
    if image_data and audio_loop:
        log.debug(f"[SERVER] camera_frame received: {len(str(image_data))} chars")
        asyncio.create_task(audio_loop.send_frame(image_data))
    elif not image_data:
        log.debug(f"[SERVER] camera_frame: no image data in payload, keys={list(data.keys()) if data else None}")
    elif not audio_loop:
        log.debug(f"[SERVER] camera_frame: audio_loop is None, frame dropped")

@sio.event
async def camera_fullscreen_close(sid, data=None):
    """User closed the full-screen camera view via the UI close button."""
    if audio_loop:
        audio_loop._camera_active = False
        audio_loop._latest_camera_frame = None
        log.info("[SERVER] camera_fullscreen_close: camera deactivated via UI")

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
            log.info("No messages to save.")
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
        log.info(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        log.error(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    log.info(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            log.info("No memory data provided.")
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
        log.info("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.session.send_realtime_input(text=context_msg)
        log.info("Memory context sent successfully.")
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
    log.info(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        log.info(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    if "user_native_lang" in data:
        SETTINGS["user_native_lang"] = data["user_native_lang"]
        # Update translation agent
        from translation_agent import translation_agent
        translation_agent.set_native_language(data["user_native_lang"])
        log.info(f"[SERVER] Native language set to: {data['user_native_lang']}")

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', SETTINGS)


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    log.info(f"Updating permissions (legacy event): {data}")
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
        log.info(f"Audio {'muted' if muted else 'unmuted'}")
        await sio.emit('status', {'msg': f"Audio {'muted' if muted else 'unmuted'}"})
    else:
        log.info("No audio loop running")

@sio.event
async def close_panel(sid, data=None):
    """Close a specific panel on the frontend. Called by SODA when it wants to dismiss panels."""
    if not data:
        return
    panel = data.get('panel', '')
    log.info(f"[SODA] Backend closing panel: {panel}")
    await sio.emit('close_panel', {'panel': panel}, room=sid)


@sio.on("wake_up")
async def handle_wake_up(sid, data=None):
    global _audio_loop
    if _audio_loop:
        await _audio_loop._exit_idle_mode()
        log.info("[SODA] Widget click wake_up — exited idle mode")

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
        log.info(f"[SODA] Notepad saved: {filepath} ({len(content)} chars)")
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
    log.info(f"[SODA] Backend received control_window: {action}")
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
        log.info(f"[SERVER] Created folder: {folder_path}")
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
    log.info(f"[SODA] Webview action result: {data.get('action')} id={action_id}")
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
    log.info(f"[SERVER] face_frame_response id={request_id[:8]}...")
    if hasattr(audio_loop, '_pending_face_frames'):
        future = audio_loop._pending_face_frames.get(request_id)
        if future and not future.done():
            future.set_result(data.get('image'))
    else:
        log.info(f"[SERVER] audio_loop has no _pending_face_frames")


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
        log.info(f"[SERVER] frame_response: audio_loop has no _pending_frames")

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
        log.info("[SERVER] No pending browser URL request")



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
    elif isinstance(raw, str):
        raw = base64.b64decode(raw)
    audio_loop.feed_browser_audio(raw)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    log.info(f"[SERVER] Starting on port {port}...")
    log.info(f"[SERVER] Expecting local agent at desktop PC")
    uvicorn.run(app_socketio, host="0.0.0.0", port=port)
