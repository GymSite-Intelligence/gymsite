# Plano de Enriquecimento de Dados do Relatório

> Transforma dados JÁ no banco (CNO nacional, parque CNPJ, market warehouse) em
> **sinal de relatório**, sem depender da inversão registro-primeiro (gated em
> IPTU/CKAN). Fecha os Apêndices A–D de `MOTOR_CANDIDATOS_V2_REGISTRO_PRIMEIRO.md`.
>
> Duas camadas: **(1) metodologia** (SIPOC/PDCA/5W2H/critério+testes) e
> **(2) arquitetura de construção** (schemas, queries BQ, tools, integração).
> Regra: nenhuma fase entra sem critério de aceite + teste verde.

Relacionado: [`MOTOR_CANDIDATOS_V2_REGISTRO_PRIMEIRO.md`](./MOTOR_CANDIDATOS_V2_REGISTRO_PRIMEIRO.md) (Apêndices A–D), [`COMPILADO_FONTES_DADOS.md`](./COMPILADO_FONTES_DADOS.md) §7 (rota BQ).

---

## PARTE 1 — METODOLOGIA

### 1.0 REGRA DE OURO (governa tudo) — zero hardcode

**Todo dado e dado futuro tem mecânica de cálculo + metodologia + fonte. Nada hardcoded.**
- Parâmetro = registro `{valor, fonte, data_coleta, metodo, unidade}` em
  `tools/parametros_metodologia.py` + tabela Supabase `parametros_metodologia`
  (override recalibrável). Nunca float solto na lógica.
- Default só como **fallback rotulado** (`fonte: fallback_ACAD_2024`), nunca verdade silenciosa.
- Toda métrica declara a **cadeia de cálculo** explícita.
- Relatório expõe **fonte + confiança** por número; proxy ≠ fato.
- Hierarquia: estruturado → curadoria datada → grounding → fallback rotulado.

### 1.1 SIPOC do enriquecimento

| S (Suppliers) | I (Inputs) | P (Process) | O (Outputs) | C (Customers) |
|---|---|---|---|---|
| basedosdados BQ (CNO), parque CNPJ (Supabase), Places/A3a, IBGE | obras CNO (fitness + grande porte), competidores, demografia | batch minera → Supabase; tools leem banco e calculam sinal | demanda futura datada, anéis competitivos, vetores de obra | A7/A9/A4/A6 (relatório), módulo prospecção B2B |

Princípio: **mineração no batch (banco), cálculo no pipeline (read), zero API Google por relatório repetido.**

### 1.2 PDCA

- **Plan:** este doc (fases B → A-CNO → D → C → A-IPTU; critério+teste cada).
- **Do:** codar por fase, teste antes de marcar.
- **Check:** rodar gate de teste + smoke em 1 relatório real (Meireles/Parangaba); medir sinal novo presente e numericamente plausível.
- **Act:** ajustar fatores (unidades/m², penetração) como DADO recalibrável, não hardcode espalhado.

### 1.3 5W2H da implantação

| | |
|---|---|
| **What** | enriquecer relatório com demanda futura (CNO residencial), anéis competitivos, vetores de obra |
| **Why** | sinal único/datado (moat); corrige score competitivo distorcido (caso Wally) |
| **Who** | responsável: Marcelo (aprova) · executor: pipeline ADK + batch |
| **Where** | tools/ + agents/ + Supabase + batch BQ |
| **When** | B primeiro (reusa rota CNO/BQ); ordem na Parte 2 §2.6 |
| **How** | batch minera slice → tabela Supabase → tool lê e estima → agente injeta no relatório |
| **How much** | custo ~US$0 (BQ free tier + Supabase free); esforço por fase na Parte 2 |

---

## PARTE 2 — ARQUITETURA DE CONSTRUÇÃO

### 2.1 Fase B — Demanda Futura Datada (🟥 BLOQUEADA POR VINTAGE DE DADO)

> **Achado 2026-06-14:** `basedosdados.br_me_cno` é snapshot **defasado** —
> `max(data_inicio) = 2021-05`. Zero obras desde 2022. "Demanda FUTURA" (entrega
> início+30m no futuro) é **impossível** com esse dado: o filtro de entrega futura
> retorna `sem_dados` (código correto — recusa rotular obra de 2021 como futura).
> **Demanda futura datada exige CNO FRESCO** (dump vivo da Receita, mensal — o
> download que adiamos), não o snapshot do basedosdados.
> **Construído e correto** (migração + loader + tool + 7 testes); fica **dormente**
> até fonte fresca. As 42.678 obras mineradas servem como **densificação histórica
> (até 2021)** — contexto estrutural, não timing. Reframe possível: "pipeline
> imobiliário histórico" com vintage declarado.

**Objetivo (quando houver dado fresco):** obras residenciais de grande porte no raio
→ moradores futuros → leads fitness → receita em T+24. Apêndice B.

**Modelagem do "residencial" (CNO não tem campo destinação):** proxy declarado —
`area > 2000 m²` (escala multi-unidade) + NÃO bate keyword fitness + NÃO bate
exclusão comercial óbvia (galpão, hospital, escola). Confiança SEMPRE declarada
(`confianca: baixa|media`); cobertura imperfeita = viés conservador (subestima).

**Schema** `db/migrations/*_cno_obras_grande_porte.sql`:
```
public.cno_obras_grande_porte (
  id_cno text pk, nome text, area_m2 double precision,
  cep, logradouro, numero_logradouro, bairro,
  sigla_uf, id_municipio, id_municipio_rf,
  situacao text, em_curso boolean, data_inicio date, data_situacao date,
  ni_responsavel text, fonte text default 'basedosdados.br_me_cno',
  raw jsonb, updated_at timestamptz
)  -- RLS on; índices (id_municipio_rf), (sigla_uf), (em_curso)
```

**Mineração** `tools/cno_bigquery_loader.py` (estende): query BQ `microdados`
`WHERE area > 2000 AND NOT fitness_regex AND NOT comercial_regex` → upsert.

**Cadeia de cálculo CORRIGIDA (todos os fatores via `parametros_metodologia`, zero hardcode):**
```
unidades  × ocupacao(tipologia)         = moradores
            (studio 1.5 / 1-2dorm 2.2 / 3+dorm 3.0 / default 2.8 — IBGE+tipologia do lançamento)
moradores × penetracao(perfil_bairro)   = pool_fitness_enderecavel
            (ACAD: ~4.5% geral / ~10% bairro A/B)
pool      × market_share(realista)      = captura_estimada
            (quota do raio — vem do A4/anéis de concorrência, NÃO 100%)
captura   × ticket × (1 − inadimplencia) = receita_incremental_T+24
entrega   = data_inicio + meses_entrega  (mediana 24-36; recalibrável por CNO encerradas)
```
Relatório mostra **pool potencial X / captura estimada Y** (proxy ≠ fato; nunca infla decisão).
Cada fator carrega `fonte` → exibido no relatório.

**Tool** `tools/demanda_futura_tools.py` (lê fatores de `parametros_metodologia`):
```python
def demanda_futura_datada(cidade, uf, *, bairro=None, market_share=None,
                          ticket_brl=None) -> dict
# retorna {status, n_obras, moradores_est, pool_fitness_est, captura_est,
#          receita_incremental_est, janela_entrega, fatores_usados[com fonte],
#          confianca, fonte}
```

**Refino A4-grounded — verificação cruzada com a construtora (Apêndice B, OBRIGATÓRIO):**
o proxy `área/75` é o **piso**. Quando a obra tem empreendimento/construtora nomeada
(`nome_empresarial`/`ni_responsavel`→RFB razão social), A4 faz **grounding na página
de lançamento** → `torres × unidades EXATAS` + amenidade fitness; alvará municipal
refina pavimentos. Tool `refinar_demanda_via_lancamento(obra) -> {unidades_exatas,
fonte_url, confianca}`: se achou site → usa unidades exatas (confiança **alta**) e
sobrescreve o proxy; senão mantém proxy (confiança baixa/média). Estimativa nunca
piora — só sobe de confiança quando há fonte primária do empreendimento.

**Integração:** A9 (gap "janela de entrada"), A7 (cenário ano-2), score candidato
(bônus timing). Read via Supabase (`CNO_SOURCE=supabase`), fallback vazio.

**Critério de aceite:**
1. `cno_obras_grande_porte` populada com obras **frescas** (RFB bulk, não basedosdados
   ≤2021) — ≥ 1 obra em curso recente por UF onde houver.
2. `demanda_futura_datada("Fortaleza","CE")` retorna `status=ok` com `leads_est`
   numérico e `confianca` quando há obras com entrega futura; `sem_dados` quando 0.
3. Matemática: 40.000 m² → ~530 unidades → ~1.480 moradores → ~67 leads (pen. 4,5%)
   (±5%). Trava a fórmula do Apêndice B.
4. **Verificação cruzada construtora:** quando a página de lançamento é encontrada,
   `unidades_exatas` sobrescreve o proxy e `confianca=alta` com `fonte_url`; quando
   não, mantém proxy + confiança baixa/média. Nunca piora a estimativa.

**Testes** (`tools/test_demanda_futura.py`):
- `test_estimativa_unidades_moradores_leads` — fórmula pura (sem rede). ✅
- `test_penetracao_bairro_ab` — pen. 0.10 muda leads proporcional. ✅
- `test_sem_obras_retorna_sem_dados` / `test_entrega_no_futuro_corta_zumbi` ✅
- `test_confianca_declarada` ✅
- `test_refino_lancamento_sobrescreve_proxy` (PENDENTE) — mock grounding com torres/
  unidades → usa exato sobre proxy + confiança alta; sem site → mantém proxy.

### 2.2 Fase A-CNO — Vetores de obra (quase grátis)

**Objetivo:** obra no endereço/CEP de concorrente = reforma/expansão; obra fitness
nova = concorrente abrindo antes do Maps. Usa `cno_obras_fitness` (já existe).

**Tool** `sinal_obra_concorrente(competidores: list, cidade, uf) -> list` — casa CEP/
endereço de competidor com `cno_obras_fitness` → anota `obra_em_curso=True`.

**Integração:** A2/A4 (concorrência). **Critério:** competidor com obra casada recebe
flag; teste com fixture (competidor CEP X + obra CEP X → match).

### 2.3 Fase D — Anéis competitivos (precede F2 metadados)

**Objetivo:** corrigir score (caso Wally: 40 pins, 7 de outro bairro). Apêndice D.

**Schema** (F2 §7): `aneis_competitivos`, `portes_academia` + colunas em
`competidores`: `anel` (NO_BAIRRO/FRONTEIRA/REGIONAL), `dist_borda_km`, `porte`,
`multiesporte`.

**Process (A3a):** paginação Places até 60 + grade pelo polígono (não centróide);
classifica por distância à BORDA; `type=gym`+termo aquático/luta → `multiesporte=true`
(não exclui); porte por `min_avaliacoes`. Score ponderado: NO_BAIRRO 1.0 / FRONTEIRA
0.5 / REGIONAL 0.2.

**Critério:** competidor recebe `anel` correto por distância à borda; score competitivo
do bairro ≠ score puxado pelo vizinho. **Teste:** fixture de pins em 3 distâncias →
anéis corretos + score ponderado.

### 2.4 Fase C — Leads condominial B2B (subproduto de B)

**Objetivo:** obra residencial + A4 grounding (amenidade "academia/fitness/wellness"
no lançamento) → lead de academia condominial. Apêndice C. Módulo de prospecção
vendável, não relatório de viabilidade.

**Tool** `leads_academia_condominial(cidade, uf)` — sobre `cno_obras_grande_porte` do
B + grounding página de lançamento → `oportunidades_prospeccao` (tabela já existe).

**Decisor + contato (cadeia):**
```
CNO ni_responsavel (CNPJ incorporadora)
  → RFB QSA (sócio/empresa — base própria)
  → Apollo: apollo_organizations_enrich (CNPJ/domínio → org)
            apollo_mixed_people_api_search (org + títulos compras|suprimentos|obras|
                                            engenharia|diretor) → decisor + email/tel verificado
```
RFB dá o sócio formal; **Apollo traz o decisor operacional de compra** (quem assina o
equipamento). Timing: `data_inicio + meses_entrega − janela_compra_equipamento` (3-6m,
parâmetro). **Critério:** obra com amenidade fitness vira lead com decisor Apollo +
contato + janela de abordagem datada.

### 2.5 Fase A-IPTU — Valor venal/áreas (🔒 gated em CKAN municipal)

**Bloqueio:** IPTU/Áreas Edificadas são datasets municipais (CKAN/prefeitura), fora
do BQ. Requer `discover_ckan_catalog` Fortaleza + loader IPTU. **Não inicia** até a
ingestão CKAN existir. Documentado, não construído.

### 2.6 Ordem e Definition of Done

Ordem: **B → A-CNO → D → C** (A-IPTU gated).

**DoD do plano de enriquecimento:**
1. Relatório de Fortaleza mostra bloco "Demanda futura (obras no raio)" com confiança.
2. Competidor com obra CNO recebe flag de reforma/expansão.
3. Score competitivo agrupado por anel (quando D entregue).
4. Toda fase: critério de aceite + teste verde + smoke em 1 relatório real.
5. Custo por relatório não sobe (leitura do banco; zero API extra).

---

## PARTE 3 — STATUS

| Fase | Estado |
|---|---|
| B — Demanda futura datada | 🟢 **VIVO (2026-06-14)** — CNO fresco (RFB maio/2026) no banco via `rfb_cno_loader`; demanda futura acende nacional (Fortaleza 359 obras/janela 2026-2028, SP 640, Curitiba 416…). Crosswalk RFB↔IBGE 5570 (`municipio_rf_ibge`) destravou todas as cidades. Falta só refino A4 + integração A7/A9 |
| A-CNO — vetores de obra | ⏳ **próximo** (funciona com dado histórico) |
| D — anéis competitivos | 🟢 **tool construído** — `aneis_competitivos_tools.py`: classifica NO_BAIRRO/FRONTEIRA/REGIONAL (nome + distância ao centroide), score PONDERADO (1.0/0.5/0.2), porte por avaliações, multiesporte flag. Params na regra de ouro. 8 testes (fix Wally: 1.7 vs 3 plano). **Falta wire no A6** (plumbing do centroide) |
| C — leads condominial | 🟢 **construído** — `leads_condominial_tools.py`: gatilho amenidade fitness (refino) → CNPJ incorporadora → RFB QSA + **Apollo decisor** → `oportunidades_prospeccao`. 4 testes (deps injetadas). Prioridade por janela de compra de equipamento |
| A-IPTU — valor venal | 🔒 gated (CKAN municipal) |

**Reprioritização (pós-achado vintage):** A-CNO + D primeiro (não dependem de futuro/
freshness); B/C revisitar quando fonte CNO fresca existir.

**Infra REGRA DE OURO (construída 2026-06-14):** `tools/parametros_metodologia.py` +
tabela `public.parametros_metodologia` (11 fatores com fonte/método, recalibráveis).
Zero hardcode: `demanda_futura_tools` lê tudo de `param()`.

**Fase B — metodologia construída + testada (dado dormente):**
- `db/migrations/20260614_cno_obras_grande_porte.sql` + tabela (42.678 obras, basedosdados ≤2021)
- `tools/demanda_futura_tools.py` — **cadeia corrigida** (unidades→moradores→pool→captura),
  `unidades_exatas` hook p/ refino A4, filtro entrega-futura, fatores com fonte
- `tools/test_demanda_futura.py` — **10 testes verdes** (cadeia/proxy-vs-exato/perfil/fontes)
- `cno_bigquery_loader.minerar_grande_porte`

**`rfb_cno_loader` — CONSTRUÍDO + 4 testes (parse/classify) 2026-06-14:** baixa CNO
FRESCO do RFB bulk (`dadosabertos.rfb.gov.br/CNO`, sem token), parseia nacional (reusa
`cno_fitness_tools._map_headers`), classifica fitness + grande-porte → upsert ambas
tabelas. **Execução: BR obrigatório** (host geo-bloqueia IP não-BR; GitHub Actions US
NÃO baixa — igual sandbox). Rodar da máquina BR do usuário OU Cloud Run `sa-east1`:
`python -m tools.rfb_cno_loader`. Download não testável no sandbox (geo-block); parser
validado por fixture.

**Refino A4 + gate residencial — CONSTRUÍDO 2026-06-14:** `refino_lancamento_tools.py`
(grounding Vertex → unidades exatas/tipologia/amenidade; match cep+número=alta;
só alta sobrescreve proxy) + `demanda_futura_detalhada` (por-obra, top_n refinadas,
flag `provavel_residencial`). 8+1 testes. **Lição:** proxy área é limite superior
ruidoso (infra/obra pública vazam); o refino A4 + flag residencial é o gate de confiança.
Exclusões reforçadas + 11k linhas infra limpas do banco.

**Pendente Fase B:** integração **A7/A9** no relatório (bloco "Demanda futura" usando
`demanda_futura_detalhada`, liderando pelo refinado). Refino roda nas top_n por custo.

*Criado 2026-06-14. Atualizado conforme cada fase fecha com teste verde.*
