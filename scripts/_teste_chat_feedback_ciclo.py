import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from services.chat_log import registrar_interacao, registrar_feedback

UID = "00000000-0000-0000-0000-000000000000"

iid = registrar_interacao(
    user_id=UID,
    endpoint="chat",
    pergunta="[TESTE-CICLO] quanto custa franquia Panobianco?",
    resposta="A partir de R$ 950 mil (fonte: pagina oficial, 2026).",
    intencao="pergunta_simples",
    kb_fontes=[{"fonte": "web:panobianco", "similarity": 0.78}],
)
print("interacao_id:", iid)
assert iid, "insert falhou"

ok = registrar_feedback(iid, user_id=UID, rating=1, comentario="resposta boa")
print("feedback ok:", ok)
assert ok

# feedback de outro usuario deve FALHAR (guard de dono)
ok2 = registrar_feedback(iid, user_id="11111111-1111-1111-1111-111111111111", rating=-1)
print("feedback usuario errado bloqueado:", not ok2)
assert not ok2

# limpeza
from db.supabase_writer import _get_client
_get_client().table("chat_interacoes").delete().eq("id", iid).execute()
print("limpo. ciclo OK")
