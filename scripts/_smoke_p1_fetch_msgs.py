import os
from supabase import create_client

from tools.db_schema import tbl

ids = [
    "5ae1539e-d6a2-44df-965f-c6b7c5b4c307",
    "9d3886c5-0b5a-4b1d-9d08-7a4809a7e50c",
    "3ae28e7b-a114-4810-ac98-8f7f3a3c7df5",
    "9b65af9d-e230-4958-ab51-3cecbc286695",
    "b640ddb3-079c-4014-84ba-1ecb1c2d3372",
    "20cbdbdf-7b7b-4c5f-b372-111806c3be7f",
    "68117034-9f49-4ff0-a07b-fc58e2c5b904",
    "97cd9abd-b54e-4b95-b150-d3c00d5cbc2b",
    "25577ce8-0f60-481f-9679-dc67b756f783",
    "f2712bc6-8537-4342-898c-3f0420fecfd7",
]
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
for pid in ids:
    proj = (
        tbl(sb, "user_projects")
        .select("id,user_id")
        .eq("id", pid)
        .maybe_single()
        .execute()
        .data
        or {}
    )
    msgs = (
        tbl(sb, "project_messages")
        .select("role,agente,content,created_at")
        .eq("projeto_id", pid)
        .order("created_at")
        .execute()
        .data
        or []
    )
    print(f"== {pid} user={proj.get('user_id')} ==")
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        txt = (m.get("content") or "").replace("\n", " ")[:500]
        print(f"  [{m.get('agente')}] {txt}")
    print()
