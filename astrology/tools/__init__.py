"""P2 local tools. Not connected to HTTP handlers or an LLM/agent registry."""

from .registry import describe_tools, invoke_tool

__all__ = ["invoke_tool", "describe_tools"]
