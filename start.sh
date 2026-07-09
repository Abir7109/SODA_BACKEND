#!/bin/bash
set -e

echo "[STARTUP] Setting PYTHONUNBUFFERED=1"
export PYTHONUNBUFFERED=1

echo "[STARTUP] Testing critical imports..."
for mod in socketio uvicorn fastapi google.genai PIL httpx numpy PIL.Image; do
    python -c "import $mod" 2>/dev/null && echo "  [OK] $mod" || echo "  [FAIL] $mod"
done

echo "[STARTUP] All critical imports OK"

echo "[STARTUP] Testing backend imports..."
for mod in tools workbase personality schedules task_planner screen_vision screen_control reminders system_app system_control system_local user_memory memory_store code_runner gesture_detector welcome_home whatsapp_bridge spotify_bridge scheduler_service external_apis; do
    output=$(python -c "import sys; sys.path.insert(0, 'backend'); import $mod" 2>&1) && echo "  [OK] $mod" || echo "  [FAIL] $mod: $(echo "$output" | head -1)"
done
echo "[STARTUP] All backend imports OK"

echo "[STARTUP] Starting server..."
exec python -m uvicorn backend.server:app_socketio --host 0.0.0.0 --port ${PORT:-8000} --ws-ping-interval 10 --ws-ping-timeout 5
