from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    url: str
    method: str = "POST"
    timeout_seconds: float = 10.0


class MCPRegistry:
    def __init__(self, tools_json: str) -> None:
        self._tools: Dict[str, MCPToolSpec] = {}
        for spec in self._parse_tools_json(tools_json):
            self._tools[spec.name] = spec

    def list_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for spec in sorted(self._tools.values(), key=lambda s: s.name):
            tools.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "url": spec.url,
                    "method": spec.method,
                }
            )
        return tools

    def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        spec = self._tools.get(tool_name)
        if spec is None:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        method = (spec.method or "POST").upper()
        if method not in {"POST", "GET"}:
            raise ValueError(f"Unsupported MCP tool method: {method}")

        if method == "GET":
            return self._http_get_json(spec, tool_input)

        return self._http_post_json(spec, tool_input)

    def _http_get_json(self, spec: MCPToolSpec, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        query = urllib.parse.urlencode({"input": json.dumps(tool_input, ensure_ascii=False)})
        url = f"{spec.url}?{query}"
        req = urllib.request.Request(url=url, method="GET")
        with urllib.request.urlopen(req, timeout=spec.timeout_seconds) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload or "{}")

    def _http_post_json(self, spec: MCPToolSpec, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(tool_input, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=spec.url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=spec.timeout_seconds) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload or "{}")

    def _parse_tools_json(self, tools_json: str) -> List[MCPToolSpec]:
        raw = (tools_json or "").strip()
        if not raw:
            return []

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise ValueError(f"Invalid MCP_TOOLS_JSON: {exc}") from exc

        if not isinstance(data, list):
            raise ValueError("MCP_TOOLS_JSON must be a JSON array")

        specs: List[MCPToolSpec] = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("MCP_TOOLS_JSON items must be objects")

            name = item.get("name")
            description = item.get("description") or ""
            url = item.get("url")
            method = item.get("method") or "POST"
            timeout_seconds = item.get("timeout_seconds")

            if not isinstance(name, str) or not name.strip():
                raise ValueError("MCP tool name must be a non-empty string")
            if not isinstance(url, str) or not url.strip():
                raise ValueError(f"MCP tool '{name}' url must be a non-empty string")
            if not isinstance(description, str):
                raise ValueError(f"MCP tool '{name}' description must be a string")

            parsed_timeout: Optional[float]
            if timeout_seconds is None:
                parsed_timeout = None
            elif isinstance(timeout_seconds, (int, float)):
                parsed_timeout = float(timeout_seconds)
            else:
                raise ValueError(f"MCP tool '{name}' timeout_seconds must be a number")

            specs.append(
                MCPToolSpec(
                    name=name.strip(),
                    description=description.strip(),
                    url=url.strip(),
                    method=str(method).strip().upper(),
                    timeout_seconds=parsed_timeout if parsed_timeout is not None else 10.0,
                )
            )

        return specs
