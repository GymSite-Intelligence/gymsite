import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from services.kb_rag import buscar_kb

for pergunta in [
    "Quanto custa abrir uma franquia da Panobianco?",
    "Qual o payback tipico de uma academia franqueada?",
    "Quem e o decisor de expansao da Smart Fit?",
    "Qual a melhor pizzaria de Fortaleza?",
]:
    chunks = buscar_kb(pergunta, top_k=2)
    print(f"Q: {pergunta}")
    if not chunks:
        print("  (sem match acima do threshold)")
    for c in chunks:
        print(f"  [{c['similarity']:.2f}] {c['titulo']} :: {c['conteudo'][:90]}...")
    print()
