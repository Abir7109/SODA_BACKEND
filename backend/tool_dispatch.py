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
import time
from datetime import datetime

import metrics
from logger import log


async def _dispatch_bg_task(name: str, args: dict) -> dict:
    """bg_tasks / opencode — both run headless `npx opencode --prompt` jobs.

    ponytail: one id space (BackgroundAgentManager). opencode_monitor + notebook
    stay the registry for agent_push-driven sessions started by the local agent;
    the two launch paths are not linked.
    """
    from background_agent_manager import BackgroundAgentManager
    action = args.get('action', 'list')
    if name == 'opencode':
        action = {'start': 'spawn', 'stop': 'kill'}.get(action, action)
    if action == 'spawn':
        prompt = args.get('prompt', '').strip()
        if not prompt:
            return {'success': False, 'error': 'prompt is required to spawn a task.'}
        try:
            return await BackgroundAgentManager.spawn(prompt, args.get('workdir', ''))
        except FileNotFoundError:
            return {'success': False,
                    'error': 'Node/npx not found on this machine — cannot launch opencode.'}
        except Exception as e:
            return {'success': False, 'error': f'Failed to spawn task: {e}'}
    if action in ('status', 'get'):
        task_id = args.get('task_id', '')
        if task_id:
            st = BackgroundAgentManager.get_status(task_id)
            return st or {'success': False, 'error': f'No such task: {task_id}'}
        return {'tasks': BackgroundAgentManager.list_tasks()}
    if action == 'kill':
        st = await BackgroundAgentManager.kill(args.get('task_id', ''))
        return st or {'success': False, 'error': f"No such task: {args.get('task_id', '')}"}
    if action == 'list':
        return {'tasks': BackgroundAgentManager.list_tasks()}
    return {'success': False, 'error': f'Unknown {name} action: {action}'}


async def dispatch_local_tool(name: str, args: dict, sio=None, audio_loop=None) -> dict:
    """
    Execute a tool locally on the server side (timed — single metrics choke point).

    Args:
        name: Tool name (e.g. 'terminal_execute', 'get_weather').
        args: Tool arguments dict.
        sio: Socket.IO server instance (for emit-based tools).
        audio_loop: AudioLoop instance (for tools that need session state).

    Returns:
        Tool result dict.
    """
    t0 = time.perf_counter()
    try:
        r = await _dispatch_local_tool(name, args, sio, audio_loop)
    except Exception:
        metrics.record_tool_run(name, (time.perf_counter() - t0) * 1000, False)
        raise
    ok = not (isinstance(r, dict) and (r.get("error") or r.get("success") is False))
    metrics.record_tool_run(name, (time.perf_counter() - t0) * 1000, ok)
    return r


async def _dispatch_local_tool(name: str, args: dict, sio=None, audio_loop=None) -> dict:
    if name == 'get_metrics':
        from metrics import get_summary
        return {'success': True, **get_summary(args.get('window_hours', 1))}

    elif name == 'terminal_execute':
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

    elif name == 'recall_by_relationship':
        import memory_store
        return memory_store.recall_by_relationship(args.get('relationship', ''), limit=5)

    elif name == 'search_youtube':
        from system_app import search_youtube
        return await asyncio.to_thread(search_youtube, args.get('query', ''))

    elif name == 'plan':
        import task_planner
        action = args.get('action', 'get')
        if action == 'create':
            r = task_planner.plan_tasks(args.get('title', ''), args.get('tasks', []))
        elif action == 'update':
            r = task_planner.update_task(args.get('task_id', ''), args.get('status', 'done'), args.get('result'))
        elif action == 'cancel':
            r = task_planner.cancel_plan()
        else:
            r = task_planner.get_active_plan()
        if sio and isinstance(r, dict) and r.get('id'):
            await sio.emit('task_plan_update', r)
        return r

    elif name == 'cancel_plan':
        import task_planner
        return task_planner.cancel_plan()

    elif name == 'github':
        import github_tools as gh
        action = args.get('action', '')
        calls = {
            'list_repos': lambda: gh.list_repos(args.get('owner')),
            'create_repo': lambda: gh.create_repo(args.get('name', ''), args.get('description', ''),
                                                   args.get('private', False), args.get('auto_init', False)),
            'get_repo': lambda: gh.get_repo(args.get('repo', '')),
            'create_pr': lambda: gh.create_pr(args.get('repo', ''), args.get('title', ''),
                                              args.get('body', ''), args.get('head', ''), args.get('base', 'main')),
            'list_issues': lambda: gh.list_issues(args.get('repo', ''), args.get('state', 'open')),
            'create_issue': lambda: gh.create_issue(args.get('repo', ''), args.get('title', ''), args.get('body', '')),
        }
        if action not in calls:
            return {'success': False, 'error': f'Unknown github action: {action}'}
        # ponytail: `gh` CLI is blocking — run off the event loop
        return await asyncio.to_thread(calls[action])

    elif name == 'vercel':
        import vercel_tools as vc
        action = args.get('action', '')
        calls = {
            'list_projects': lambda: vc.list_projects(),
            'deploy': lambda: vc.deploy(args.get('path', '.'), args.get('name'), args.get('prod', False)),
            'list_deployments': lambda: vc.list_deployments(args.get('project'), args.get('limit', 20)),
            'get_deployment': lambda: vc.get_deployment(args.get('url_or_id', '')),
        }
        if action not in calls:
            return {'success': False, 'error': f'Unknown vercel action: {action}'}
        return await asyncio.to_thread(calls[action])

    elif name == 'netlify':
        import netlify_tools as nl
        action = args.get('action', '')
        calls = {
            'list_sites': lambda: nl.list_sites(),
            'get_site': lambda: nl.get_site(args.get('site_id', '')),
            'deploy': lambda: nl.deploy(args.get('path', '.'), args.get('prod', False), args.get('message', '')),
            'create_site': lambda: nl.create_site(args.get('name')),
            'list_deploys': lambda: nl.list_deploys(args.get('site_id', '')),
        }
        if action not in calls:
            return {'success': False, 'error': f'Unknown netlify action: {action}'}
        return await asyncio.to_thread(calls[action])

    elif name == 'deep_research':
        from research_engine import deep_research
        try:
            return await asyncio.wait_for(
                deep_research(args.get('topic', ''), args.get('depth', 'normal')), timeout=180)
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Research timed out after 3 minutes. Narrow the topic and retry.'}

    elif name == 'export_research':
        from research_engine import export_research
        raw = args.get('research_data', '')
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return {'success': False, 'error': 'research_data is not valid JSON.'}
        return await export_research(raw, args.get('format', 'json'))

    elif name == 'notebook_read':
        from notebook import read_task
        r = await read_task(args.get('task_id', ''))
        return r or {'success': False, 'error': f"No notebook entry for task {args.get('task_id', '')}"}

    elif name == 'notebook_search':
        from notebook import search_tasks
        return await search_tasks(args.get('keyword', ''))

    elif name in ('opencode', 'bg_tasks'):
        return await _dispatch_bg_task(name, args)

    elif name.startswith('agent_'):
        from soda_agents import get_global_orchestrator
        orch = get_global_orchestrator()
        agent = orch.get_agent(name)
        if agent:
            return await agent.execute(**args)
        return {'success': False, 'error': f'Unknown agent: {name}'}

    # ── MCP tools (mcp_servers in settings.json) ──
    from mcp import call_registered
    r = await call_registered(name, args)
    if r is not None:
        return r

    # ── Skills (projects/skills/*.toml) ──
    from skills import call_registered as call_skill
    r = await call_skill(name, args, sio=sio, audio_loop=audio_loop)
    if r is not None:
        return r

    return {'success': False, 'error': f'Unknown tool: {name}'}
