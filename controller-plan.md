# World Monitor × SODA Integration Plan

**Date**: September 2026
**Status**: In Progress
**Author**: Opencode (ponytail mode)

---

## Objective

Integrate [World Monitor](https://github.com/koala73/worldmonitor) (87k+ GitHub stars, AGPL v3) into SODA as a voice-controlled fullscreen dashboard called "the controller."

- Same colors, theme, and options as world-monitor.com
- Voice-controlled with dynamic natural language commands
- Two-sector command system: controller commands (always active) + navigation commands (only when controller is open)

---

## What World Monitor Is

- **Preact SPA** (not React) with Vite, TypeScript
- Uses **globe.gl + Three.js** for 3D globe, **deck.gl + MapLibre GL** for flat map
- Aggregates from 578+ upstream sources: GDELT, USGS, OpenSky, Finnhub, Polymarket, ACLED, 500+ RSS feeds
- 109 panel classes: THE MAP, THE WIRE, THE GLOBE, CHAT, STOCKS, STREAMS, PREDICTIONS, CAMERAS, DEFCON, OUTBREAKS
- Runs locally with Docker or `npm run dev` on port 3000
- No API keys required for basic features (Docker required for full data stack)

---

## Architecture Decision: iframe the Live Site

### Why iframe is the right approach

- World Monitor already works perfectly at worldmonitor.app
- No infrastructure needed — just embed the live site
- Always up-to-date with latest features
- Clean separation of concerns
- ~40 lines of code vs. weeks of integration work

### Trade-offs

| Aspect | iframe (chosen) | Clone + modify | SDK + custom UI |
|--------|----------------|---------------|-----------------|
| Lines of code | ~40 | 500+ | 300+ |
| Setup complexity | Zero | Docker + Redis | npm install + custom UI |
| Matches world-monitor.com | Exact | Exact | Approximate |
| Works offline | No | Yes | Yes |
| Maintenance burden | None | High | Medium |
| AGPL compliance | No issue | Must share source | No issue |

---

## Phased Implementation

### Phase 1: Frontend Panel Component
**Goal**: Create the WorldMonitorPanel component that renders a fullscreen iframe.

| Step | Task | Status |
|------|------|--------|
| 1.1 | Create `src/components/panels/WorldMonitorPanel.jsx` | Done |
| 1.2 | Add CSS styles to `src/styles/main.css` | Done |

**Files**: `src/components/panels/WorldMonitorPanel.jsx` (new, ~80 lines)
**Pattern**: Follows `FullscreenCamera.jsx` pattern — fullscreen overlay with close button.

---

### Phase 2: Frontend State & Socket Integration
**Goal**: Wire up the panel to SODA's state management and socket events.

| Step | Task | Status |
|------|------|--------|
| 2.1 | Add `worldMonitorOpen` state to App.jsx | Done |
| 2.2 | Add socket listener for `world_monitor_open` event | Done |
| 2.3 | Add socket listener for `world_monitor_navigate` event | Done |
| 2.4 | Add `world_monitor` to `close_all` handler | Done |
| 2.5 | Render `<WorldMonitorPanel>` when open | Done |
| 2.6 | Build frontend and verify no errors | Done |

**Files**: `src/App.jsx` (~15 lines added)
**Depends on**: Phase 1 complete.

---

### Phase 3: Backend Tool Definitions
**Goal**: Register the two new tools (`open_world_monitor`, `navigate_world_monitor`) in Gemini's function declarations.

| Step | Task | Status |
|------|------|--------|
| 3.1 | Add `open_world_monitor_tool` declaration to tools.py | Done |
| 3.2 | Add `navigate_world_monitor_tool` declaration to tools.py | Done |
| 3.3 | Add both tools to `tools_list` | Done |

**Files**: `backend/tools.py` (~20 lines added)
**Depends on**: None (can be done in parallel with Phase 1-2).

---

### Phase 4: Backend Dispatch & System Prompt
**Goal**: Handle the tool calls in soda.py and teach Gemini when to use them.

| Step | Task | Status |
|------|------|--------|
| 4.1 | Add `_world_monitor_open` flag init in `run()` | Done |
| 4.2 | Add `open_world_monitor` handler in `_dispatch_tool` | Done |
| 4.3 | Add `navigate_world_monitor` handler with gating logic | Done |
| 4.4 | Add World Monitor section to `_build_system_prompt` | Done |
| 4.5 | Verify backend starts without errors | Done |

**Files**: `backend/soda.py` (~25 lines added)
**Depends on**: Phase 3 complete.

---

### Phase 5: Deploy & Test
**Goal**: Push everything live and verify end-to-end.

| Step | Task | Status |
|------|------|--------|
| 5.1 | Commit all changes | Pending |
| 5.2 | Deploy frontend to Netlify | Pending |
| 5.3 | Push backend to Render | Pending |
| 5.4 | Test: "Open the controller" → fullscreen opens | Pending |
| 5.5 | Test: "Close the controller" → fullscreen closes | Pending |
| 5.6 | Test: Navigation commands when controller is open | Pending |
| 5.7 | Test: Navigation commands when controller is closed → error | Pending |

**Depends on**: Phase 2 + Phase 4 complete.

---

## Voice Command System

### Two Sectors

**Sector 1: Controller commands (always active)**
- "Open the controller" / "Open world map" / "Show me the world"
- Opens the fullscreen World Monitor panel
- Works anytime, no prerequisites

**Sector 2: Navigation commands (only when controller is open)**
- "Open stock market" / "Show the chat" / "What are the predictions?"
- Gated by `_world_monitor_open` boolean flag
- If controller isn't open, SODA says "Open the controller first"
- Commands are dynamic — Gemini matches intent, not exact phrases

### Command Flow

```
User: "Open the controller"
  → Gemini calls open_world_monitor
  → Backend sets _worldMonitorOpen = True
  → Backend emits "world_monitor_open" to frontend
  → Frontend renders <iframe src="https://worldmonitor.app" fullscreen>
  → SODA responds: "Controller open"

User: "Open the stock market"
  → Gemini checks: controller open? (system prompt tells it to check)
  → If open: calls navigate_world_monitor(section="stocks")
  → Backend emits "world_monitor_navigate" with section
  → Frontend posts message to iframe
  → If closed: Gemini calls open_world_monitor FIRST, then navigate

User: "Close the controller"
  → Gemini calls close_panel(panel="world_monitor")
  → Frontend closes the fullscreen iframe
  → Backend resets _worldMonitorOpen = False
```

### Dynamic Matching Examples

| User says | Gemini calls | Action |
|-----------|-------------|--------|
| "Open the controller" | `open_world_monitor` | Opens fullscreen iframe |
| "Show me the world" | `open_world_monitor` | Opens fullscreen iframe |
| "Open stocks" (closed) | `open_world_monitor` | Opens controller first |
| "Open stocks" (open) | `navigate_world_monitor(section="stocks")` | Navigates to stocks |
| "Show me the chat" | `navigate_world_monitor(section="chat")` | Navigates to chat |
| "What are the predictions?" | `navigate_world_monitor(section="predictions")` | Navigates to predictions |
| "Switch to cameras" | `navigate_world_monitor(section="cameras")` | Navigates to cameras |
| "What's happening on the map?" | `navigate_world_monitor(section="map")` | Switches to map view |
| "Close the controller" | `close_panel(panel="world_monitor")` | Closes the panel |

---

## Files Summary

| File | Action | Lines | Phase |
|------|--------|-------|-------|
| `src/components/panels/WorldMonitorPanel.jsx` | **Create** | ~80 | 1 |
| `src/App.jsx` | **Modify** | ~15 | 2 |
| `backend/tools.py` | **Modify** | ~20 | 3 |
| `backend/soda.py` | **Modify** | ~25 | 4 |

---

## AGPL v3 Compliance

- We are **not modifying** World Monitor source code
- We are **not redistributing** World Monitor binaries
- We are **embedding** the live site via iframe (same as embedding a YouTube video)
- No AGPL derivative work triggered — clean integration
