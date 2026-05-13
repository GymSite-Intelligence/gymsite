"""
Diagnóstico de state após cada agente (debug #124).

after_agent_callback que registra em metrics/state_diagnostics.jsonl:
  - run_id, agent_name, timestamp
  - keys do state (com tamanho e preview do conteúdo)
  - flag de "candidatos vazios" / "concorrentes vazios"

Não altera comportamento; só observa. Pra desligar, remover do _attach_*
em gymsite_intelligence/agent.py.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from tools.token_telemetry import _get_run_id, _resolve_agent_name

JSONL_PATH = Path(__file__).resolve().parent.parent / "metrics" / "state_diagnostics.jsonl"
_LOCK = threading.Lock()

_KEYS_DE_INTERESSE = (
    "market_context",
    "candidatos_geoscout",
    "analise_demografica",
    "concorrentes_brutos",
    "inteligencia_competitiva",
    "analise_financeira",
    "contato_decisor",
    "relatorio_id",
)


def _resumir_valor(v, max_chars: int = 400) -> dict:
    """Resume o conteúdo de uma key do state pra logging."""
    info: dict = {"type": type(v).__name__}
    try:
        if isinstance(v, (dict,)):
            info["dict_keys"] = list(v.keys())
            info["len_keys"] = len(v)
            for sub in ("candidatos", "concorrentes_brutos", "concorrentes_detalhados", "candidatos_filtrados"):
                if sub in v:
                    sv = v.get(sub)
                    info[f"{sub}_type"] = type(sv).__name__
                    if isinstance(sv, list):
                        info[f"{sub}_len"] = len(sv)
        elif isinstance(v, list):
            info["list_len"] = len(v)
            if v and isinstance(v[0], dict):
                info["item0_keys"] = list(v[0].keys())[:8]
        elif isinstance(v, str):
            info["str_len"] = len(v)
            info["preview"] = v[:max_chars]
        else:
            info["preview"] = str(v)[:max_chars]
    except Exception as e:
        info["resumo_err"] = repr(e)
    return info


def after_agent_state_dump(callback_context) -> None:
    """Loga o state após cada agente. Falha silenciosa."""
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return
        # `state` no ADK é proxy; tentamos extrair como dict.
        try:
            state_dict = dict(state)
        except Exception:
            state_dict = {k: state.get(k) for k in _KEYS_DE_INTERESSE if k in state}

        agent_name = _resolve_agent_name(callback_context)
        run_id = _get_run_id()

        entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "agent": agent_name,
            "state_keys": list(state_dict.keys()),
            "keys_de_interesse": {
                k: _resumir_valor(state_dict.get(k))
                for k in _KEYS_DE_INTERESSE
                if k in state_dict
            },
        }

        JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with JSONL_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass
