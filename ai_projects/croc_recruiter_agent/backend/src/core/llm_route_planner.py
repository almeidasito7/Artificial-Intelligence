from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RoutePlan:
    route: str
    tool_name: str | None = None
    tool_input: Dict[str, Any] | None = None


_PROMPT = """
You are Croc Router (a lightweight routing agent). Your task is to route a user message to the correct processing path.

Return ONLY valid JSON (no markdown) with this schema:
{
  "route": "message|access_info|candidates_info|sql|rag",
  "tool_name": string | null,
  "tool_input": object | null
}

Routing rules:
- message: greetings, thanks, small talk, help, "who are you", short conversational responses.
- access_info: questions about "my access", "coverage regions", "what regions/divisions can I access".
- candidates_info: "find a candidate", skills, years of experience; list employee/candidate matches.
- sql: staffing.db structured queries (jobs, candidates, placements) for counts/filters/lists.
- rag: policy/procedure/company documents questions.

If uncertain, prefer:
1) message for simple conversation
2) access_info for access questions
3) candidates_info for candidate searches
4) rag for policy/procedure
5) sql otherwise

Examples:
User: "hi"
{ "route": "message", "tool_name": null, "tool_input": null }

User: "What is my access regions?"
{ "route": "access_info", "tool_name": null, "tool_input": null }

User: "I want a candidate with 5 years of experience in Programming"
{ "route": "candidates_info", "tool_name": null, "tool_input": null }

User: "How many open jobs do we have?"
{ "route": "sql", "tool_name": null, "tool_input": null }

User: "What does our onboarding policy say about background checks?"
{ "route": "rag", "tool_name": null, "tool_input": null }

User message: {question}
""".strip()


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


class LLMRoutePlanner:
    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    def plan(self, question: str) -> RoutePlan | None:
        if self.llm_client is None:
            return None

        try:
            prompt = _PROMPT.replace("{question}", question)
            response = self.llm_client.generate_chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.0,
                max_tokens=250,
            )

            data = _extract_json(response)
            if not isinstance(data, dict):
                return None

            route = (data.get("route") or "").strip()
            tool_name = data.get("tool_name")
            tool_input = data.get("tool_input")

            if tool_name is not None and not isinstance(tool_name, str):
                tool_name = None
            if tool_input is not None and not isinstance(tool_input, dict):
                tool_input = None

            if route not in {
                "message",
                "access_info",
                "candidates_info",
                "sql",
                "rag",
            }:
                return None

            return RoutePlan(route=route, tool_name=tool_name, tool_input=tool_input)

        except Exception as exc:
            logger.exception("llm_route_planner.failed", extra={"error": str(exc)})
            return None
