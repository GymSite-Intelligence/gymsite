# Golden Case: curitiba_batel_20260512

## Identificação
- **UUID:** `55938a88-1a27-4f30-b375-cab8a29a4e2d`
- **ADK Run ID:** `rpt_1778585537`
- **Data Criação:** 2026-05-12T11:29:22.458064+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Curitiba
- **Bairro:** Batel
- **UF:** PR
- **Área:** 800-1200 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO COM RESSALVAS
- **Score Top1:** 6.0
- **Score Bairro:** 6.0
- **Modelo Recomendado:** Nenhum
- **Saturação:** BAIXO
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 0
- **Entrantes CNPJ 90d:** *(vazio — `entrantes_cnpj_90d: {}`)*

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao` ⚠️ *valor presente, mas derivado de fallback (Maps falhou)*

## Campos com Tolerância
- `score_top1_candidato`: ±0,5 ponto absoluto (ver `expected_output.json`)
- `aluguel_mensal`: ±10%

## Notas do Curador

### Revisão (curadoria)

- **Caso de borda superior**: score top1 **exatamente 6.0** — limiar típico entre faixas mais positivas e `INVESTIGAR MAIS` (~5.0). Útil para o eval não arredondar nem usar tolerância percentual.
- **Combo raro do dataset**: **`APROVADO COM RESSALVAS` + `modelo_recomendado = Nenhum`** — mercado regional “passa” no score macro, mas **nenhum cenário A4 fecha** como modelo recomendável.

- **Scores regionais (bate com o output)**:
  - Demográfico **10.0**, Competitivo **7.0**, Viabilidade **1.0** → Score Bairro **6.0** = \((10.0 + 7.0 + 1.0) / 3\).
  - Score Top1 **6.0** = \((10.0 + 7.0 + 1.0 + 6.0\ \text{geoscout default}) / 4\) — **sem candidato real**; `score_geoscout = 6` do placeholder “Ponto comercial identificado na região de busca”.
  - **Score bairro = score top1** porque o 4º termo (geoscout) não altera a média neste fallback.

- **Falhas de API (execução incompleta)**:
  - GeoScout: **Geocoding REQUEST_DENIED** → **0 candidatos** persistidos.
  - Google Maps concorrentes: **API Key** → **0 concorrentes** analisados.
  - `score_concorrencia = 7.0` e `nivel_saturacao = BAIXO` são **estimativa de fallback**, não Maps real — **não** usar este caso para validar saturação/concorrência georreferenciada.
  - DR lista Smart Fit, Bluefit, WePlay, Pantheon, Tonus — **mercado Batel não está vazio**; a lacuna é de coleta, não de realidade.

- **Tensão veredito vs. narrativa A6**:
  - JSON: **APROVADO COM RESSALVAS** (score 6.0).
  - Markdown “Decisão Recomendada”: **REPROVADO** (“descartar Batel”).
  - **Ground truth = JSON** para o eval; documentar divergência verbal.
  - Leitura: `viabilidade = 1.0` (não 0.0) mantém score em **6.0**; se fosse **0.0** como Camboinhas, score bairro cairia para **~5.67** — possível **veredito mais duro** com regra futura.

- **Modelo `Nenhum` — coerente com A4**:
  - Low Cost: lucro **+R$ 4.575**, margem **2,5%**, payback **270 meses** (22,5 anos).
  - Mid: **prejuízo −0,9%**; Premium: **prejuízo −41,2%**.
  - **Stress tests** (aluguel +20%, matrículas −30%, ticket −15%): **todos INVIÁVEL**.
  - Aluguel **R$ 108/m² × ~1.004 m² ≈ R$ 108.440/mês** — **58%** da receita Low Cost (teto ACAD ~15%).
  - Batel **é** bairro premium (Bodytech Crystal, Smart/Bluefit caros), mas **imóvel mata** Mid/Premium; **não** deveria sair `Premium` no modelo — **`Nenhum` está correto**.

- **Demografia vs. input**:
  - DR: perfil **idosos (60+)** predominante vs. input **25-40** — tensão de público-alvo; reforça **RESSALVAS** (validar campo antes de investir).

- **Decisão de ground truth**:
  - Referência de **borda score 6.0 + RESSALVAS + modelo Nenhum + falha Maps/GeoScout**.
  - **Não** referência de saturação BAIXA nem de concorrentes_count.
  - Par com Camboinhas: Camboinhas = viabilidade **0** → score **&lt;5**; Batel = viabilidade **1** → score **6** — par ideal para eval de sensibilidade à dimensão financeira.

### Benchmark de mensalidades (Batel / Curitiba) — curadoria manual

Referência para contrastar tickets A4 (Low **R$ 89,90**, Mid **R$ 149,90**, Premium **R$ 299,90**) vs. mercado premium do bairro. Coleta 01/06/2026.

| # | Rede / unidade | Plano referência | Mensalidade | Fonte |
|---|----------------|------------------|-------------|-------|
| 1 | **Smart Fit Batel** | Fit / Smart / Black | **149,90** / **169,90** / **159,90** | [smartfit.com.br — Batel](https://www.smartfit.com.br/academias/batel) |
| 2 | **Bluefit Batel** | A partir de | **119,90+** *(dinâmico no site)* | [bluefit.com.br — Batel](https://www.bluefit.com.br/unidade/batel) |
| 3 | **Bodytech Shopping Crystal** *(Batel)* | Consulta comercial | *Sem tabela pública*; ref. rede **~R$ 400+**; unidades premium **R$ 200–1.000+** | [bodytech.com.br — Crystal](https://bodytech.com.br/academias/shopping-crystal) |
| 4 | **Bluefit Centro** *(ref. municipal)* | Gold Pro | **139,90** | [academiabluefitcentro.com.br](https://www.academiabluefitcentro.com.br/) |
| 5 | *(pendente)* | WePlay / Pantheon (DR) | — | Pesquisa de campo |

**Leitura vs. relatório:**

- **Batel no chão** tem redes **mid/premium** (Smart Fit **mais cara** que Parangaba: Fit **149,90** vs. **119,90**).
- Ticket A4 Premium **R$ 299,90** é **defensável** vs. Smart Black, mas **não fecha** com aluguel **R$ 108/m²**.
- **Modelo Nenhum** ≠ “bairro sem premium”; = **nenhum P&L fecha** com custo imobiliário atual.
- DR “R$ 79,90 a R$ 250” é **faixa ampla**; benchmark manual ancora **~120–170** (redes) + **400+** (club).

### Regras eval (este caso)

| Sinal | Esperado no eval |
|-------|------------------|
| `score_top1 = 6.0` (±0,5) | Manter `APROVADO COM RESSALVAS` (não `APROVADO` puro) |
| `modelo_recomendado = Nenhum` | Não aceitar `Low`/`Mid`/`Premium` como recomendado |
| `competidores_count = 0` | Não exigir match em `total_concorrentes` nem validar `BAIXO` como ground truth forte |
| `candidatos_count = 0` | Regressão = inventar candidatos sem flag de ressalva |
| Markdown “REPROVADO” | Ignorar — usar `output_consolidado.veredito` |

## Aprovação
- [x] Veredito correto *(como ground truth de borda — ver tensão com markdown)*
- [x] Score dentro da faixa esperada
- [x] Modelo recomendado faz sentido
- [ ] Campos críticos validados *(bloqueado: `nivel_saturacao`/`score_concorrencia` via fallback API)*
- [x] Notas do curador preenchidas

*Curadoria 01/06/2026 — pronto para aprovação parcial; reavaliar saturação após re-run com Maps/GeoScout OK.*
