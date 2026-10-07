"""MCP (Model Context Protocol) layer for SODA.

Adapted from open-jarvis/OpenJarvis (Apache License 2.0).
stdio transport only; SSE/HTTP deferred until needed.
"""

from mcp.client import MCPClient
from mcp.manager import call_registered, connect_servers, disconnect_all, status
from mcp.protocol import MCPError, MCPNotification, MCPRequest, MCPResponse
from mcp.transport import MCPTransport, StdioTransport

__all__ = [
    "MCPClient",
    "MCPError",
    "MCPNotification",
    "MCPRequest",
    "MCPResponse",
    "MCPTransport",
    "StdioTransport",
    "call_registered",
    "connect_servers",
    "disconnect_all",
    "status",
]
