#!/usr/bin/env python3
"""
Smoke Test Real: Executa o pipeline de enrichment com dados reais e mede performance.
Uso: python scripts/enrichment/smoke_test_real.py --cidade Fortaleza --bairro Meireles --uf CE
"""
from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

# Garante que o root do projeto esteja no path
ROOT_DIR = Path(__file__).resolve().parents[2] # Ajuste se necessário (geralmente parents[2] para scripts/enrichment)
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Imports dos seus módulos locais
from scripts.enrichment.cache_enrichment import build_cache
from scripts.enrichment.prompt_compressor import compress_from_cache
from tools._genai_client import build_genai_client
from tools.pricing import compute_cost_brl

def run_smoke_test(
    cidade: str,
    bairro: str,
    uf: str,
    model: str = "gemini-3.6-flash",
    *,
    use_bundle: bool = False,
):
    print(f"[smoke] {cidade}/{bairro} - {uf}  modelo={model}  bundle={use_bundle}")

    t_start = time.perf_counter()
    t_cache_start = time.perf_counter()

    if use_bundle:
        print("[1/3] market_bundle (OSM+portais+IBGE+bairro piloto)...")
        try:
            from scripts.batch.build_market_bundles import build_bundle
            from tools.market_bundle import compress_bundle_for_llm, save_market_bundle

            bundle = build_bundle(cidade, bairro, uf, skip_ckan=True)
            save_market_bundle(cidade, bairro, uf, bundle)
            cache_data = bundle
            prompt_text = compress_bundle_for_llm(bundle)
            t_cache_end = time.perf_counter()
            print(f"   OK bundle em {t_cache_end - t_cache_start:.2f}s")
            print(f"   missing_fields: {bundle.get('missing_fields')}")
            rb = (bundle.get('demografia') or {}).get('bairro') or {}
            print(f"   renda_bairro: {rb.get('renda_media')} fonte={rb.get('fonte')}")
        except Exception as e:
            print(f"   ERRO bundle: {e}")
            return
    else:
        print("[1/3] cache deterministico (OSM + Aluguel + BCB)...")
        try:
            cache_data = build_cache(cidade, bairro, uf)
            t_cache_end = time.perf_counter()
            print(f"   OK cache em {t_cache_end - t_cache_start:.2f}s")
            print(f"   concorrentes: {cache_data.get('competicao_local', {}).get('total_unidades_osm', 0)}")
        except Exception as e:
            print(f"   ERRO cache: {e}")
            return

        print("[2/3] Comprimindo contexto...")
        try:
            prompt_text = compress_from_cache(cache_data)
            print(f"   OK prompt ({len(prompt_text)} chars)")
        except Exception as e:
            print(f"   ERRO compress: {e}")
            return

    if use_bundle:
        print(f"[2/3] Prompt bundle ({len(prompt_text)} chars)")

    print("[3/3] LLM...")
    client = build_genai_client()
    
    # Instrução estruturada para garantir resposta útil
    instruction = (
        "Você é um analista sênior de expansão de academias. \n"
        "Analise o CONTEXTO DE MERCADO LOCAL fornecido abaixo e responda APENAS com os 4 tópicos seguintes:\n\n"
        "1. **Viabilidade:** [ALTA/MÉDIA/BAIXA] - Justifique em 1 frase baseada na saturação e aluguel.\n"
        "2. **Concorrência:** Cite o número de unidades e as redes principais. O mercado está saturado?\n"
        "3. **Aluguel:** A mediana encontrada é competitiva para o modelo Low-Cost ou Premium?\n"
        "4. **Recomendação:** Uma ação comercial clara.\n\n"
        "NÃO invente dados. Se uma informação não estiver no contexto, diga 'Dado não disponível'.\n\n"
        "--- CONTEXTO ---\n"
    )
    
    full_prompt = instruction + prompt_text
    
    t_llm_start = time.perf_counter()
    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt
        )
        t_llm_end = time.perf_counter()
        
        # Extrair métricas de uso
        usage_metadata = response.usage_metadata
        tokens_in = usage_metadata.prompt_token_count
        tokens_out = usage_metadata.candidates_token_count
        
        # Calcular custo real via sua ferramenta de pricing
        cost_brl = compute_cost_brl(model, tokens_in, tokens_out)
        
        llm_text = response.text
        print(f"   ✅ Resposta recebida em {t_llm_end - t_llm_start:.2f}s")
        print(f"   💰 Custo LLM: R$ {cost_brl:.6f}")
        print(f"   🔢 Tokens: In={tokens_in}, Out={tokens_out}")
        
    except Exception as e:
        print(f"   ❌ Erro na chamada LLM: {e}")
        return

    t_total = time.perf_counter() - t_start
    
    # 4. Consolidar Métricas para ROI Validator
    metrics = {
        "report_id": f"smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "localizacao": f"{cidade}/{bairro}",
        "status": "done",
        "tempo_execucao_segundos": round(t_total, 3),
        "tempo_cache_segundos": round(t_cache_end - t_cache_start, 3),
        "tempo_llm_segundos": round(t_llm_end - t_llm_start, 3),
        "tokens_in_total": tokens_in,
        "tokens_out_total": tokens_out,
        "custo_total_brl": round(cost_brl, 6),
        "resumo_resposta": llm_text[:200] + "..." if llm_text else ""
    }
    
    # Salvar em arquivo para usar no validator
    output_path = Path("scripts/enrichment/production_run_metrics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    
    print("\n" + "="*50)
    print("📝 RESPOSTA COMPLETA DO LLM")
    print("="*50)
    print(llm_text)
    
    print("\n" + "="*50)
    print("📊 RESULTADOS DO SMOKE TEST")
    print("="*50)
    print(f"Tempo Total:     {metrics['tempo_execucao_segundos']}s")
    print(f"Custo Total:     R$ {metrics['custo_total_brl']}")
    print(f"Tokens Input:    {metrics['tokens_in_total']}")
    print(f"Métricas salvas em: {output_path}")
    print("="*50)
    print("\n✅ Pronto para rodar o validador:")
    print(f"python scripts/enrichment/roi_validator.py --tempo {metrics['tempo_execucao_segundos']} --custo {metrics['custo_total_brl']} --tokens {metrics['tokens_in_total']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke Test Real de Enrichment")
    parser.add_argument("--cidade", default="Fortaleza", help="Cidade alvo")
    parser.add_argument("--bairro", default="Meireles", help="Bairro alvo")
    parser.add_argument("--uf", default="CE", help="UF alvo")
    parser.add_argument("--model", default="gemini-3.6-flash", help="Modelo Gemini")
    parser.add_argument(
        "--use-bundle",
        action="store_true",
        help="Usa market_bundle (Fase A/B) em vez de só cache_enrichment",
    )

    args = parser.parse_args()
    run_smoke_test(
        args.cidade,
        args.bairro,
        args.uf,
        args.model,
        use_bundle=args.use_bundle,
    )
