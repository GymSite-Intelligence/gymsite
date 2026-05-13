"""
Smoke test isolado de popular_times_tool.

Roda fora do ADK pra validar:
- Playwright + sync_api + asyncio.to_thread funciona em Windows Python 3.14
- Pattern aria-label "Movimento às" extrai 168 entries
- Cache 7 dias é gerado em competitor_cache/
- Análise por dia + oportunidade_horario são produzidas

Uso:
    cd C:\\Users\\marce\\gymsite_intelligence
    python -m tools._smoke_popular_times
"""
import asyncio
import json
from tools.popular_times_tool import pesquisar_horarios_pico


# Targets de validação
TARGETS = [
    {
        "nome": "Top Up CT 24h Aldeota",
        "place_id": "top_up_ct_aldeota_smoke",
        # URL que você validou via DevTools — 168 entries no DOM
        "url": "https://www.google.com/maps/place/Top+Up+CT+24h+Aldeota/@-3.7404056,-38.5159062,17z/",
    },
    {
        "nome": "Smart Fit Papicu (controle: sem dados)",
        "place_id": "smart_fit_papicu_smoke",
        "url": "https://www.google.com/maps/search/Smart+Fit+Papicu+Fortaleza/",
    },
]


async def main():
    print(f"\n{'=' * 70}")
    print(f"SMOKE TEST — popular_times_tool")
    print(f"{'=' * 70}\n")

    for t in TARGETS:
        print(f"▶  {t['nome']}")
        print(f"   URL: {t['url'][:80]}...")

        result = await pesquisar_horarios_pico(t["url"], t["place_id"])

        status = result.get("status", "?")
        cached = result.get("cached", False)
        cache_tag = " [CACHED]" if cached else ""

        print(f"   Status: {status}{cache_tag}")
        print(f"   Total pontos extraídos: {result.get('total_pontos_extraidos', 0)}")
        print(f"   Dias com dados: {len(result.get('dados_por_dia', {}))}")

        if status == "ok":
            dia_top = result.get("dia_mais_movimentado")
            if dia_top:
                print(f"   Dia mais movimentado: {dia_top['dia']} {dia_top['hora']}h ({dia_top['percentual']}%)")
            print(f"   Oportunidade: {result.get('oportunidade_horario', '')[:120]}...")
            print(f"   Resumo por dia:")
            for dia, r in result.get("resumo_por_dia", {}).items():
                print(f"     {dia:10s} pico={r['hora_pico']}h ({r['pct_pico']}%)  "
                      f"vale={r['hora_vale']}h ({r['pct_vale']}%)  perfil={r['perfil']}")

        elif status == "sem_popular_times":
            print(f"   Motivo: {result.get('motivo', '')[:120]}")

        elif status == "erro":
            print(f"   ERRO: {result.get('motivo', '')[:200]}")

        print()

    print(f"{'=' * 70}")
    print("Cache files em: competitor_cache/")
    print("Próximo passo: se Top Up retornar status=ok com 168 pontos,")
    print("integramos no A3a.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())
