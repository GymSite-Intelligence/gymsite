"""
GymSite MCP Server — Protocolo MCP (Model Context Protocol) para VectraClaw
Expõe as funcionalidades do GymSite como tools que agentes podem usar.

Transport: HTTP (JSON-RPC)
Auth: Bearer token (GYMSITE_API_KEY)
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from mcp.segments import segment_tool_text
from mcp.segments.listings import LISTINGS_HANDLERS, LISTINGS_TOOLS
from mcp.segments.mercado import MERCADO_HANDLERS, MERCADO_TOOLS
from mcp.segments.reviews import REVIEWS_HANDLERS, REVIEWS_TOOLS
from mcp.segments.social import SOCIAL_HANDLERS, SOCIAL_TOOLS

# ─── Config ─────────────────────────────────────────────────────────────────
GYMSITE_API_BASE = os.getenv("GYMSITE_API_BASE", "http://127.0.0.1:8000")
GYMSITE_API_KEY = os.getenv("GYMSITE_API_KEY", "")
SERVER_NAME = "gymsite-mcp"
SERVER_VERSION = "1.2.0"

_SEGMENT_TOOL_PREFIXES = (
    "gymsite_mercado_",
    "gymsite_reviews_",
    "gymsite_social_",
    "gymsite_listings_",
)

MCP_TOOLS = [
    {
        "name": "gymsite_listar_relatorios",
        "description": "Lista todos os relatórios de mercado disponíveis no GymSite. Retorna ID, município, estado, status e data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "municipio": {"type": "string", "description": "Filtrar por nome do município (opcional)"},
                "estado": {"type": "string", "description": "Filtrar por UF (opcional)"},
                "limit": {"type": "integer", "description": "Limite de resultados (default: 20)", "default": 20}
            }
        }
    },
    {
        "name": "gymsite_buscar_relatorio",
        "description": "Busca detalhes completos de um relatório de mercado pelo ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relatorio_id": {"type": "string", "description": "UUID do relatório"}
            },
            "required": ["relatorio_id"]
        }
    },
    {
        "name": "gymsite_mapa_mercado",
        "description": "Retorna dados do mapa municipal: bounds, concorrentes, entrantes e heatmap para um relatório.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relatorio_id": {"type": "string", "description": "UUID do relatório"}
            },
            "required": ["relatorio_id"]
        }
    },
    {
        "name": "gymsite_listar_oportunidades",
        "description": "Lista oportunidades de prospecção identificadas pelo GymSite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "municipio": {"type": "string", "description": "Filtrar por município (opcional)"},
                "status": {"type": "string", "description": "Filtrar por status: pendente, em_andamento, concluido (opcional)"},
                "limit": {"type": "integer", "description": "Limite de resultados (default: 20)", "default": 20}
            }
        }
    },
    {
        "name": "gymsite_executar_prospeccao",
        "description": "Executa uma prospecção de mercado em um município específico. Pode demorar alguns minutos.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "municipio": {"type": "string", "description": "Nome do município"},
                "estado": {"type": "string", "description": "UF do estado"},
                "segmento": {"type": "string", "description": "Segmento de mercado (ex: Logística de Cargas, Transporte Container)", "default": "Logística de Cargas"}
            },
            "required": ["municipio", "estado"]
        }
    },
    {
        "name": "gymsite_buscar_cnpj",
        "description": "Busca dados enriquecidos de um CNPJ (QSA, sócios, endereço, atividade principal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cnpj": {"type": "string", "description": "CNPJ com ou sem formatação"}
            },
            "required": ["cnpj"]
        }
    },
    {
        "name": "gymsite_geocodificar",
        "description": "Converte um endereço ou nome de cidade em coordenadas geográficas (lat, lng).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "endereco": {"type": "string", "description": "Endereço completo ou nome da cidade"}
            },
            "required": ["endereco"]
        }
    }
]


# ─── Tool Handlers ──────────────────────────────────────────────────────────

async def _gymsite_get(path: str, params: dict | None = None) -> dict:
    """Chama a API interna do GymSite."""
    async with httpx.AsyncClient() as client:
        headers = {}
        if GYMSITE_API_KEY:
            headers["Authorization"] = f"Bearer {GYMSITE_API_KEY}"
        resp = await client.get(f"{GYMSITE_API_BASE}{path}", params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()


async def _gymsite_post(path: str, json_body: dict | None = None) -> dict:
    """POST para a API interna do GymSite."""
    async with httpx.AsyncClient() as client:
        headers = {}
        if GYMSITE_API_KEY:
            headers["Authorization"] = f"Bearer {GYMSITE_API_KEY}"
        resp = await client.post(f"{GYMSITE_API_BASE}{path}", json=json_body, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()


async def handle_listar_relatorios(args: dict) -> list:
    params = {}
    if args.get("municipio"):
        params["municipio"] = args["municipio"]
    if args.get("estado"):
        params["estado"] = args["estado"]
    params["limit"] = args.get("limit", 20)
    data = await _gymsite_get("/api/relatorios", params)
    if isinstance(data, dict):
        return data.get("items", data)
    return data


async def handle_buscar_relatorio(args: dict) -> dict:
    rid = args["relatorio_id"]
    return await _gymsite_get(f"/api/relatorios/{rid}")


async def handle_mapa_mercado(args: dict) -> dict:
    rid = args["relatorio_id"]
    return await _gymsite_get(f"/api/relatorios/{rid}/mapa-mercado")


async def handle_listar_oportunidades(args: dict) -> list:
    params = {}
    if args.get("municipio"):
        params["municipio"] = args["municipio"]
    if args.get("status"):
        params["status"] = args["status"]
    params["limit"] = args.get("limit", 20)
    data = await _gymsite_get("/api/prospeccao/oportunidades", params)
    if isinstance(data, dict):
        return data.get("items", data)
    return data


async def handle_executar_prospeccao(args: dict) -> dict:
    body = {
        "municipio": args["municipio"],
        "estado": args["estado"],
        "segmento": args.get("segmento", "Logística de Cargas")
    }
    return await _gymsite_post("/api/prospeccao/executar", body)


async def handle_buscar_cnpj(args: dict) -> dict:
    cnpj = args["cnpj"].replace(".", "").replace("/", "").replace("-", "").replace(" ", "")
    return await _gymsite_get(f"/api/canais/cnpj", {"cnpj": cnpj})


def _parse_endereco_cidade_uf(endereco: str) -> tuple[str, str]:
    raw = (endereco or "").strip()
    if not raw:
        return "", ""
    if "," not in raw:
        return raw, ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) >= 2 and len(parts[-1]) <= 3:
        return ", ".join(parts[:-1]), parts[-1].upper()
    return raw, ""


async def handle_geocodificar(args: dict) -> dict:
    cidade, uf = _parse_endereco_cidade_uf(args["endereco"])
    params: dict[str, str] = {"cidade": cidade}
    if uf:
        params["uf"] = uf
    return await _gymsite_get("/api/geocode/cidade", params)


TOOL_ROUTER = {
    "gymsite_listar_relatorios": handle_listar_relatorios,
    "gymsite_buscar_relatorio": handle_buscar_relatorio,
    "gymsite_mapa_mercado": handle_mapa_mercado,
    "gymsite_listar_oportunidades": handle_listar_oportunidades,
    "gymsite_executar_prospeccao": handle_executar_prospeccao,
    "gymsite_buscar_cnpj": handle_buscar_cnpj,
    "gymsite_geocodificar": handle_geocodificar,
    **MERCADO_HANDLERS,
    **REVIEWS_HANDLERS,
    **SOCIAL_HANDLERS,
    **LISTINGS_HANDLERS,
}

MCP_TOOLS.extend(MERCADO_TOOLS)
MCP_TOOLS.extend(REVIEWS_TOOLS)
MCP_TOOLS.extend(SOCIAL_TOOLS)
MCP_TOOLS.extend(LISTINGS_TOOLS)


# ─── FastAPI App ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[GymSite MCP] v{SERVER_VERSION} iniciado")
    print(f"[GymSite MCP] Conectado ao GymSite: {GYMSITE_API_BASE}")
    yield
    print("[GymSite MCP] Encerrado")


app = FastAPI(title="GymSite MCP Server", lifespan=lifespan)


@app.get("/mcp")
async def mcp_get_no_sse():
    """Streamable HTTP: servidor stateless sem SSE — 405 spec-compliant."""
    return Response(status_code=405)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Endpoint principal MCP — JSON-RPC over HTTP."""
    body = await request.json()
    req_id = body.get("id", None)
    method = body.get("method", "")
    params = body.get("params", {})

    # ── Initialize ────────────────────────────────────────────────────────
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
            }
        })

    # ── tools/list ────────────────────────────────────────────────────────
    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS}
        })

    # ── tools/call ────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        handler = TOOL_ROUTER.get(tool_name)
        if not handler:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' não encontrada"}
            }, status_code=404)

        try:
            result = await handler(tool_args)
            if any(tool_name.startswith(p) for p in _SEGMENT_TOOL_PREFIXES):
                text = segment_tool_text(result)
            else:
                text = json.dumps(result, ensure_ascii=False, indent=2)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": text}]
                }
            })
        except httpx.HTTPStatusError as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Erro na API GymSite: {e.response.status_code} — {e.response.text[:200]}"}
            }, status_code=500)
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Erro interno: {str(e)}"}
            }, status_code=500)

    # ── notifications/initialized ─────────────────────────────────────────
    if method == "notifications/initialized":
        return Response(status_code=202)

    # ── Método desconhecido ───────────────────────────────────────────────
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Método '{method}' não suportado"}
    }, status_code=404)


@app.get("/health")
async def health():
    """Health check para o VectraClaw validar conexão."""
    return {"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION}


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
