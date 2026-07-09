# Handoff — Degustação (5 agentes), RAG e busca CNO · 2026-07-09

Sessão longa. Frentes: robustez e correção da degustação do site (chat dos 5 especialistas),
curadoria/faxina do RAG, e uma ferramenta interna de busca do CNO. Regra que atravessou o dia:
**ler a fonte antes de responder** — três vezes mudou o diagnóstico e evitou "consertar" a coisa errada.

## Degustação — 6 achados no teste + 2 correlatos

Repo do chat: `gym-insight-hub` (Cloudflare Pages, www.gymsite.com.br). Backend: `gymsite_intelligence`.

| # | Problema (visível no teste) | Causa-raiz (verificada, não suposta) | Fix | PR |
|---|---|---|---|---|
| 1 | Crachá do sidebar não seguia a passagem de bastão | rail destacava o card escolhido, não quem respondeu | rail segue `idDestaque` (último responder) | gym-insight-hub #23 |
| 2 | `**` aparecendo cru no texto | balão renderiza texto puro, sem markdown | `renderRich()` — negrito/bullets/quebras, sem lib, sem HTML cru | #23 |
| 3 | UI apertada no celular | altura fixa 62vh + rail largo | 75vh mobile + rail w-14 | #23 |
| 4 | Técnico "inventou" Lion Fitness/Precor | **RAG contaminado** — `fornecedores-fitness-brasil-v2` tinha marcas fora do PRD | purga + doc curado `tecnico_fornecedores_catalogos_ref` | gymsite #87 |
| 5 | Regulatório "a base não especifica o CREF da PB" | doc obsoleto `regulatorio_valores_crefs` vencia + chunk Pará≈Paraíba | purga + doc `regulatorio_anuidades_processo_2026` (anuidade por CREF, Res. CONFEF 596/2025) | #87 |
| 6 | Sem CTA de relatório/forms após N perguntas | CTA só via `podeGerar` (localização capturada) | card "análise gratuita" após 3 perguntas, independe de `podeGerar` | gym-insight-hub #24 |
| + | Crachá rotulava o **roteador** como especialista Mercado | banco provou `agente=GymSiteSite`; `crachaDoAgente` mapeava `degustacao`→card Mercado | `crachaDoAgente(degustacao)`→undefined (roteador é neutro) | gym-insight-hub #25 |
| + | **"Travou"** (resposta vazia, "Desculpe não consegui") | ADK encerra o `run_async` após `transfer_to_agent` SEM o sub-agente emitir o texto final | `_rodar_turno` + **retry FIXADO no alvo** se vazio pós-transfer | gymsite #88 |

### Detalhe técnico do #88 (o travou)
Logando os eventos reais do ADK: caminho feliz é `GymSiteSite → transfer → EngenheiroObra → tool → ev(texto)`.
O vazio é quando o evento de texto não vem após a transferência. Fix: `agents_site/runner.py` extrai
`_rodar_turno(agente_obj, ...)` retornando `(resposta, autor, alvo)`; se a 1ª rodada volta vazia E houve
transferência, re-roda **fixado no alvo** (cópia `_PINADOS`, sem parent/transfer) → o especialista responde
direto. Fallback final convida a reformular (não dead-end). Verificado local: roteador→EngenheiroObra 1226
chars; especialista fixo 2318 chars; suíte 25 passed.

## RAG — curadoria e a lição

- **Fornecedores (Técnico):** purgado `fornecedores-fitness-brasil-v2.txt` (Lion Fitness/TRG/Evoque, fora do
  PRD). Ingerido `tecnico_fornecedores_catalogos_ref.txt` — 15 fornecedores BR + veto a orçamento + aviso padrão.
  Também descartados 9 catálogos de fábrica chinesa (BRTW×3, Lanbo, MBH, OKPRO, XZH, Supreme, ad23e3d99a26).
- **CREF/anuidade (Regulatório):** purgado `regulatorio_valores_crefs.txt` (mapeamento obsoleto). Ingerido
  `regulatorio_anuidades_processo_2026.txt` — anuidade PJ 2026 por CREF (base R$ 1.569,68 = Res. CONFEF nº
  596/2025, NÃO fabricado), registro (Res. 477/2023), RT (Lei 9.696), alvará/AVCB. Re-teste: CREF10/PB 2/3,
  anuidade 3/3, "não especifica" 0/3.
- Correções aplicadas ao copiar o relatório: **MA=CREF21** (não CREF15); CREF23–27 OMITIDOS da anuidade
  (instituídos, não recebem registro até 02/01/2027 — vão pro CREF pai). Coerente com o mapa verificado.
- **Lição (registrada na SPEC_RAG_AGENTES_SITE.md):** curar (ingerir bom) sem purgar (tirar velho) NÃO
  resolve — o doc velho vence no ranking. Após ingerir doc verificado, SEMPRE purgar o que ele substitui.

## Ferramenta interna: busca CNO por UF+Cidade (gymsite #86)

Rota `/cno-obras` no sidebar do consultor (`gymsite_intelligence/frontend`). Read-only. Busca obras EM CURSO
do CNO (`cno_obras_grande_porte` — proxy residencial já minerado, sem custo de BigQuery) por UF + Cidade
(id IBGE via `MUNICIPIOS_BRASIL` offline) + bairro. Endpoint `GET /api/cno/obras` (exige login). Colunas:
nome, área, endereço, bairro, início, situação, CNO. Validado: João Pessoa/PB → 78 obras.

## Documento REJEITADO (não aplicar)
`docs/SYSTEM_PROMPT_AGENTE_TECNICO.md` (de sessão-nuvem isolada) propunha reescrever o Técnico hardcodando
matriz CREF + fornecedores + anuidades no prompt, e "nunca dizer que não sabe". **Regressão** — reintroduziria
o dado fabricado que tiramos do RAG e força alucinação. O prompt real do Técnico já é tool-grounded e correto.
Só a regra "sem asteriscos visíveis" prestava — virou o `renderRich()` no front (#23).

## Deploy (estado no fim do dia)
- **Front (#23/#24/#25):** Cloudflare Pages auto-deploya no merge à main do gym-insight-hub.
- **Backend api (#85 cap, #86 cno, #88 runner):** trigger buildou; api no `ffeef0d`.
- **Worker:** deployado manualmente pro `ffeef0d` (roda o `runner.py` — o fix #88 do travou só vale no worker).
- **RAG (#87):** já ingerido nos stores; não depende de deploy de código.

## Pendências (próxima sessão)
- Roteador às vezes pede clarificação já dada (usuário disse "engenheiro E arquiteto", roteador perguntou
  "arquiteto ou obra?") — nuance de prompt do roteador, não bug crítico.
- Title da aba do gym-insight-hub ainda "Lovable App" → trocar pra "GymSite Intelligence".
- Faxina do `market-docs` (ruído não-mercado) — pendente de sessões anteriores.
- Mascotes: engenheiro tinha xadrez gravado; a versão limpa está no crachá/mini-página, mas o `.png` canônico
  em `docs/produto/brand/icons/` pode ter resíduo — reverificar se for usar em tamanho grande.
