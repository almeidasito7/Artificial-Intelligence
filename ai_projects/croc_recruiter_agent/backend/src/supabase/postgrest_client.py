from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    api_key: str
    schema: str = "office"
    timeout_seconds: float = 10.0


class SupabasePostgrestClient:
    def __init__(self, config: SupabaseConfig) -> None:
        self.config = config

    @property
    def available(self) -> bool:
        return bool(self.config.url.strip()) and bool(self.config.api_key.strip())

    def select(
        self,
        table: str,
        filters: Dict[str, Any] | None = None,
        limit: int = 20,
        order: str | None = None,
    ) -> List[Dict[str, Any]]:
        if not self.available:
            raise RuntimeError("Supabase is not configured (SUPABASE_URL / SUPABASE_*_KEY).")

        base = self.config.url.rstrip("/")
        endpoint = f"{base}/rest/v1/{table}"

        params: Dict[str, str] = {"select": "*", "limit": str(limit)}
        if order:
            params["order"] = order

        for k, v in (filters or {}).items():
            if v is None:
                continue
            params[k] = str(v)

        url = endpoint + "?" + urllib.parse.urlencode(params, doseq=True)

        req = urllib.request.Request(
            url=url,
            method="GET",
            headers={
                "apikey": self.config.api_key,
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json",
                "Accept-Profile": self.config.schema,
            },
        )

        logger.info("supabase.select", extra={"table": table, "url_preview": url[:160]})

        with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
            payload = resp.read().decode("utf-8")
            data = json.loads(payload or "[]")
            if not isinstance(data, list):
                raise RuntimeError("Unexpected Supabase response")
            return data

