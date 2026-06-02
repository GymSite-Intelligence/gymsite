# Golden Case: fortaleza_aldeota_20260601

## Identificação
- **UUID:** `daa39e58-cc5a-4353-a021-146d29b8a13f`
- **ADK Run ID:** `rpt_1780341163`
- **Data Criação:** 2026-06-01T18:55:40.096336+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Fortaleza
- **Bairro:** Aldeota
- **UF:** CE
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO
- **Score Top1:** 9.0
- **Score Bairro:** 9.0
- **Modelo Recomendado:** Premium
- **Saturação:** *(vazio no DB — ver curadoria)*
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 0
- **Entrantes CNPJ 90d (Fortaleza):** 47

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao` ⚠️ *vazio no output atual — tratar no eval ou corrigir pipeline antes de aprovar este campo*

## Campos com Tolerância
- `score_top1_candidato`: ±0,5 ponto absoluto (ver `expected_output.json`)
- `aluguel_mensal`: ±10%

## Notas do Curador

### Revisão (curadoria)

- **Referência positiva do dataset**: único **APROVADO puro** com **score 9.0** — caso para validar pipeline “funcionando bem” em bairro nobre (renda DR ~R$ 10.572).
- **Scores regionais (bate com o output)**:
  - Demográfico **8.0**, Viabilidade **10.0**, Competitivo **`null`** → Score Bairro **9.0** = \((8.0 + 10.0) / 2\) — **média só das dimensões disponíveis** (sem concorrência georreferenciada).
  - Score Top1 **9.0** = Score Bairro (sem delta GeoScout relevante; top candidato genérico score_geoscout **6**).
- **Gap de coleta Maps**: `total_concorrentes_analisados = 0`, `competidores_count = 0`, `rating_medio = 0` — **não** significa ausência de mercado (DR cita Smart Fit, Selfit, Greenlife); significa **falha/lacuna de persistência ou busca no raio** nesta execução.
- **`nivel_saturacao` vazio**: campo crítico sem valor — **bloqueia** aprovação plena de “Campos críticos” até fix de A6/persistência ou exceção explícita no eval.
- **`candidatos_count = 0`** vs. markdown “10 candidatos avaliados” — mesma tensão Anápolis/Parangaba (DB vs. narrativa A6).
- **Ticket DR “R$ 1.600–4.000”** parece **pacote anual / faixa errada**, não mensalidade vitrine — **não** usar no eval; preferir benchmark manual abaixo.
- **Modelo Premium**: coerente com Aldeota (renda alta, posicionamento aspiracional), mesmo com redes low-cost presentes na região.

### Benchmark de mensalidades (Aldeota) — curadoria manual

Referência para validar **Premium** vs. mercado real. **3/5 unidades** com preço público; Greenlife/Bodytech exigem consulta. Coleta 01/06/2026.

**Regras:** preço estrutural pós-promo; Premium = faixa **> R$ 159,90** (acima Black Smart Fit) ou clubes full-service.

| # | Rede / unidade | Plano referência | Mensalidade | Fonte |
|---|----------------|------------------|-------------|-------|
| 1 | **Smart Fit Santos Dumont** (Aldeota) | Fit / Smart / Black | **139,90** / **159,90** / **159,90** | [smartfit.com.br — Santos Dumont](https://www.smartfit.com.br/academias/santos-dumont) |
| 2 | **Smart Fit Barbosa de Freitas** (Aldeota) | Fit / Smart / Black | **129,90** / **149,90** / **159,90** | [smartfit.com.br — Barbosa de Freitas](https://www.smartfit.com.br/academias/barbosa-de-freitas) |
| 3 | **Bodytech Iguatemi Bosque** | Consulta comercial *(premium)* | Student Plan ref. **~R$ 213+** (12–25a, anual) | [btstudentplan.com.br](https://www.btstudentplan.com.br/) · [Bodytech Iguatemi](https://www.iguatemibosque.com.br/loja/bodytech/) |
| 4 | **Greenlife Family Club Aldeota** | Sob consulta (Esmeralda anual) | *Sem tabela pública* | [greenlifeacademias.com.br — Aldeota](https://greenlifeacademias.com.br/unidade/greenlife-aldeota/) |
| 5 | *(pendente)* | — | — | — |

**Leitura Premium vs. relatório:**

- **Low-cost na Aldeota** ainda existe (**129,90–159,90** Smart Fit) — mercado **segmentado**, não monolítico premium.
- **Premium operacional** na prática = **Bodytech / Greenlife club** (mensalidade tipicamente **> R$ 200–400+** estimado; confirmar com unidade).
- Ticket mensal **R$ 250–400+** para nova academia premium em Aldeota é **defensável** vs. Smart Black (159,90) + serviços (personal, modalidades, club).
- **Não** comparar com DR R$ 1.600–4.000 sem normalizar periodicidade.

### Decisão de ground truth (provisória)

- Manter como referência **APROVADO + score alto + Premium** para eval de veredito/score positivo.
- **Não** usar como referência de concorrência/saturation até `competidores_count` e `nivel_saturacao` estarem populados.
- Após fix de pipeline, re-curar benchmark (completar Greenlife + Selfit Aldeota se houver).

## Aprovação
- [x] Veredito correto
- [x] Score dentro da faixa esperada
- [x] Modelo recomendado faz sentido
- [ ] Campos críticos validados *(bloqueado: `nivel_saturacao` vazio; concorrentes=0)*
- [x] Notas do curador preenchidas

*Curadoria 01/06/2026 — parcialmente aprovado; completar após fix saturação/concorrentes ou exceção no eval.*
