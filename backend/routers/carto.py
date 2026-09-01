from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from tools.carto_hex import HexCountNotFound, load_hex_table, lookup_hex_count

router = APIRouter(prefix="/api/carto", tags=["carto"])


class HexCountBody(BaseModel):
    lat: float = Field(...)
    lng: float = Field(...)


def _user_id_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        from api import _supabase_client

        sb = _supabase_client()
        user_resp = sb.auth.get_user(token)
        user = getattr(user_resp, "user", None)
        uid = getattr(user, "id", None) if user else None
        return str(uid) if uid else None
    except Exception:
        return None


def _hex_count(request: Request, lat: float, lng: float):
    if not _user_id_from_request(request):
        raise HTTPException(status_code=401, detail="login necessario")
    try:
        table = load_hex_table()
        return lookup_hex_count(lat, lng, table)
    except HexCountNotFound:
        raise HTTPException(status_code=404, detail="sem hex para este ponto") from None


@router.get("/hex-count")
def hex_count_get(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
):
    return _hex_count(request, lat, lng)


@router.post("/hex-count")
def hex_count_post(request: Request, body: HexCountBody):
    return _hex_count(request, body.lat, body.lng)
