# tools/token_telemetry.py
"""
Telemetria de tokens por agente do pipeline ADK.

Usa **before/after_model_callback** (não agent_callback) porque:
- agent_callback NÃO recebe usage_metadata
- model_callback recebe llm_response com prompt_token_count e
  candidates_token_count diretamente do response do Gemini

Cada chamada LLM é registrada em metrics/tokens_pipeline.csv.
Um agente pode aparecer múltiplas vezes (vários LLM calls em uma execução)
— isso é correto e mostra o custo real por interação.
"""
import csv
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

METRICS_DIR = Path(__file__).resolve().parent.parent / "metrics"
CSV_PATH = METRICS_DIR / "tokens_pipeline.csv"
CSV_HEADER = [
    "run_id",
    "timestamp",
    "agent_name",
    "tokens_in",
    "tokens_out",
    "tokens_total",
    "model",
    "fonte_usage",
    "finish_reason",   # diagnóstico de OUT=0 — VEC-380
]

_WRITE_LOCK = threading.Lock()
_run_id_holder = {"value": None}


def _ensure_csv_header() -> None:
    """
    Garante que o CSV existe e que o header está atualizado.

    Se o CSV existir com header desatualizado (menos colunas que CSV_HEADER),
    faz backup do arquivo antigo (sufixo `.legacy_YYYYMMDD.csv`) e cria um
    novo com o header correto. Histórico anterior é preservado no backup.
    """
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        if not CSV_PATH.exists():
            with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_HEADER)
            return

        # Migração de header: se header atual diverge de CSV_HEADER em
        # número de colunas, faz backup e recria.
        try:
            with CSV_PATH.open("r", encoding="utf-8") as f:
                first_line = f.readline().strip()
            existing_header = first_line.split(",") if first_line else []
            if len(existing_header) != len(CSV_HEADER):
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = CSV_PATH.with_name(
                    f"{CSV_PATH.stem}.legacy_{stamp}{CSV_PATH.suffix}"
                )
                CSV_PATH.replace(backup_path)
                with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(CSV_HEADER)
        except Exception:
            pass  # nunca bloqueia a telemetria por problema de migração


def _new_run_id() -> str:
    rid = uuid.uuid4().hex[:12]
    _run_id_holder["value"] = rid
    return rid


def _get_run_id() -> str:
    return _run_id_holder["value"] or _new_run_id()


def _resolve_agent_name(callback_context) -> str:
    """Tenta múltiplos paths pra obter nome do agente."""
    # ADK moderno: property direta
    name = getattr(callback_context, "agent_name", None)
    if name:
        return str(name)
    # Fallback: invocation_context.agent.name
    for ic_attr in ("_invocation_context", "invocation_context"):
        ic = getattr(callback_context, ic_attr, None)
        if ic is None:
            continue
        agent = getattr(ic, "agent", None)
        if agent is not None:
            n = getattr(agent, "name", None)
            if n:
                return str(n)
    return "?"


def _resolve_model_name(callback_context, llm_response=None) -> str:
    """Modelo da resposta ou do agente."""
    if llm_response is not None:
        m = getattr(llm_response, "model", None)
        if m:
            return str(m)
    for ic_attr in ("_invocation_context", "invocation_context"):
        ic = getattr(callback_context, ic_attr, None)
        if ic is None:
            continue
        agent = getattr(ic, "agent", None)
        if agent is not None:
            m = getattr(agent, "model", None)
            if m:
                return str(m)
    return "?"


def _extract_finish_reason(llm_response) -> str:
    """
    Extrai finish_reason do LlmResponse. Crítico para diagnóstico
    de OUT=0 — distingue STOP (modelo decidiu não emitir), MAX_TOKENS
    (output truncado), MALFORMED_FUNCTION_CALL (tool schema inválido),
    SAFETY (filtro de segurança), RECITATION, OTHER.

    No ADK, `finish_reason` é atributo DIRETO do LlmResponse (ver
    google/adk/models/llm_response.py:83). `error_code` também é
    promovido ao topo quando a resposta termina por erro
    (linha 182 — error_code=candidate.finish_reason).

    Retorna "?" se não encontrar; nunca bloqueia gravação.
    """
    if llm_response is None:
        return "no_response"
    try:
        # Path 1: ADK LlmResponse — atributo direto (caso comum em runtime)
        fr = getattr(llm_response, "finish_reason", None)
        ec = getattr(llm_response, "error_code", None)

        if ec:
            # error_code aparece quando finish_reason indica erro (MALFORMED, etc).
            # Prefere error_code porque é mais específico que finish_reason quando ambos existem.
            ec_name = getattr(ec, "name", None)
            return f"ERROR:{ec_name or ec}"

        if fr is not None:
            name = getattr(fr, "name", None)
            return str(name) if name is not None else str(fr)

        # Path 2: GenerateContentResponse raw — candidates[0].finish_reason
        cands = getattr(llm_response, "candidates", None) or []
        if cands:
            c0_fr = getattr(cands[0], "finish_reason", None)
            if c0_fr is not None:
                name = getattr(c0_fr, "name", None)
                return str(name) if name is not None else str(c0_fr)

        return "?"
    except Exception:
        return "?"


def _extract_usage(llm_response) -> dict:
    """
    Extrai tokens do llm_response.usage_metadata, tentando múltiplos paths.

    Retorna dict com tokens E flag 'fonte' indicando de onde veio (debug).
    """
    out = {"tokens_in": 0, "tokens_out": 0, "tokens_total": 0, "fonte": "vazio"}
    if llm_response is None:
        out["fonte"] = "llm_response_none"
        return out

    # Path 1: ADK padrão
    um = getattr(llm_response, "usage_metadata", None)
    fonte = "usage_metadata"

    # Path 2: campo privado
    if um is None:
        um = getattr(llm_response, "_usage_metadata", None)
        fonte = "_usage_metadata"

    # Path 3: response_metadata.usage
    if um is None:
        rm = getattr(llm_response, "response_metadata", None) or {}
        um = (rm.get("usage") if isinstance(rm, dict) else getattr(rm, "usage", None))
        fonte = "response_metadata.usage"

    # Path 4: navegar candidates[0].content (raro)
    if um is None:
        cands = getattr(llm_response, "candidates", None) or []
        for c in cands:
            cum = getattr(c, "usage_metadata", None)
            if cum is not None:
                um = cum
                fonte = "candidates[0].usage_metadata"
                break

    if um is None:
        out["fonte"] = "nao_encontrado"
        return out

    # Aceita dict ou objeto
    if isinstance(um, dict):
        out["tokens_in"] = int(um.get("prompt_token_count", 0) or 0)
        out["tokens_out"] = int(um.get("candidates_token_count", 0) or 0)
        out["tokens_total"] = int(um.get("total_token_count", 0) or 0)
    else:
        out["tokens_in"] = int(getattr(um, "prompt_token_count", 0) or 0)
        out["tokens_out"] = int(getattr(um, "candidates_token_count", 0) or 0)
        out["tokens_total"] = int(getattr(um, "total_token_count", 0) or 0)

    if out["tokens_total"] == 0:
        out["tokens_total"] = out["tokens_in"] + out["tokens_out"]

    out["fonte"] = fonte
    return out


def reset_run_id() -> None:
    _run_id_holder["value"] = None


def caminho_csv() -> Path:
    return CSV_PATH


def prune_tokens_csv(max_age_days: int | None = None) -> int:
    """
    Remove linhas do CSV com timestamp anterior a max_age_days.

    Env: TELEMETRY_CSV_RETENTION_DAYS (default 90). Use 0 para desabilitar.
    Retorna quantidade de linhas removidas.
    """
    if max_age_days is None:
        max_age_days = int(os.getenv("TELEMETRY_CSV_RETENTION_DAYS", "90"))
    if max_age_days <= 0 or not CSV_PATH.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    kept_rows: list[list] = []

    with _WRITE_LOCK:
        try:
            with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return 0
                kept_rows.append(header)
                for row in reader:
                    if len(row) < 2:
                        kept_rows.append(row)
                        continue
                    try:
                        ts = datetime.fromisoformat(row[1])
                    except ValueError:
                        kept_rows.append(row)
                        continue
                    if ts >= cutoff:
                        kept_rows.append(row)
                    else:
                        removed += 1

            if removed == 0:
                return 0

            tmp = CSV_PATH.with_suffix(".csv.tmp")
            with tmp.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows(kept_rows)
            tmp.replace(CSV_PATH)
        except Exception:
            return 0

    return removed


# ── Callbacks ADK ───────────────────────────────────────────────

def before_agent_callback(callback_context) -> None:
    """Pre-agent: garante run_id e CSV inicializado."""
    try:
        _ensure_csv_header()
        if _run_id_holder["value"] is None:
            _new_run_id()
    except Exception:
        pass


def after_model_callback(callback_context, llm_response) -> None:
    """
    Pós-LLM: registra TODA chamada (mesmo se usage_metadata vazio).

    Logar mesmo com 0 tokens permite ver qual agente está faltando
    captura de usage_metadata — se tudo for 0, saber qual fonte
    falhou (campo `fonte_usage`).
    """
    try:
        _ensure_csv_header()
        usage = _extract_usage(llm_response)
        agent_name = _resolve_agent_name(callback_context)
        model = _resolve_model_name(callback_context, llm_response)
        finish_reason = _extract_finish_reason(llm_response)

        row = [
            _get_run_id(),
            datetime.now().isoformat(timespec="seconds"),
            agent_name,
            usage["tokens_in"],
            usage["tokens_out"],
            usage["tokens_total"],
            model,
            usage["fonte"],
            finish_reason,
        ]
        with _WRITE_LOCK:
            with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)
    except Exception:
        pass


# Mantém alias para retrocompatibilidade com agent.py
after_agent_callback = lambda ctx: None  # no-op (substituído por after_model_callback)
