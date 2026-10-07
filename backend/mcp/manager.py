"""MCP server manager — connects configured servers, registers their tools.

SODA glue over mcp.client/transport. Config lives in settings.json:

    "mcp_servers": [
        {"name": "fs", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]},
        {"name": "gh", "command": "uvx", "args": ["mcp-server-github"],
         "env": {"GITHUB_TOKEN": "..."}, "cwd": "C:/work"}
    ]

Empty/absent list = disabled. Connecting appends Gemini function
declarations to tools.list[0]["function_declarations"] and routes calls
through call_registered().

ponytail: no auto-reconnect — a crashed server returns errors until the
next backend restart. Add a health-check/reconnect loop if it ever bites.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, Optional

from logger import log
from mcp.client import MCPClient
from mcp.transport import StdioTransport

# prefixed Gemini tool name -> (server_name, original_tool_name)
_registry: Dict[str, tuple] = {}
# server_name -> MCPClient
_clients: Dict[str, MCPClient] = {}
# server_name -> decl names it contributed to tools_list (for removal)
_server_decls: Dict[str, list] = {}
# reference to tools_list[0]["function_declarations"] (set on first connect)
_decls: Optional[list] = None
# full Gemini name set (built-ins + MCP) for collision checks
_known_names: Optional[set] = None

_MAX_NAME = 60  # Gemini caps function names; keep headroom for suffixes


def _sanitize(raw: str) -> str:
    """Gemini function names: [A-Za-z0-9_-] only, must not be blank."""
    s = re.sub(r"[^A-Za-z0-9_-]", "_", raw)
    return s or "tool"


def _build_registry_name(server: str, tool: str) -> str:
    """<server>__<tool>, de-duplicated against built-ins + MCP registry."""
    base = _sanitize(f"{server}__{tool}")[:_MAX_NAME]
    taken = set(_registry)
    if _known_names:
        taken |= _known_names
    name = base
    i = 2
    while name in taken:
        suffix = f"_{i}"
        name = base[: _MAX_NAME - len(suffix)] + suffix
        i += 1
    return name


def _tool_decl(name: str, description: str, schema: Dict[str, Any]) -> dict:
    """Gemini function declaration from an MCP tool descriptor."""
    schema = dict(schema or {})
    # Gemini rejects unknown top-level JSON Schema keys in some paths;
    # pass through only what it understands.
    props = schema.get("properties") or {}
    required = schema.get("required") or []
    decl: Dict[str, Any] = {
        "name": name,
        "description": (description or f"MCP tool {name}")[:1024],
        "parameters": {"type": "object", "properties": props},
    }
    if required:
        decl["parameters"]["required"] = required
    return decl


def _flatten_result(res: Dict[str, Any]) -> Dict[str, Any]:
    """MCP content blocks -> SODA-style result dict."""
    parts = []
    for block in res.get("content") or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "image":
            parts.append("[image content omitted]")
        else:
            parts.append(str(block.get("text") or block))
    text = "\n".join(p for p in parts if p)
    if res.get("isError"):
        return {"success": False, "error": text or "MCP tool reported an error"}
    return {"success": True, "result": text}


def connect_servers(configs: list, tools_list) -> int:
    """Connect every configured server and merge tools into tools_list.

    Blocking (spawns processes + handshakes) — call from a thread or at
    startup before serving. Returns number of tools registered.
    Never raises: one bad server must not kill startup.
    """
    global _known_names, _decls
    if not configs:
        return 0
    decls = tools_list[0]["function_declarations"]
    _decls = decls
    if _known_names is None:
        _known_names = {d.get("name") for d in decls}

    registered = 0
    for cfg in configs:
        server = str(cfg.get("name") or "").strip()
        command = str(cfg.get("command") or "").strip()
        args = [str(a) for a in (cfg.get("args") or [])]
        if not server or not command:
            log.warning(f"[MCP] Skipping config without name/command: {cfg}")
            continue
        if server in _clients:
            log.warning(f"[MCP] Server '{server}' already connected, skipping")
            continue

        env = None
        if cfg.get("env"):
            env = {**os.environ, **{str(k): str(v) for k, v in cfg["env"].items()}}

        transport = None
        try:
            transport = StdioTransport(
                [command, *args],
                env=env,
                cwd=cfg.get("cwd"),
                response_timeout=float(cfg.get("timeout", 600)),
            )
            client = MCPClient(transport)
            client.initialize()
            tools = client.list_tools()
        except Exception as e:
            log.warning(f"[MCP] Failed to connect server '{server}': {e}")
            if transport is not None:
                try:
                    transport.close()
                except Exception:
                    pass
            continue

        _clients[server] = client
        added = []
        n = 0
        for t in tools:
            orig = t.get("name", "")
            if not orig:
                continue
            reg_name = _build_registry_name(server, orig)
            _registry[reg_name] = (server, orig)
            decls.append(_tool_decl(reg_name, t.get("description", ""), t.get("inputSchema")))
            added.append(reg_name)
            n += 1
        _server_decls[server] = added
        registered += n
        log.info(f"[MCP] Connected '{server}' — {n} tools registered")

    if registered:
        log.info(f"[MCP] {registered} MCP tools now available "
                 f"(servers: {', '.join(_clients) or 'none'})")
    return registered


async def call_registered(name: str, args: dict) -> Optional[Dict[str, Any]]:
    """Call an MCP tool by its registered Gemini name.

    Returns None if the name isn't an MCP tool (caller falls through to
    the normal unknown-tool error).
    """
    entry = _registry.get(name)
    if entry is None:
        return None
    server, orig = entry
    client = _clients.get(server)
    if client is None or client.closed:
        return {"success": False,
                "error": f"MCP server '{server}' is not connected. "
                         f"Restart SODA backend to retry."}
    try:
        res = await asyncio.to_thread(client.call_tool, orig, args or {})
        return _flatten_result(res)
    except Exception as e:
        return {"success": False, "error": f"MCP tool '{name}' failed: {e}"}


def status() -> dict:
    """Connected servers + tool counts (for logs/diagnostics)."""
    return {
        "servers": list(_clients),
        "tools": len(_registry),
        "names": sorted(_registry),
    }


def disconnect_all() -> None:
    """Close every server connection and drop their declarations (shutdown path)."""
    for server, client in list(_clients.items()):
        try:
            client.close()
            log.info(f"[MCP] Disconnected '{server}'")
        except Exception as e:
            log.warning(f"[MCP] Error closing '{server}': {e}")
    if _decls is not None:
        drop = {n for names in _server_decls.values() for n in names}
        _decls[:] = [d for d in _decls if d.get("name") not in drop]
    _clients.clear()
    _registry.clear()
    _server_decls.clear()
