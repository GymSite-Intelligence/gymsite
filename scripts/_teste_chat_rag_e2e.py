import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from services.tinker_context import build_contexto_chat
from services.tinker_bot import chat_async

PERGUNTA = "Quero abrir uma academia qual é a melhor franquia?"

contexto = build_contexto_chat(user_id="00000000-0000-0000-0000-000000000000", pergunta=PERGUNTA)
print(f"[contexto: {len(contexto)} chars | tem bloco KB: {'BASE DE CONHECIMENTO' in contexto}]")
print()
resposta = asyncio.run(chat_async(contexto, max_tokens=900, temperature=0.4))
print(resposta)
