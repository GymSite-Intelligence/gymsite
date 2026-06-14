import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

PERGUNTA = "Quero abrir uma academia qual é a melhor franquia?"

print("=== 1. Classificacao de intencao ===")
from services.conversational_engine import classificar_intencao

intencao, conf = classificar_intencao(PERGUNTA)
print(f"intencao: {intencao} (conf {conf})")

print()
print("=== 2. Retrieval RAG ===")
from services.kb_rag import buscar_kb

chunks = buscar_kb(PERGUNTA, top_k=4)
for c in chunks:
    print(f"[{c['similarity']:.2f}] {c['titulo']}")

print()
print("=== 3. Contexto montado (primeiros 1200 chars do bloco KB) ===")
from services.kb_rag import formatar_contexto_kb

print(formatar_contexto_kb(chunks)[:1200])
