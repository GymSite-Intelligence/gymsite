# Golden Case: niteroi_camboinhas_20260513

## Identificação
- **UUID:** `dc1d6ad9-4bfa-40ba-83a2-ea923e377820`
- **ADK Run ID:** `rpt_1778633462`
- **Data Criação:** 2026-05-13T00:36:02.591005+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Niterói
- **Bairro:** Camboinhas
- **UF:** RJ
- **Área:** 300-600 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** INVESTIGAR MAIS
- **Score Top1:** 4.99
- **Score Bairro:** 3.98
- **Modelo Recomendado:** Nenhum
- **Saturação:** MEDIO
- **Candidatos (DB):** 3
- **Concorrentes (DB):** 9 *(raio ~3 km — maioria em Itaipu/Piratininga)*
- **Entrantes CNPJ 90d:** *(vazio nesta execução — `entrantes_cnpj_90d: {}`)*

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao`

## Campos com Tolerância
- `score_top1_candidato`: ±0,5 ponto absoluto (ver `expected_output.json`)
- `aluguel_mensal`: ±10%

## Notas do Curador

### Revisão (curadoria)

- **Primeiro caso negativo do dataset** — essencial para o eval detectar regressão em cenários de **inviabilidade financeira** (não só concorrência fraca).
- **Caso de borda inferior perfeito**: score top1 **4.99** — logo **abaixo do limiar ~5.0** entre `INVESTIGAR MAIS` e faixas mais positivas.

- **Scores regionais (bate com o output)**:
  - Demográfico **10.0**, Competitivo **1.94**, Viabilidade **0.0** → Score Bairro **3.98** = \((10.0 + 1.94 + 0.0) / 3\).
  - Score Top1 **4.99** = \((10.0 + 1.94 + 0.0 + 8.0\ \text{geoscout}) / 4\) = **4.985** → arredonda **4.99**.
  - Markdown arredonda para **4.0** / **5.0** na narrativa; **ground truth = JSON Supabase**.

- **Tensão veredito vs. narrativa A6**:
  - `veredito` estruturado: **INVESTIGAR MAIS**.
  - Seção “Decisão Recomendada” no markdown: **REPROVADO** (“descartar Camboinhas”).
  - **Ground truth = INVESTIGAR MAIS** (campo persistido). O eval deve usar o JSON, não o texto livre do markdown.
  - Interpretação: score 4.99 ainda cai na faixa “investigar” (validar aluguel real, imóvel alternativo); narrativa verbal é mais dura — documentar como inconsistência conhecida do relatório.

- **Modelo `Nenhum` — coerente com A4**:
  - Low Cost: lucro **+R$ 5.025**, margem **6%**, payback **161 meses** — tecnicamente positivo, mas **fora de benchmark** (alerta: payback > 60m).
  - Mid Market: **prejuízo −8,1%**; Premium: **prejuízo −105%**.
  - **Stress tests** (aluguel +20%, matrículas −30%, ticket −15%): **todos INVIÁVEL** nos 3 modelos.
  - Driver principal: aluguel **R$ 75/m² × 450 m² = R$ 33.750/mês** (> 40% da receita Low Cost vs. teto ACAD ~15%).
  - `score_viabilidade = 0.0` reflete essa inviabilidade estrutural — não contradiz `modelo Nenhum`.

- **Concorrência local vs. score**:
  - **9 concorrentes** no raio; só **1 em Camboinhas** (Tio Sam — clube premium multi-modalidade).
  - **4 em Itaipu** (Body Intensity, Smart Fit, Halternativa, CTP) + **3 em Piratininga**.
  - `nivel_saturacao = MEDIO` com `score_concorrencia ≈ 1.94` — tensão conhecida (Parangaba); **não reprovar** o caso só por isso.
  - DR citou SM Fitness, Pulse, XFusion — **redes fantasma** (sem unidade no raio 5 km); `cobertura_redes_a0` confirma só **Smart Fit + Body Intensity**.

- **Demografia vs. financeiro**:
  - Demo **10/10** (público classe média-alta, faixa etária madura) **não salva** o bairro quando viabilidade = 0.
  - Caso ideal para eval: **regressão = veredito positivo indevido** ou **modelo recomendado ≠ Nenhum**.

- **Candidatos / GeoScout**:
  - `candidatos_count = 3` no DB; markdown “8 candidatos” — persistência parcial (âncoras indiretas: supermercado, concessionárias).
  - Top1 **Armazém Camboinhas** — sinal **indireto-heurístico**, não imóvel vago confirmado.

- **Decisão de ground truth**:
  - Referência de **INVESTIGAR MAIS + score ~5 + modelo Nenhum + viabilidade zero**.
  - Redirecionamento para **São Francisco** (0 concorrentes mapeados) é narrativa A6 — não entra no eval estruturado.

### Benchmark de mensalidades (Camboinhas / região oceânica) — curadoria manual

Referência para contrastar **tickets A4** (Low R$ 90, Mid R$ 150, Premium R$ 250) vs. mercado. Camboinhas tem **pouca oferta no bairro**; benchmark usa raio Itaipu/adjacente. Coleta 01/06/2026.

**Regras:** preço estrutural pós-promo; unidade fora de Camboinhas = contexto regional, não concorrente do endereço alvo.

| # | Rede / unidade | Plano referência | Mensalidade | Fonte |
|---|----------------|------------------|-------------|-------|
| 1 | **Smart Fit Niterói — Itaipu** (~5 km) | Fit / Smart / Black | **129,90** / **149,90** / **159,90** | [smartfit.com.br — Itaipu](https://www.smartfit.com.br/academias/niteroi-itaipu) |
| 2 | **Tio Sam Camboinhas** *(no bairro)* | Sob consulta | *Sem tabela pública* — clube premium (natação, artes marciais, dança) | [tiosam.com.br](http://www.tiosam.com.br/tio-sam-top-de-linha) |
| 3 | **Body Intensity — Itaipu** | Sob consulta | *Sem vitrine* — parceiro Wellhub/TotalPass | [Wellhub](https://wellhub.com/pt-br/search/partners/body-intensity-academia-itaipu/) |
| 4 | **CTP Fitness — Itaipu** | Sob consulta | *Sem preço online* | Maps / relatório A3 |
| 5 | *(pendente)* | Halternativa Itaipu ou Proquality Piratininga | — | — |

**Leitura vs. A4:**

- Mercado regional cobra **129,90–159,90** (Smart Fit) — **acima** do ticket Low Cost modelado (**R$ 90**), o que **não** salva margem se aluguel permanece R$ 75/m².
- Tio Sam é **referência premium local** (11 mil m², multi-modalidade) — reforça que Camboinhas **não é deserto fitness**, mas **nicho club**; nova academia genérica competiria com estrutura já instalada + custo imobiliário alto.
- Ticket A4 Low **R$ 90** é **conservador** vs. vitrine Smart — mesmo subindo ticket, stress tests mostram fragilidade.

### CNO — Itaipu / Piratininga (consulta manual 01/06/2026)

Fonte: `C:\Users\marce\Downloads\cno_extract\cno.csv` · município RFB **5865** (Niterói) · script `scripts/query_cno_bairros.py` · artefato `cno_itaipu_piratininga.json`.

| Bairro | Obras fitness CNO (em curso) | Obras fitness CNO (todas) | Concorrentes Maps (relatório) |
|--------|------------------------------|---------------------------|-------------------------------|
| **Itaipu** | **0** | **0** | Body Intensity, Smart Fit, Halternativa, CTP Fitness (4) |
| **Piratininga** | **0** | **0** | Proquality, AMA Fitness, Dançarte (3) |
| **Camboinhas** | **0** | **0** | Tio Sam (1) |

**Leitura para curadoria:**

- **Niterói inteiro: 0 obras fitness no CNO** (keywords padrão: academ, smart fit, bodytech, etc.) — snapshot com **1.328 obras** no município, mas nenhuma classificada como fitness.
- Concorrência na região oceânica vem de **unidades já operacionais** (A3/Maps), não de pipeline de obras registradas no CNO.
- Itaipu tem obras **imobiliárias** grandes no CNO (ex.: La Brise **5.840 m²**, Costa Bella **4.197 m²**) — sinal de **valorização/construção**, não de nova academia mapeada.
- **Não há alerta CNO de concorrência futura** equivalente ao Max Forma em Aldeota — coerente com `obras_cno_em_curso: {}` no relatório Camboinhas (e com ausência de dados, não só falha de env).

**Fix pipeline:** adicionado `3303302 → 5865` em `IBGE_TO_RFB_MUNICIPIO` — runs anteriores em Niterói caíam no fallback **1389 (Fortaleza)** se `CNO_DATA_DIR` estivesse setado.

### Regras eval (este caso)

| Sinal | Esperado no eval |
|-------|------------------|
| `score_viabilidade = 0` | Deve correlacionar com `modelo_recomendado = Nenhum` |
| `score_top1 < 5.0` | Deve manter `veredito = INVESTIGAR MAIS` (não APROVADO*) |
| Stress A4 | Pelo menos 1 cenário base inviável ou payback > 60m |
| Markdown “REPROVADO” | Ignorar — comparar só `output_consolidado.veredito` |

## Aprovação
- [x] Veredito correto
- [x] Score dentro da faixa esperada
- [x] Modelo recomendado faz sentido
- [x] Campos críticos validados
- [x] Notas do curador preenchidas

*Curadoria 01/06/2026 — pronto para aprovação final (`approved: true`) após confirmação do curador.*
