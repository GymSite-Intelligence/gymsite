"""MCP GymSite — tools por segmento de mercado."""

from __future__ import annotations

import json
from typing import Any


def segment_tool_text(result: Any) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
