# SPEC — RAG dos 5 agentes do site (auditoria + plano de preenchimento)

> Registrada 2026-07-08. **Atualizado 2026-08-04:** Vertex Discovery **DEPRECATED** no happy path
> dos facades `agents_site`. L2 = Eros → corpus local `docs/agente/agentes_site/rag/` → stub.
> Design: `docs/superpowers/specs/2026-08-04-rag-deterministico-llm-leitura-design.md`
> Plan: `docs/superpowers/plans/2026-08-04-rag-deterministico-llm-leitura.md`

## Mapa canônico 2026-08-04 (L2)

| Agente | Tool L2 | Eros env | Corpus glob |
|---|---|---|---|
| Mercado | `consultar_base_mercado` (+ L1 Maps/IBGE) + `consultar_share_agregadores` + `consultar_eros_wellhub` / `totalpass` / `gurupass` | `EROS_GROUP_ID_MERCADO` + `WELLHUB` / `TOTALPASS` / `GURUPASS` | `mercado_*.txt` (pode vazio) |
| Técnico | `consultar_catalogo_equipamentos` | `EROS_GROUP_ID_TECNICO` | `tecnico_*.txt` |
| Regulatório | `consultar_base_regulatoria` | `EROS_GROUP_ID_REGULATORIO` | `regulatorio_*.txt`, `mapa_uf_cref_*.txt` |
| Arquiteto | `consultar_engenharia_obra` + sanitários | `EROS_GROUP_ID_ARQUITETO` → fallback ENGENHARIA | `engenharia_*.txt` |
| Engenheiro | `consultar_engenharia_obra` | `EROS_GROUP_ID_ENGENHARIA` | `engenharia_*.txt` |

`VERTEX_RAG_ENABLED=0` em prod. Facades **não** importam `tools/discovery_engine_tools.py`.
Exceção legado: `services/consultor/consultor_engine.py` ainda pode chamar Discovery (fora degustação).

## Mapa histórico Vertex (legado — NÃO usar em facades site)

| Agente | Tool RAG | Engine | Store | Docs |
|---|---|---|---|---|
| Mercado | `consultar_base_mercado` + `buscar_concorrentes` (SearchAPI) | gymsite-market-app | gymsite-market-docs | 68 (ruidoso) |
| Técnico | `consultar_catalogo_equipamentos` | gymsite-equip-app | gymsite-equip-docs | 37 (catálogos) |
| Regulatório | `consultar_base_regulatoria` | gymsite-regulatorio-app | gymsite-regulatorio-docs | 5 |
| Arquiteto | `consultar_engenharia_obra` + `calcular_sanitarios_por_lotacao` | gymsite-obra-app | gymsite-obra-docs | 3 |
| Engenheiro | `consultar_engenharia_obra` | gymsite-obra-app | gymsite-obra-docs | 3 |

Engines existentes (todos Enterprise): market-app, equip-app, obra-app, regulatorio-app,
consultor-app, marketing-app, assitente-tecnico (dados-storage).

## Parte 1 — FEITA hoje (PR #79, aguarda deploy)
- **Bug corrigido:** Regulatório caía no `gymsite-market-app` (respondia CREF com doc de mercado).
  Agora `consultar_base_regulatoria` → `gymsite-regulatorio-app` (env `DISCOVERY_REGULATORIO_ENGINE_ID`).
- Nova `consultar_base_mercado` (→ market-app); Mercado passou a usar ela.
- **Pendente:** merge PR #79 + deploy api/worker (o ADK roda no worker; a mudança é em `agents_site/`).

## Parte 2 — FEITA 2026-07-08 (obra + regulatório ingeridos e testados)

| Store | Antes | Depois | Doc ingerido | Teste de recuperação |
|---|---|---|---|---|
| `gymsite-obra-docs` | 3 | **4** | `engenharia_normas_obra_projeto_ref.txt` | ✅ piso (15–16 mm) e carga de laje (5,0 kN/m²) |
| `gymsite-regulatorio-docs` | 5 | **6** | `regulatorio_abertura_academia_ref.txt` | ✅ 6/6 estados em transição + controle SP |
| `gymsite-market-docs` | 68 | 68 | — | **faxina pendente** (tirar não-mercado; sem Deep Research) |

Docs fonte versionados em `docs/agente/agentes_site/rag/`.
⚠ O agente Regulatório só enxerga o store novo **depois do deploy do PR #79** (hoje ainda cai no market-app).

## Parte 3 — FAXINA do market-docs (FEITA 2026-07-08)

ID real do store: `gymsite-market-docs_1782013477930` (sufixo numérico; os demais não têm).

| | Antes | Depois |
|---|---|---|
| docs | 68 | **24** |
| úteis | 4 | 24 |
| ruído CONFEF em 36 recuperações | onipresente | **0** |
| `Benchmark Financeiro de Academias` | não indexado | doc mais recuperado |

Apagados 66: 54 stubs de link do CONFEF (79–228 B, só `Nome/URL/Fonte`), 4 regulatórios
(store errado; já existiam em `regulatorio-docs`), 6 órfãos, 1 de obra (já em `obra-docs`).
Importados 24 por URI explícita de `mercado/**` + `franquias/**`. Nada se perdeu: os 5
"órfãos de path" voltaram (o bucket fora reorganizado, `podcasts/`→`mercado/`); os 2 órfãos
permanentes (IHRSA "Dummy", Sebrae) não recuperavam nada e o objeto GCS já não existia.

Deixados FORA de propósito:
- `mercado/content.pdf` — é `Dissertação Final - Fillipe Brito.docx`, 87 páginas. Tese
  acadêmica, não relatório de mercado. Indexar = agente citando TCC como verdade, sem carimbo.
- `mercado/mapa-das-franquias-capipoint-coffee-business-....json` — é sobre uma cafeteria.

## ⚠ CURADORIA DE CONTEÚDO — ABERTO (o índice está limpo; o conteúdo NÃO é confiável)

**1. Números conflitantes, sem carimbo.** Uma pergunta ("faturamento do mercado fitness
brasileiro") retorna três valores incompatíveis, nenhum com base·fonte·janela:

| Doc | Valor |
|---|---|
| `mercado_panobianco_expansao_lowcost` | R$ 15 bilhões |
| `Análise do Mercado Fitness` | 8,6 mil milhões de reais (= R$ 8,6 bi) |
| `estudo_dimensionamento_layout_ginasios` | R$ 12 mil milhões (= R$ 12 bi) |

O agente escolhe um por sorteio de ranking e apresenta como fato. É exatamente a doença da
auditoria do Cocó (`docs/produto/AUDITORIA_RELATORIO_COCO.md`), agora do nosso lado.

**2. Os docs são PT-PT.** "ginásios", "faturação", "mil milhões" (= bilhões), "a registar",
"Macroeconómico". O agente fala com dono de academia BRASILEIRO. Se ecoar "1,59 mil milhões",
o usuário não entende.

**3. `Dinâmicas e Segmentação do Mercado.txt` e `Análise do Mercado Fitness.pdf` não declaram
fonte nem data.** Trazem `62.700 estabelecimentos ativos em 2025`, `13,65 milhões de membros`,
`margem EBITDA 47,8%` — números fortes, procedência zero.

**Ação:** cabeçalho de carimbo (`FONTE · BASE · JANELA`) em cada doc de mercado, PT-BR, e
eleger UM valor de faturamento com fonte declarada. É curadoria de conteúdo, não de índice —
merece sessão própria.

## Reconciliação bucket↔índice (2026-07-09) — verificado

Auditoria do drift repo ↔ bucket GCS ↔ índice Vertex. Método: rodar a busca REAL de cada
engine (read-only) e ver o que volta, N≥3 por variância (regra 4e).

**Contaminantes purgados do índice E apagados do bucket (landmine morto):**
- `regulatorio_valores_crefs.txt` — **0/5** no índice Regulatório (incl. query da assinatura
  obsoleta `CREF13/BA-SE`). Apagado de `gs://gymsite-market-docs-…/regulatorio/`.
- `fornecedores-fitness-brasil-v2.txt` — **0/4** no índice Equip. Apagado de
  `gs://gymsite-market-docs-…/equipamentos/`.
- Apagar do bucket NÃO mexe no índice (índice é cópia importada) — serve só pra um re-import
  futuro não ressuscitar. Por isso a ordem: provar 0/N no índice → então apagar do bucket.

**AINDA ABERTO — `estudo_dimensionamento_layout_ginasios.pdf`:** está **VIVO no índice Obra
(3/3)** e aparece também no Equip — NÃO é landmine dormindo, é doc ativo. Apagar do bucket não
o tira do índice; sumir da busca exige `delete_document` no Obra. É **decisão de conteúdo**, não
faxina: tem material de layout útil, MAS é PDF (número vira math-span) e traz faturamento sem
fonte (R$ 12 bi — um dos 3 valores conflitantes). Curadoria: re-ingerir a parte de layout como
`.txt` carimbado → depois `delete_document` do PDF.

**Achados de drift (relevantes pro plano dos agentes de descoberta):**
- `gymsite-market-docs` é **gaveta de tranqueira** (72 objetos): equip + market + marketing +
  prefixos `obra/` e `regulatorio/` de outros stores.
- O engine **Regulatório indexa também `market-docs/regulatorio/`** (`registro_pj`, `lei_base`,
  `leis_funcionamento` são buscáveis de lá — **NÃO são órfãos**, não varrer o prefixo inteiro).
- O store **Equip não tem bucket próprio** (404) — importa de `market-docs/equipamentos/`.
- Repo `rag/` (12 .txt curados) ≠ buckets. Normalizar (repo=fonte, 1 bucket por store,
  ingest-no-merge) é **pré-requisito dos agentes de descoberta** (re-import tem que ser seguro),
  mas **não urgente pro usuário** (índice já limpo). Fazer junto com a construção dos agentes.

## Parte 4 — CURADORIA POR AGENTE + FAXINA DE CONTAMINAÇÃO (2026-07-09)

Erros na degustação eram **RAG contaminado**, não prompt: o agente lia doc velho que vencia o bom.

| Store | Purgado (contaminante) | Por quê |
|---|---|---|
| `gymsite-equip-docs` | `fornecedores-fitness-brasil-v2.txt` | tinha Lion Fitness/TRG/Evoque — marcas FORA do PRD de fornecedores; o Técnico respondia elas |
| `gymsite-regulatorio-docs` | `regulatorio_valores_crefs.txt` | mapeamento CREF obsoleto (CREF13/BA-SE etc.) contradizia o verificado |

| Store | Ingerido (curado) | Efeito |
|---|---|---|
| `gymsite-equip-docs` | `tecnico_fornecedores_catalogos_ref.txt` | 15 fornecedores BR do PRD + veto a orçamento + aviso padrão. Lion Fitness sumiu do top |
| `gymsite-regulatorio-docs` | `regulatorio_anuidades_processo_2026.txt` | anuidade PJ 2026 por CREF (base R$ 1.569,68, Res. CONFEF 596/2025), registro (Res. 477/2023), RT (Lei 9.696), alvará/AVCB. Resolveu o "não especifica o CREF da Paraíba" (CREF10 2/3 · anuidade 3/3) |

Correções aplicadas ao copiar o relatório: **MA=CREF21** (não CREF15); CREF23–27 OMITIDOS da anuidade
(instituídos, não recebem registro até 02/01/2027 — vão pro CREF pai). Coerente com o mapa (#80).

Lição reforçada: **curar (ingerir bom) sem purgar (tirar velho) não resolve** — o velho vence.
Após ingerir doc verificado, SEMPRE purgar o que ele substitui.

### Contexto original (mantido para histórico)

### Lacunas por agente (curador, sem métrica de perguntas — julgado por cobertura)
- **Técnico** — ✅ suficiente_pleno. Não raspar. (residual: tabela de footprint/dimensões; premium Technogym/Life Fitness).
- **Mercado** — ⚠️ suficiente_mvp mas **ruidoso**. Ação = **curar** (tirar não-mercado: política de redes sociais, cursos_e_eventos), não raspar.
- **Regulatório** — ⚠️ núcleo ok; DESCOBERTO: anuidades CREF por região, licença municipal por cidade, AVCB por estado.
- **Arquiteto** — ❌ insuficiente. DESCOBERTO: NBR 9050 acessibilidade, NBR 13532 etapas, sanitários/vestiário por lotação, pisos por zona.
- **Engenheiro** — ❌ insuficiente. DESCOBERTO: NBR 6120 laje, 16280 laudo reforma, 5410 elétrica, 16401 climatização, 10152/10151 acústica, IT-08 bombeiros/AVCB, retrofit×obra nova.

**Prioridade de ingest:** 1º obra (2 agentes cegos), 2º regulatório (regional/municipal), 3º curar market.

### Deep Research — Prompt 1 (Obra & Projeto → gymsite-obra-docs)
Ver o prompt completo na conversa (2026-07-08). Cobre: NBR 6120, 16280, 6122, 5410, 16401,
10152/10151, IT-08/AVCB, NBR 9050, NBR 13532, sanitários por lotação, retrofit×obra nova.
Regra: cada norma com número + requisito + fonte (URL); ABNT é paga → citar requisito público,
não o texto integral; variação por estado/município declarada + datada. Tabela final Tema|Norma|Requisito|Fonte.

### Deep Research — Prompt 2 (Regulatório → gymsite-regulatorio-docs)
Cobre: registro PJ no CREF, responsável técnico (Lei 9.696), anuidades por CREF regional (ano+fonte),
alvará municipal (exemplos SP/Fortaleza/Rio), vigilância sanitária, AVCB por estado, quem pode dar aula.
Regra: valor sempre com CREF regional + ano + fonte; sem valor atual → "consultar CREF regional".

### Fluxo de ingest (VALIDADO 2026-07-08 — seguir à risca)
1. Rodar o prompt no Google Deep Research. **Pegar o TEXTO, não o PDF** — o PDF renderiza
   número como math span e a camada de texto sai sem os valores ("espessura mínima entre e").
   Ingerir o PDF cru envenena o agente.
2. **Verificar o conteúdo.** Deep Research erra. Erros reais encontrados nesta rodada:
   - atribuição de fonte errada (multa atribuída à Lei 9.696, que não fixa multa);
   - parâmetro estadual apresentado como nacional (piscina/DEA de SC; AVCB de SP);
   - jurisdição em duplicidade (6 estados em dois CREFs por transição de regionais);
   - caso comum errado (piso 40–50 mm quando o padrão de mercado é 15–16 mm).
3. Escrever `.txt` limpo: número inline, carimbo (valor · base · fonte · janela), ressalva de
   procedência, e regra explícita de citação para o agente.
4. Upload no bucket → import incremental (`data_schema=content`, `INCREMENTAL`, branch 0).
   Buckets: `gymsite-obra-docs-0106729343`, `gymsite-regulatorio-docs-0106729343`.
5. **4b. TESTAR A RECUPERAÇÃO com a pergunta do usuário** (não com palavras-chave do doc).
   Verificar conteúdo ≠ verificar recuperação. Se o chunk decisivo não vier no top-4,
   reescrever o trecho como frase natural na linguagem da pergunta.
   (Caso real: tabela ASCII "Rondônia (RO) ..... CREF8 × CREF23" não era recuperada por
   "minha academia fica em Rondônia, qual CREF?".)
6. **4c. EM LISTAS DE ENTIDADES SIMILARES (estados, marcas, modalidades): repetir a entidade
   em CADA frase.** O extractive span corta o cabeçalho do parágrafo — se o trecho não se
   auto-identifica, contamina. (Caso real: pergunta sobre Tocantins retornava o parágrafo de
   Rondônia/CREF23.) Prosa limpa vira RAG ruim; redundância deliberada é o antídoto.
7. Re-testar com caso de controle (entidade FORA da lista) para garantir que não dispara
   aviso falso. (Ex.: "academia em São Paulo" não pode trazer aviso de transição.)
8. **4d. CHUNK GENÉRICO É CHAMARIZ.** Uma frase ampla no store ("registro no CREF da sua região")
   vence a linha específica ("Pernambuco → CREF12/PE") porque casa com a FORMA da pergunta genérica.
   O fato certo perde pro texto vago. **Antídoto: documento dedicado, entradas em formato
   PERGUNTA→RESPOSTA espelhando a query do usuário.** Não escreva pro leitor — escreva pro recuperador.
   (Caso real: mapa UF→CREF embutido no doc grande dava 19/27; extraído para `mapa_uf_cref_registro.txt`
   em Q&A, deu 27/27.)
9. **4e. TESTE DE RECUPERAÇÃO É ESTATÍSTICO, NÃO BINÁRIO.** O ranking do Vertex empata e desempata
   diferente entre execuções. Rodar a suíte N≥3 vezes e olhar a VARIÂNCIA, não uma amostra.
   (Caso real: duas execuções deram 19/27 cada, com conjuntos de falha DIFERENTES. Uma passada
   isolada teria declarado vitória falsa. Um "6/6 perfeito" anterior era ilusão: 6 amostras,
   1 execução, universo de 27.)
10. **4f. COBERTURA COMPLETA DO DOMÍNIO.** Testar TODAS as entidades (27 UFs), não uma amostra.
   Amostra de 6 escondeu 8 falhas.

### Restrições
- Regra de ouro: número/norma citado ao usuário vem do store; store vazio = "não sei/confirme na fonte", nunca inventar.
- **CARIMBO OBRIGATÓRIO em toda LEI/CÓDIGO/NORMA no output — vale para TODOS os agentes** que
  citem legislação da sua especialidade (Regulatório: CREF/Lei 9.696/anuidade/licença; Arquiteto:
  NBR/COE municipal; Engenheiro: NBR de obra; e qualquer outro que cite lei). Nenhuma fonte legal
  sai sem **valor · base · fonte · janela**: o número/exigência, sobre o que se aplica, de qual
  lei/artigo/órgão, e de que ano/atualização. Ex.: "7 bacias femininas · para 100 alunas · COE
  João Pessoa art. X · lei de 1971". Sem carimbo completo, não cita. Complementa a Regra de ouro
  acima: o grounding diz DE ONDE veio; o carimbo obriga a MOSTRAR ao usuário.
- **FONTE precisa + link profundo (senão sem link).** A FONTE nomeia a norma: **lei nº + ano +
  artigo** (ex.: "Lei nº 1.347/1971, art. 3.570") — nunca "art. X", nome vago ou só o órgão.
  Quando houver URL, ela abre a **norma específica** (deep-link), NUNCA o portal genérico da
  prefeitura/órgão. Sem deep-link pra norma exata → a fonte fica em **texto preciso, sem link**:
  link pra página genérica é citação falsa (parece prova, não abre a lei). Vale pra todos os
  agentes; a URL boa vem naturalmente da busca ao vivo (`pesquisar_norma_municipal`), que retorna
  o endereço da norma, não da home. **NUNCA inventar/adivinhar URL** (ex.: chutar `/norma/<nº da
  lei>` não resolve — SAPL não indexa assim): só linkar endereço que a busca RETORNOU e que se
  confirmou abrir a norma; na dúvida, texto sem link. URL chutada é o pior caso — parece prova e
  leva a lugar errado.
- LGPD/Fase 0: não ingerir dado de cliente nem material com preço público.
- Dado regional/municipal vence → re-scraping periódico + carimbo de data.

## Prompt do Curador de RAG (reuso — Template Universal)
Registrado na conversa (2026-07-08). IDENTIDADE (curador de suficiência, decide por cobertura),
CONTEXTO (5 stores), TAREFA (temas → COBERTO/PARCIAL/DESCOBERTO + ação de ingest), FORMATO (JSON).
Rodar contra cada agente quando houver métrica de perguntas por tema pra recalibrar.

## Follow-ups abertos (cross-ref)
- PR #78 (bypass anti-bot no /conversar) — aguarda merge + deploy + `SITE_CHAT_BYPASS_TOKEN` (secret já criado).
- Cap fail-closed em `_cap_chat_estourado` + `SITE_CHAT_TURNOS_PROJETO=5` — antes de prometer "5 perguntas" na UI.
- Página dos 5 agentes (gym-insight-hub) com mascotes PNG (`docs/produto/brand/icons/mascote-*.png`) + anel de cor por setor.
- Persistir `agente` por turno em `project_messages` + endpoint de feedback 👍/👎 (roda de aprendizado / SFT).
