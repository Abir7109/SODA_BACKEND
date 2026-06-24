# SODA Development Standards (Claude & Stitch)
**Location**: Project root `AGENTS.md`
**Applies to**: All UI and backend development for SODA Tactical HUD

## Quick Reference

### Socket.IO Events (Backend -> Frontend)
- `connect`, `disconnect`
- `status`, `audio_data`, `transcription`
- `tool_confirmation_request`, `window_control`
- `project_update`, `settings`, `error`
- `command_output` (after `terminal_execute` runs — payload `{command, output, success}`)
- `search_results` (after `web_search_live` runs — payload `{query, results: [{title, url, snippet}]}`)
- `tool_result` (after `force_tool` runs — payload `{tool, result, forced}`)
- `auth_status` (always emitted as authenticated; legacy listener compat)
- `open_url` (open a URL in floating webview window — payload `{url}`)
- `webview_action` (perform action inside a webview — payload `{id, action, params}`)
- `close_panel` (close a panel by name — payload `{panel}`)
- `workflow_start` (launch a workflow HUD animation — payload `{workflow, ...data}`)
- `news_briefing_control` (navigate article in news briefing — payload `{action, index}`)
- `stop_audio` (stop current audio playback — no payload)
- `web_builder_status` (website builder status update — payload `{phase, message, timestamp, builder?, prompt_preview?, elapsed?}`)
- `web_builder_progress` (website builder build progress — payload `{progress, message, phase, timestamp}`)

### Socket.IO Events (Frontend -> Backend)
- `webview_action_result` (result from a webview action — payload `{id, action, result}`)
- `video_frame` (camera frame capture — payload `{data: base64}`)
- Translation events are no longer in use (removed)

### Tools (Backend -> Gemini Function Declarations)
- `get_pagespeed_insights` — calls Google PageSpeed Insights API (free), returns Lighthouse SEO/performance/accessibility scores, Core Web Vitals, and ranked optimization opportunities. Registered in `backend/tools.py` as function declaration, dispatched in `backend/soda.py:_dispatch_tool`. Panel: `PageSpeedPanel` (slide-right).

### Webview Action Service (`src/services/WebviewActionService.js`)
Singleton managing webview instances. Actions:
- `click(id, selector)` — click an element
- `type(id, selector, text)` — type into an input
- `scroll(id, x, y)` — scroll page
- `getContent(id)` — get page text/links/URL
- `getUrl(id)` / `goBack(id)` / `goForward(id)` — navigation
- `navigate(id, url)` — load new URL in webview
- `waitForLoad(id)` — wait for page to finish loading
- `executeJS(id, code)` — run arbitrary JavaScript
- `register(id, webviewEl)` / `unregister(id)` — lifecycle

### Panel Space Context (`src/contexts/PanelSpaceContext.jsx`)
Auto-positions slide panels to avoid overlap:
- `registerPanel(direction)` / `unregisterPanel(direction)`
- `getOffset(direction)` returns `{offsetX, offsetY}`
- Top panels shift right (+160px) to avoid center orb
- Bottom panels shift right (+200px)
- Floating windows avoid left/right panel zones via `findFreeFloatPosition`

### Frontend APIs (Preserve)
- MediaPipe Hand Tracking (@mediapipe/tasks-vision)
- Web Audio API (Microphone visualization)
- MediaDevices API (getUserMedia, enumerateDevices)
- Speech Recognition (window.SpeechRecognition) - if used by future components
- LocalStorage (user preferences, e.g. selected mic id)

### Electron Build Chain
```bash
npm run dev      # Vite dev server + Electron
npm run build    # Vite build -> dist/
npm run electron # Electron loads dist/
```

### Backend Run
```bash
pip install -r requirements.txt
py -3.11 server.py  # FastAPI + Socket.IO on :8000
```

### Component Structure
- Single-file React components in `src/`
- Default export: `export default function ComponentName() { }`
- Use Lucide React icons: `import { Mic } from 'lucide-react'`

### Design Tokens
Colors, typography, and spacing are defined as CSS custom properties in
`src/styles/main.css` and exposed via Tailwind utility classes.

## DO NOT
- Use Next.js, SSR, or external state libraries (Redux/Zustand/etc.)
- Add rounded corners or center-aligned layouts
- Use Tailwind CDN (use CSS files)
- Import Node.js modules directly in renderer code
- Re-add removed subsystems: CAD, web automation, face auth, printers,
  Kasa smart home, phone calls, Telegram, Ollama

## Workflow System (Current State)

### Socket Events Added
| Event | Direction | Payload | Purpose |
|---|---|---|---|
| `workflow_start` | backend→frontend | `{workflow, articles?, profile?, facts?, people?, lessons?, ...}` | Launch HUD animation |
| `news_briefing_control` | backend→frontend | `{action, index?}` | Navigate news articles |
| `stop_audio` | backend→frontend | `{}` | Stop playback (barge-in) |
| `video_frame` | frontend→backend | `{data: base64}` | Camera frame from browser |

### Backend Handlers (`soda.py:_dispatch_tool`)
- **`get_news`** — Calls `get_news_briefing()` (multi-category DDG/RSS), emits `workflow_start` with `workflow:"news-briefing"`
- **`news_control`** — Emits `news_briefing_control` with `{action, index}` for article navigation
- **`show_memory`** — Collects profile/facts/people/lessons, emits `workflow_start` with `workflow:"memory-view"`
- **`start_workflow`** — Emits `workflow_start` with any named workflow from `WORKFLOW_MAP`
- **`close_panel`** — Accepts `"workflow"` and `"all"` panel values to dismiss active workflow
- Workflow auto-triggered in `receive_audio` via `workflow_intent.match_with_context()` (word2vec keyword matching)

### Frontend Integration (`App.jsx`)
- Imports `WorkflowOverlay` from `src/components/workflows/WorkflowOverlay.jsx`
- State `workflow` and refs `workflowRef`, `workflowDismissRef`
- `socket.on('workflow_start')` → `setWorkflow(data)`
- `socket.on('news_briefing_control')` → merges `newsControl` into workflow state
- `socket.on('transcription')` → auto-dismiss non-animated workflows after 60s
- `onClosePanel` handles `"workflow"` and `"all"`
- `WorkflowOverlay` renders inside `<CameraCapture />` area

### Workflow Components (`src/components/workflows/`)
- `index.js` — Exports `WORKFLOW_MAP` (workflow name → lazy component)
- `WorkflowOverlay.jsx` — Renders active workflow, passes `data` and `onComplete`
- `WorkflowNewsBriefing.jsx` — 6-phase animation with Electron `<webview>` article browser
- `WorkflowMemoryView.jsx` — 7-phase animation for memory database
- 11 animated workflow components (startup, morning, outside, etc.)

### Audio Pipeline (Echo-Safe)
- `listen_audio()`: mic input buffered while `_model_is_speaking`; buffer flushed when model stops
- `play_audio()`: sets `_model_is_speaking = False` when `audio_in_queue` empty for 0.2s
- `receive_audio()`: sets `_model_is_speaking = True` on first audio data chunk
- `_clear_queues()`: clears `video_queue` and `_audio_buffer` when Gemini starts responding (preserves `audio_queue` — pending user audio continues to drain)
- VAD threshold: `VAD_THRESHOLD = 150` RMS
- Server-side VAD enabled: `automatic_activity_detection` with `start_of_speech_sensitivity=0.5`, `end_of_speech_sensitivity=0.5`, `prefix_padding_ms=500`, `silence_duration_ms=1000`
- Interruption/barge-in is NOT implemented in current audio pipeline (mic fully muted during playback)

### Latency Optimization (Critical)
- `session.send()` is **deprecated** — use `send_realtime_input(audio=Blob(...))` for live audio (same websocket message, skips ordering guarantees for faster processing)
- `send_client_content(turns=Content(...), turn_complete=True)` replaces `session.send(input=string, end_of_turn=True)` for start messages
- **Server-side VAD is ENABLED**. No client-side `activity_start`/`activity_end` signals — the Gemini server handles voice activity detection automatically.
- `speech_config.language_code` is **NOT supported** for `gemini-2.5-flash-native-audio-latest` — the model rejects the setup with code 1007
- `AudioTranscriptionConfig.languageCode` is NOT sent through pydantic serialization (LiveConnectParameters caches original schema — extra fields stripped)
- `context_window_compression` should be omitted entirely — low `trigger_tokens` adds latency on every turn

### Spotify Playback (Spicetify Bridge — see final architecture below)

### Key Notes
- `npm run dev` uses `py -3.11` — default `python` (3.12+) crashes `server.py`
- Electron `<webview>` requires `webviewTag: true` in `electron/main.js`
- News RSS fails often; DDG HTML scraping is fallback via `_parse_ddg_html()`
- `get_news` handler has 5s cooldown (`_last_news_briefing`)

### Spotify Bridge (Final Architecture)

**Spicetify extension** at `%LOCALAPPDATA%\spicetify\Extensions\soda_spotify_bridge.js`:
- Connects to Python WebSocket server at `ws://127.0.0.1:18920`
- Loads inside Spotify's CEF browser via Spicetify injection
- **Playback control**: Uses `Spicetify.Player` API — `playUri()`, `togglePlay()`, `next()`, `back()`, `setVolume()`
- **Search**: Uses Pathfinder GraphQL API via **direct `fetch()`** (CosmosAsync skips auth for `api-partner.spotify.com`)
  - Auth token from `Spicetify.Platform.AuthorizationAPI.getState().token.accessToken`
  - Query operation `searchDesktop` with SHA-256 hash `4801118d4a100f756e833d33984436a3899cff359c532f8fd3aaf174b60b3b49`
  - URL: `https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchDesktop&variables=...&extensions=...`
  - Normalizes Pathfinder response → Web API format (`tracks.items[].{name,artists,album,uri,id}`)

**Python bridge** at `backend/spotify_bridge.py`:
- Starts `websockets.serve` on port 18920 in background thread
- `_send_command()` sends JSON over WebSocket, blocks on `threading.Event` for response
- Public API: `search()`, `play_track()`, `play_uri()`, `play_music()`, `play_pause()`, `resume()`, `next_track()`, `previous_track()`, `set_volume()`, `get_status()`

**No UI automation** — no pyautogui, no OCR, no screen coordinates.
**No Playwright** — all token acquisition goes through Spicetify's in-app session.
**No rate limits** — Pathfinder uses desktop session auth, separate pool from `api.spotify.com`.
**Spicetify CLI**: `spicetify apply --bypass-admin` then `spicetify restart` to load patched app.
**Refresh after extension changes**: `spicetify refresh -e` then `spicetify restart`.
