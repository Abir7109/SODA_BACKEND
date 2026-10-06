"""
Shared tool dispatch registry for SODA.

Eliminates duplication between server.py force_tool and soda.py _dispatch_tool.
Both call into dispatch_local_tool() for server-side tool execution.
"""

import asyncio
import base64
import json
import os
import mimetypes
from datetime import datetime

from logger import log


async def dispatch_local_tool(name: str, args: dict, sio=None, audio_loop=None) -> dict:
    """
    Execute a tool locally on the server side.

    Args:
        name: Tool name (e.g. 'terminal_execute', 'get_weather').
        args: Tool arguments dict.
        sio: Socket.IO server instance (for emit-based tools).
        audio_loop: AudioLoop instance (for tools that need session state).

    Returns:
        Tool result dict.
    """
    if name == 'terminal_execute':
        from system_app import _run_terminal_command_unchecked
        command = args.get('command', 'echo hello')
        r = await _run_terminal_command_unchecked(command, args.get('timeout', 10))
        return r

    elif name in ('web_search_live', 'agent_search'):
        from agents.web_search_agent import WebSearchAgent
        agent = WebSearchAgent()
        query = args.get('query', 'python')
        r = await agent.execute(query=query, num_results=args.get('num_results', 5))
        return r

    elif name == 'browse_webpage':
        from agents.webpage_agent import WebpageAgent
        agent = WebpageAgent()
        url = args.get('url', '')
        r = await agent.execute(url=url)
        return r

    elif name == 'list_files':
        from external_apis import list_files
        r = await list_files(args.get('path', ''), args.get('search', ''))
        if sio and r.get('success'):
            await sio.emit('file_list', {
                'path': r.get('path', args.get('path', '')),
                'items': r.get('items', []),
                'success': True,
            })
        return r

    elif name == 'open_file':
        from external_apis import open_file
        return await open_file(args.get('path', ''))

    elif name == 'get_weather':
        from external_apis import get_weather
        return await get_weather(args.get('location', ''), args.get('units', 'celsius'))

    elif name in ('get_news', 'agent_news'):
        from agents.news_agent import NewsAgent
        agent = NewsAgent()
        return await agent.execute(query=args.get('query', ''), max_results=args.get('max_results', 5))

    elif name in ('get_wikipedia_summary', 'agent_wikipedia'):
        from agents.wikipedia_agent import WikipediaAgent
        agent = WikipediaAgent()
        return await agent.execute(topic=args.get('topic', ''))

    elif name == 'get_system_status':
        from external_apis import get_system_status
        return await get_system_status()

    elif name == 'control_system':
        from system_control import computer_settings_action
        return await computer_settings_action(args.get('action', ''), args.get('value'))

    elif name == 'open_browser':
        raw_url = args.get('url', 'https://www.google.com')
        if sio:
            await sio.emit('open_url', {'url': raw_url})
        return {'message': f'Opened {raw_url} in floating window.', 'url': raw_url}

    elif name == 'open_app':
        from system_app import open_app
        return open_app(args.get('app_name', ''))

    elif name == 'screenshot':
        from system_local import take_screenshot
        return take_screenshot()

    elif name == 'list_processes':
        from system_local import list_processes
        return list_processes(args.get('limit', 10), args.get('sort_by', 'memory'))

    elif name == 'get_active_window':
        from system_local import get_active_window
        return get_active_window()

    elif name == 'run_code':
        from code_runner import run_code
        return run_code(args.get('code', ''), args.get('language', 'auto'), args.get('timeout', 10))

    elif name == 'remember_fact':
        from user_memory import add_fact
        return add_fact(args.get('key', ''), args.get('value', ''))

    elif name == 'recall_facts':
        from user_memory import search_facts
        return search_facts(args.get('query', ''))

    elif name == 'get_user_profile':
        from user_memory import memory_summary
        return memory_summary()

    elif name == 'set_preference':
        from user_memory import set_preference
        return set_preference(args.get('key', ''), args.get('value', ''))

    elif name == 'forget_fact':
        from user_memory import delete_fact
        return delete_fact(args.get('key', ''))

    elif name == 'list_memory':
        import memory_store
        return memory_store.list_memory(type=args.get('type', 'all'), limit=10)

    elif name == 'show_memory':
        from user_memory import list_facts, get_profile
        import memory_store
        profile = get_profile()
        facts = list_facts(limit=50)
        people = memory_store.list_people(limit=20)
        lessons = memory_store.recall_lessons("", limit=10)
        return {
            "profile": profile,
            "facts": facts.get("facts", []),
            "people": people,
            "lessons": lessons,
        }

    elif name == 'remember_person':
        import memory_store
        return memory_store.remember_person(
            args.get('name', ''), args.get('relationship', ''),
            args.get('traits', ''), args.get('preferences', ''), args.get('notes', '')
        )

    elif name == 'recall_person':
        import memory_store
        return memory_store.recall_person(args.get('query', ''), limit=5)

    elif name == 'remember_lesson':
        import memory_store
        return memory_store.remember_lesson(args.get('situation', ''), args.get('correction', ''))

    elif name == 'analyze_screen':
        from screen_vision import analyze_screen
        return await analyze_screen(args.get('prompt', 'Describe what is on the screen in detail.'))

    elif name == 'read_screen_text':
        from screen_vision import read_screen_text
        return await read_screen_text()

    elif name == 'set_reminder':
        from reminders import set_reminder
        return set_reminder(
            args.get('message', ''),
            fire_at=args.get('fire_at'),
            in_seconds=args.get('in_seconds'),
            recurring_seconds=args.get('recurring_seconds'),
        )

    elif name == 'list_reminders':
        from reminders import list_reminders
        return list_reminders()

    elif name == 'cancel_reminder':
        from reminders import cancel_reminder
        return cancel_reminder(args.get('id', ''))

    elif name == 'recognize_face':
        from face_api import encode_face
        from face_store import recognize_face as _match_face
        request_id = str(__import__('uuid').uuid4())
        future = asyncio.Future()
        if audio_loop and hasattr(audio_loop, '_pending_face_frames'):
            audio_loop._pending_face_frames[request_id] = future
        if sio:
            await sio.emit('request_face_frame', {'id': request_id})
        try:
            frame_data = await asyncio.wait_for(future, timeout=5.0)
            image_bytes = base64.b64decode(frame_data)
            enc_result = await encode_face(image_bytes)
            if "error" in enc_result:
                return {"result": enc_result["error"]}
            elif "embedding" in enc_result:
                match = _match_face(enc_result["embedding"])
                return {"result": match.get("name") or "Face not recognized"}
            else:
                return {"result": "No face detected"}
        except asyncio.TimeoutError:
            return {"result": "Camera not responding"}
        finally:
            if audio_loop and hasattr(audio_loop, '_pending_face_frames'):
                audio_loop._pending_face_frames.pop(request_id, None)

    elif name == 'remember_face':
        from face_api import encode_face
        from face_store import store_face
        name_str = args.get('name', '').strip()
        if not name_str:
            return {"result": "Name is required"}
        request_id = str(__import__('uuid').uuid4())
        future = asyncio.Future()
        if audio_loop and hasattr(audio_loop, '_pending_face_frames'):
            audio_loop._pending_face_frames[request_id] = future
        if sio:
            await sio.emit('request_face_frame', {'id': request_id})
        try:
            frame_data = await asyncio.wait_for(future, timeout=5.0)
            image_bytes = base64.b64decode(frame_data)
            enc_result = await encode_face(image_bytes)
            if "error" in enc_result:
                return {"result": enc_result["error"]}
            elif "embedding" in enc_result:
                store_face(name_str, enc_result["embedding"])
                return {"result": f"Remembered {name_str}"}
            else:
                return {"result": "No face detected"}
        except asyncio.TimeoutError:
            return {"result": "Camera not responding"}
        finally:
            if audio_loop and hasattr(audio_loop, '_pending_face_frames'):
                audio_loop._pending_face_frames.pop(request_id, None)

    elif name == 'export_data':
        from export_service import export_data as _export
        fmt = args.get('format', 'markdown')
        title = args.get('title', 'soda_export')
        path = args.get('path', None)
        data = getattr(audio_loop, '_last_scraped_data', None) if audio_loop else None
        if data is None:
            return {'success': False, 'error': 'No scraped data available.'}
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
        return await _export(data, fmt, title, path)

    elif name == 'camera_control':
        action = (args or {}).get('action', '')
        if action == 'close':
            if audio_loop:
                audio_loop._camera_active = False
                audio_loop._latest_camera_frame = None
            if sio:
                await sio.emit('camera_fullscreen_close', {})
            return {'result': 'Full-screen camera closed.'}
        elif action in ('open', 'analyze', 'snapshot'):
            if audio_loop:
                audio_loop._camera_active = True
            if sio:
                await sio.emit('camera_fullscreen_open', {})
            return {'result': 'Full-screen camera opened.'}
        else:
            return {'result': f'Unsupported camera_control action: {action}'}

    elif name == 'view_file':
        path = args.get('path', '')
        mime, _ = mimetypes.guess_type(path)
        mime = mime or 'text/plain'
        if mime.startswith('text/'):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            payload = {'type': 'text', 'content': content, 'mime': mime, 'path': path}
        elif mime.startswith('image/'):
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            payload = {'type': 'image', 'content': b64, 'mime': mime, 'path': path}
        elif mime.startswith('video/'):
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            payload = {'type': 'video', 'content': b64, 'mime': mime, 'path': path}
        else:
            payload = {'type': 'text', 'content': f'[Binary file: {mime}]', 'mime': mime, 'path': path}
        if sio:
            await sio.emit('view_file_content', {'payload': payload})
        return {'viewed': path, 'type': payload['type']}

    elif name.startswith('agent_'):
        from soda_agents import get_global_orchestrator
        orch = get_global_orchestrator()
        agent = orch.get_agent(name)
        if agent:
            return await agent.execute(**args)
        return {'success': False, 'error': f'Unknown agent: {name}'}

    else:
        return {'success': False, 'error': f'Unknown tool: {name}'}
