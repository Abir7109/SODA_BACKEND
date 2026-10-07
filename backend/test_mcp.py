"""Self-check for the MCP layer: fake stdio server → connect → list → call.

Run: py -3.11 backend/test_mcp.py
Exits 0 on pass, 1 on failure.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

FAKE_SERVER = r'''
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    method = msg.get("method", "")
    mid = msg.get("id")
    if mid is None:
        continue  # notification
    if method == "initialize":
        result = {"protocolVersion": "2025-03-26",
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "fake", "version": "0.0.1"}}
    elif method == "tools/list":
        result = {"tools": [{
            "name": "echo.tool",
            "description": "Echoes text back",
            "inputSchema": {"type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"]}}]}
    elif method == "tools/call":
        text = msg.get("params", {}).get("arguments", {}).get("text", "")
        result = {"content": [{"type": "text", "text": "echo: " + text}],
                  "isError": False}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
    sys.stdout.flush()
'''


def main() -> int:
    import tempfile

    from tools import tools_list
    from mcp import manager

    server_path = Path(tempfile.gettempdir()) / "soda_fake_mcp_server.py"
    server_path.write_text(FAKE_SERVER, encoding="utf-8")

    before = len(tools_list[0]["function_declarations"])
    n = manager.connect_servers(
        [{"name": "fake", "command": sys.executable, "args": [str(server_path)]}],
        tools_list,
    )
    decls = tools_list[0]["function_declarations"]
    assert n == 1, f"expected 1 tool registered, got {n}"
    assert len(decls) == before + 1, "tools_list not extended"

    # Sanitized name: server__tool, dots replaced
    assert "fake__echo_tool" in manager._registry, manager.status()
    decl = next(d for d in decls if d["name"] == "fake__echo_tool")
    assert decl["parameters"]["properties"]["text"]["type"] == "string"
    assert decl["parameters"]["required"] == ["text"]

    # End-to-end call through the dispatch entry point
    r = asyncio.run(manager.call_registered("fake__echo_tool", {"text": "hi"}))
    assert r == {"success": True, "result": "echo: hi"}, r

    # Unknown name passes through as None (dispatch falls to unknown-tool)
    r2 = asyncio.run(manager.call_registered("not_an_mcp_tool", {}))
    assert r2 is None, r2

    manager.disconnect_all()
    assert manager.status() == {"servers": [], "tools": 0, "names": []}
    assert len(tools_list[0]["function_declarations"]) == before, "decls not removed... (leftover)"

    print("MCP self-check PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"MCP self-check FAILED: {e}")
        sys.exit(1)
