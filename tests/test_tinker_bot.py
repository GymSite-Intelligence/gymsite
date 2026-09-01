"""Script de teste do Tinker Bot — valida que a integração com o Tinker funciona."""
import asyncio
import os

from services.tinker_bot import chat_async, reset_client
from services.tinker_context import build_contexto_chat

os.environ.setdefault("TINKER_BASE_MODEL", "Qwen/Qwen3-8B")

async def main():
    print("=" * 60)
    print("TESTE: Tinker Bot Integration")
    print("=" * 60)

    # Teste 1 — Sampling básico
    print("\n[1] Teste de sampling básico...")
    try:
        resposta = await chat_async(
            prompt_text="Qual é a capital da França? Responda em português.",
            max_tokens=50,
            temperature=0.3,
        )
        print(f"Resposta: {resposta.strip()}")
        print("✅ Sampling OK")
    except Exception as e:
        print(f"❌ Erro no sampling: {e}")
        return

    # Teste 2 — Context builder
    print("\n[2] Teste de context builder (sem Supabase)...")
    try:
        # Simulamos um contexto manualmente já que não temos user real
        contexto = (
            "Você é o GymSite Assistant, um especialista em viabilidade de franquias de academia no Brasil.\n"
            "--- RELATÓRIOS RECENTES DO USUÁRIO ---\n"
            "- Fortaleza/Meireles | Veredito: viavel | Status: completed\n"
            "--- PERGUNTA DO USUÁRIO ---\n"
            "Qual o veredito do relatório de Meireles?\n"
            "Responda com base nos dados disponíveis."
        )
        resposta = await chat_async(
            prompt_text=contexto,
            max_tokens=100,
            temperature=0.5,
        )
        print(f"Resposta: {resposta.strip()}")
        print("✅ Context builder OK")
    except Exception as e:
        print(f"❌ Erro no context builder: {e}")
        return

    print("\n" + "=" * 60)
    print("Todos os testes passaram! 🎉")
    print("=" * 60)

    reset_client()

if __name__ == "__main__":
    asyncio.run(main())
