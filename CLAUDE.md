# GymSite Intelligence

Plataforma de inteligência de mercado para academias: relatórios de viabilidade cruzando CNPJ, CNO, Google Maps e análise financeira (pipeline de agentes Google ADK A0–A9). Backend Python/FastAPI + Supabase; frontend React/Vite; **front** Cloudflare Pages (`wrangler`); **API + worker** Hetzner VPS + Cloudflare Tunnel (Cloud Run deprecado).

## Como falar com o Marcelo

Linguagem natural, menos técnica. Ele é o dono do produto, não precisa de jargão de implementação pra decidir. Ao reportar:

- **Erro:** descrever curto e em português comum o que quebrou e o efeito prático, ANTES do detalhe técnico. Ex.: "O botão de gerar de novo não funcionava porque o navegador travava antes de mandar o pedido" — não "fetchRelatorioInputsForRerun rejeita a Promise antes do POST".
- **Melhoria:** sempre dar um **exemplo de uso** de como fica melhor pra quem usa. Ex.: "Agora, se o relatório falhar no meio, o mesmo e-mail pode pedir de novo sem ficar travado" — não só "libera o entitlement no mark_failed".
- Nome de arquivo/função/erro exato pode entrar, mas depois da explicação simples, não no lugar dela.

## Fonte de verdade: `.agent/`

O cérebro do projeto vive em `.agent/` (compartilhado com Antigravity/Cursor/VS Code/Gemini). Ler sob demanda — nunca tudo de uma vez:

- `.agent/rules/processo-mudanca.md` — **regra mestra** (P-001..P-010, padrões P0–P3, banco). Ler ANTES de qualquer mudança de código/schema/UX.
- `.agent/rules/workspace.md` — governança (qualidade, naming, git).
- `.agent/AGENTS.md` — identidade do agente + mapa de skills.
- `.agent/skills/<nome>/SKILL.md` — carregar SÓ a relevante: `gymsite-backend` (FastAPI/Pydantic/Supabase), `gymsite-frontend` (React/rotas), `gymsite-pipeline` (agentes ADK/runner), `gymsite-intelligence` (CNPJ/CNO/Maps), `gymsite-reporting` (PDF/gráficos), `gymsite-prospecting` (lead-gen/webhooks), `gymsite-devops` (deploy/env), `gymsite-testing`.
- `.agent/workflows/*.md` — procedimentos salvos (prospect, report, deploy, review, debug, test, migrate, backup).

## Fontes de dados do pipeline

- **SearchAPI** (`SEARCHAPI_KEY`) — Google Maps/Search via API paga. Backend PRIMÁRIO de concorrentes (A3a, `engine=google_maps`, ~4× mais barato que Places) E de imóveis/pontos comerciais (cascata `listing_cascata.py`, bairro-scoped). Preferir sempre sobre scraping. **Aluguel viabilidade = MRLR** (`tools/aluguel_mrlr.py`), não SearchAPI. **Regra canônica:** `.agent/rules/conferencia-fontes-pipeline.md` + `.agent/rules/pipeline-fontes-deterministicas.md` + `docs/arquitetura/PIPELINE_AGENTES.md` §7–§9 — revisitar antes de mudar pipeline.
- **MRLR determinístico** (`aluguel_mrlr.py`) — fonte do ALUGUEL na viabilidade (A4 Tier 0), sobre espelhos BQ. O aluguel NÃO vem de listing raspado.
- **Playwright** (`imobiliaria_scraper.py`, OLX/ImovelWeb) — legado, FORA do caminho crítico (flag `LISTINGS_PLAYWRIGHT`, default off): era o gargalo que estourava o pipeline (timeouts 45s + Cloudflare). A cascata SearchAPI o substitui.
- **Eros** (`knowledge-ask` / grupos `EROS_GROUP_ID_*`) + corpus local — RAG qualitativo dos agentes (mercado/regulatório/engenharia/técnico). **Vertex Discovery = legado OFF** (`VERTEX_RAG_ENABLED=0`); LLM do pipeline também NÃO usa Vertex (`GOOGLE_GENAI_USE_VERTEXAI=false`, `PIPELINE_LLM_PROVIDER=nvidia`). Ver `docs/handoffs/2026-08-04-vertex-off-eros-rag-parallel.md`.

## Regras que mais mordem

- **LER A FONTE, NUNCA ASSUMIR.** Antes de afirmar como uma biblioteca, um serviço ou o
  banco se comporta, abrir o código/schema/API e verificar. Vale pro `.venv` (o fonte do
  ADK está lá), pro `git show origin/main:arquivo` (o working tree pode estar sujo ou
  atrasado), pro `list_documents` antes de apagar, pro schema real antes da migration.
  Casos em que assumir teria quebrado produção:
  - ADK: fixar um sub-agente no `Runner` não basta — ele mantém `parent_agent` e ganha
    `AutoFlow` com a tool `transfer_to_agent`; o especialista "fixado" saltaria pro outro.
    Só lendo `llm_agent.py:_llm_flow` dá pra ver que precisa de cópia com as DUAS flags
    de `disallow_transfer_*` e sem `sub_agents`.
  - Store `gymsite-market-docs` **não existe** com esse id — o real tem sufixo
    (`_1782013477930`). Um `delete` "óbvio" teria batido em NotFound (ou pior, no store errado).
  - `_cap_chat_estourado` fail-open parecia descuido; era decisão documentada em teste.
    Reverter sem ler o commit teria desfeito uma escolha de produto na surdina.
  Um número ou comportamento vindo de memória/intuição é hipótese, não fato. Verificar
  custa um comando; errar custa produção.
- Testes: backend SEMPRE `.venv/Scripts/python.exe -m pytest` (o `pytest` solto usa o
  Python global 3.13, sem as dependências do projeto, e quebra na importação); frontend
  `npx tsc --noEmit`. NUNCA `npm run dev`/`build` pra testar. Teste que valida correção
  roda ANTES do commit — fecha a etapa com o teste, não com o diff.
- **Teste que passa não prova que testa.** Rodar o teste novo ANTES do fix e exigir que ele
  FALHE — e por `AssertionError`, não por erro de import/plugin. `pytest.ini` precisa de
  `asyncio_mode = auto`: sem isso o pytest-asyncio roda em modo `strict` e todo
  `async def test_` sem marcador FALHA em vez de rodar (4 testes de cap ficaram vermelhos
  e invisíveis por 3 dias; o commit dizia "coberto"). Teste sobre serviço não-determinístico
  (recuperação do Eros/RAG) roda N≥3 e olha a variância — uma passada mente.
- Dinheiro em centavos (integer) no banco; datas `timestamptz` UTC.
- Comentário no código só quando registra DECISÃO ou armadilha não-óbvia (o PORQUÊ —
  ex.: "peso por anel: concorrente distante pressiona menos"); nunca comentário que
  repete o que o código já diz.
- **Todo número exibido ao usuário carrega carimbo: valor · base · fonte · janela.**
  Ex.: "60.165 hab · 105 setores (raio do centróide) · IBGE Censo 2022". Número sem
  base rotulada foi a doença encontrada em TODOS os concorrentes auditados — e em nós
  (auditoria Cocó 4b211a02). Rótulo de proxy é obrigatório (renda per capita = rend. do
  responsável ÷ moradores).
- Jinja/PDF: NUNCA usar chave de contexto com nome de método de dict (`pop`, `get`,
  `items`, `keys`, `values`) — `demografia.pop` resolve pro MÉTODO dict.pop, o repr
  vira pseudo-tag e o WeasyPrint renderiza célula vazia (bug da População no PDF).
- Git: binário pesado (`docs/produto/brand/`) NÃO entra em commit de código — push HTTPS
  estoura ("remote end hung up"). Assets de marca em commit próprio; se precisar,
  `git config http.postBuffer 524288000`.
- Git no Windows: `git worktree add` estoura MAX_PATH em `market_context/investigations/*`
  ("Filename too long") e deixa índice corrompido. Pra commitar numa branch limpa com a
  árvore suja (caso comum: frente paralela em andamento), usar plumbing sobre índice
  temporário — `read-tree origin/main` → `hash-object -w` → `update-index --cacheinfo`
  → `write-tree` → `commit-tree`. **`unset GIT_INDEX_FILE` ao terminar**: exportado, ele
  envenena todo `git` seguinte (um `git status` reportou 1276 arquivos staged que não
  existiam — quase "consertei" uma branch intacta). Conferir sempre com ambiente limpo.
- Deploy prod = **Hetzner VPS + Cloudflare Tunnel** — Cloud Run (GCP) DEPRECADO (billing off,
  503; NUNCA `gcloud run deploy`). API + worker rodam na MESMA VPS em `/opt/gymsite` via
  `docker-compose.prod.yml` (serviços `api` com `RUN_QUEUE_WORKER=0`, `worker` com `=1`,
  `redis` AOF, `cloudflared`). Sem portas 80/443 abertas — o túnel entrega o tráfego para
  `api.getgymsite.com.br` / `gymsite-api.vectracargo.com.br`. Deploy: push `main` → GHCR →
  `.github/workflows/ci-cd.yml` faz SSH pull na VPS (`docker compose pull api worker && up -d`),
  ou manual `cd /opt/gymsite && ./scripts/deploy.sh [tag]`. Container roda como `USER app`
  (uid 1000): pasta do host `./cno_data` (bind → `/data/cno`) precisa ser gravável por uid 1000
  se for rodar mineração CNO dentro do container. Canônico: `docs/PLAN_HETZNER_VPS_TUNNEL.md`
  + skill `gymsite-devops`. Projeto GCP `gen-lang-client-0662901510` ("GymSite") = ÓRFÃO, não usar.
- Front monorepo (`frontend/`): **Wrangler/Pages** projeto CF `gymsite` → `getgymsite.com.br` (`npx wrangler pages deploy ./dist` após build). Landing `gym-insight-hub` → `gymsite.com.br`. Ver P-000 §7–§8. `cloudbuild.frontend.yaml` e Actions `pages.yml` = legado/ignorar.

## Documentos vivos (ler quando o assunto aparecer)

- `docs/produto/AUDITORIA_RELATORIO_COCO.md` — auditoria de metodologia do relatório
  (fila de correções, rastreabilidade fonte→fórmula, confronto com auditores externos).
- `docs/produto/CONCORRENTE_ONDEABRIR.md` — dossiê competitivo (benchmarks, o que copiar,
  onde ganhamos).
- `agents/specs/SPEC_TENDENCIA_CNPJ_BAIRROS.md` — feature Tendência CNPJ por bairro
  (RFB determinístico, 3 anos, red flag).

Diretrizes comportamentais para reduzir erros comuns de codificação em LLM. Faça a mistura com instruções específicas do projeto conforme necessário.

**Compromisso: Essas diretrizes tendem a favorecer a cautela em vez da velocidade. Para tarefas triviais, use julgamento.**

## 1. Pense antes de programar

**Não presuma. Não esconda confusão. Exponha os trade-offs.**

Antes de implementar:

- Declare suas suposições explicitamente. Se tiver dúvidas, pergunte.

- Se existirem múltiplas interpretações, apresente-as – não escolha silenciosamente.
- Se existir uma abordagem mais simples, diga isso. Resista quando necessário.
- Se algo estiver confuso, pare. Diga o que está confuso. Pergunte.
- Quando me pedir para rodar algum comando seja especifico quando estivermos trabalhando com arquivos separados de backend e frontend.

## 2. Simplicidade em primeiro lugar

**Código mínimo que resolve o problema. Nada especulativo.**

- Nenhuma característica além do que foi pedido.

- Sem abstrações para código de uso único.
- Nenhuma "flexibilidade" ou "configurabilidade" que não tenha sido solicitada.
- Sem lidar com erros para cenários impossíveis.
- Se você escrever 200 linhas e pode ser 50, reescreva.
Pergunte a si mesmo: "Um engenheiro sênior diria que isso é complicado demais?" Se sim, simplifique.

## 3. Mudanças cirúrgicas

**Toque apenas no que for preciso. Limpe só a sua própria bagunça.**

Ao editar código existente:

- Não "melhore" código, comentários ou formatação adjacentes.
- Não refatore coisas que não estão quebradas.
- Combine com o estilo existente, mesmo que você faça de forma diferente.
- Se você notar código morto não relacionado, mencione – não delete.

Quando suas mudanças criam órfãos:

- Remova importações/variáveis/funções que SUAS alterações fizeram sem uso.
- Não remova código pré-existente a menos que seja solicitado.
O teste: Cada linha alterada deve rastrear diretamente o pedido do usuário.

## 4. Execução Orientada por Metas

**Defina critérios de sucesso. Repita até ser verificado.**

Transforme tarefas em objetivos verificáveis:

- "Adicionar validação" → "Escrever testes para entradas inválidas, depois fazê-los passar"
- "Corrigir o bug" → "Escrever um teste que o reproduza e depois fazê-lo passar"
- "Refactoring X" → "Garantir que os testes passem antes e depois"

Para tarefas em múltiplas etapas, estabeleça um plano breve:

```
1. [Passo] → verificar: [confere]
2. [Passo] → verificar: [confere]
3. [Passo] → verificar: [conferir]

```

Critérios fortes de sucesso permitem que você faça o loop de forma independente. Critérios fracos ("faça funcionar") exigem esclarecimento constante.

---

**Essas diretrizes funcionam se: menos mudanças desnecessárias nos diferenciais, menos reescritas devido a complicações excessivas e perguntas esclarecedoras vêm antes da implementação, e não após erros.**
