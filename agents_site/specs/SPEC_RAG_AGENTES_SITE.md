# SPEC — RAG dos 5 agentes do site (auditoria + plano de preenchimento)

> Registrada 2026-07-08. Auditoria dos data stores que aterram os 5 agentes de degustação
> (`agents_site/agent.py`), lacunas de material por especialidade, e plano de Deep Research
> pra tapar os buracos. **Parte 1 (wiring) FEITA hoje; Parte 2 (ingest) = amanhã.**

## Mapa: agente → tool RAG → engine/store (estado após o fix de hoje)

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
