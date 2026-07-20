# P-000: REGRA MESTRA DE MUDANÇA

> **ID:** P-000
> **Status:** Ativo
> **Escopo:** Todo o código-fonte, schema de banco e configuração de infraestrutura.
> **Público:** Todos os agentes de IA e engenheiros humanos.
> **Resumo operacional:** [REGRAS_USO_GLOBAL.md](REGRAS_USO_GLOBAL.md) (checklist diário; P-000 prevalece em conflito).
> **Numeração:** As tags `(P-001)`…`(P-004)` **dentro deste arquivo** são âncoras internas do P-000 (fontes, carimbo, ler-fonte). **Não** confundir com P-001…P-010 de `.agent/rules/processo-mudanca.md` (UX/schema de produto). Em conflito de IDs, cite **P-000 §N** ou o arquivo completo.

---

**ANTES DE QUALQUER MUDANÇA, VERIFIQUE ESTES 9 PONTOS.**

## 1. Minimalismo Cirúrgico

Toda alteração deve ser a **mínima necessária** para cumprir o requisito.

- **NÃO** refatore código adjacente, a menos que seja a causa raiz do problema.
- **NÃO** adicione "melhorias" ou funcionalidades especulativas que não foram pedidas.
- **NÃO** "limpe" formatação ou renomeie variáveis fora do escopo da sua tarefa.

O objetivo é ter *diffs* limpos e focados, que resolvem um problema por vez.

## 2. LER A FONTE, NUNCA ASSUMIR (P-004)

A memória ou a intuição sobre como uma API, biblioteca ou serviço funciona é uma **hipótese**, não um fato.

- **Código-fonte:** Antes de usar uma função de `tools/`, leia seu código para entender o que ela realmente faz, quais APIs externas ela chama e como trata erros.
- **Schema do Banco:** Antes de fazer uma query, verifique o schema real em `db/migrations/` para saber os nomes exatos de colunas e tabelas e suas constraints.
- **Documentação de API Externa:** Antes de chamar uma API (Google Maps, SearchAPI, Apollo), consulte a documentação para entender os parâmetros, o custo e o formato da resposta.
- **Lineage:** Nova fonte, tabela ou tool no pipeline → atualizar `docs/metodologia/data_lineage.md` no mesmo PR.

**Exemplo real que quebrou produção:** Assumir que o aluguel de viabilidade vinha de portais imobiliários, quando a fonte de verdade determinística é o `aluguel_mrlr.py`. Ler a fonte (`tools/aluguel_mrlr.py` e `tools/financial_tools.py`) teria evitado a divergência. Scraping de portais para bundle (`aluguel_portais`) foi arquivado em `tools/9_obsolete/` (jul/2026).

## 3. Fontes de Dados Têm Hierarquia (P-001)

Nem toda fonte de dados tem o mesmo peso. A hierarquia de fontes de verdade é **determinística e obrigatória**.

- **Tier 0 (Determinístico):** Cálculos e modelos internos (`aluguel_mrlr.py`, `posicionamento_renda.py`), dados de fontes oficiais (IBGE, RFB via `basedosdados_loader.py`), e parâmetros de metodologia (`parametros_metodologia.py`). **Estes dados SEMPRE têm precedência.**
- **Tier 1 (API Paga):** Dados estruturados de APIs pagas e confiáveis (SearchAPI, Google Places). Usados para preencher gaps do Tier 0.
- **Tier 2 (Busca Web Grounded):** Pesquisa qualitativa via `google_search` (A7) ou Kimi (A0). Usada para contexto e insights, **NUNCA para números financeiros ou de viabilidade**.

**Invariante:** O **aluguel de viabilidade** vem **exclusivamente** do MRLR (Tier 0). Fallbacks (T1/T2) só são usados em caso de falha do MRLR, com a flag `aluguel_deterministico=false` e alertas explícitos no relatório. O uso de Search Grounding (Tier 2) para aluguel OPEX é proibido; o fallback deve vir de benchmarks (FipeZap/ACAD). Código legado de portais: `tools/9_obsolete/` + `.agent/rules/conferencia-fontes-pipeline.md`.

### Benchmarks financeiros (calibração de `parametros_metodologia` / A4)

Quando Panorama/ACAD **não** publica % fechado (mix agregador, margem, take rate, etc.), **não inventar ponto médio** a partir de faixa qualitativa. Hierarquia de calibração:

1. **Capital aberto / CVM (preferido quando existir número auditável):** releases, demonstrações financeiras, Formulário de Referência, earnings / Investor Relations de redes listadas — ex. **Smart Fit Holdings (SMFT3)**, **Bluefit** (e pares do setor com dado público). Carimbo: valor · base (ex. unidades, alunos, receita) · documento+ano · janela.
2. **ACAD / Sebrae / IHRSA-HFA / Panorama Setorial** — defaults setoriais e penetração; usar quando CVM não cobre o KPI ou o recorte (ex. boutique independente).
3. **Calibração GymSite** — só com carimbo explícito em `parametros_metodologia` (`fonte` + `data`); nunca silent override.

**Proxy de rede listada:** número de Smart Fit/Bluefit é proxy de **low-cost em escala**, não de mid/premium boutique. Rotular no carimbo (`fonte: CVM/IR Smart Fit …`) e não extrapolar sem nota. Search Grounding **não** substitui PDF/CVM para default financeiro.

Números auditados desta janela (evidência, não regra): `docs/metodologia/cvm-smartfit-bluefit-2025.md`.

**A4 independente por modelo de negócio:** cada faixa (`low` / `mid` / `premium` / futuro `boutique` / `crossfit`) carrega o **próprio** conjunto de params (`ticket_*`, `churn_*`, `frequencia_semanal_*`, `pico_share_*`, `matr_m2_*`, …). Proibido `pico_share` (ou freq) **global/acumulado** compartilhado entre tipologias. Pico boutique/CF (quando entrarem) = `pico_share` alto **daquele** modelo (≈0,35–0,50) + `frequencia_semanal` ≥ 3,5 — não misturar com low-cost nem somar bases.

**Fora do motor financeiro (A4):** ranking/score de imóvel (`score_geoscout`, heurísticas de listing), gate de lotação NBR 9077 / IT bombeiros / cálculo reverso \(B_{\max}=L_{\text{reg}}/f\), e veredito de ponto. Metodologia de score de imóvel **não alimenta** OPEX, TIR, VPL nem veredito de viabilidade. Obra/legal = consultor / RAG municipal (`agents_site`) — **nunca** seed de `parametros_metodologia` nem input de `calcular_viabilidade_3_cenarios`.

**Carimbo regulatório por município:** qualquer número de COE, IT de bombeiros, NBR aplicada localmente, sanitários/escoamento ou alvará deve carregar `município` + `UF` (+ norma/IT citada + janela). IT-11/SP ≠ RN ≠ GO. Sem município no carimbo = não exibir como exigência.

Tabela viva: `tools/parametros_metodologia.py` + `docs/metodologia/data_lineage.md`.

## 4. Lazy Imports em `tools/`

Módulos em `tools/` são compartilhados e importados por múltiplos agentes e processos. Para evitar que uma dependência pesada ou opcional quebre o sistema inteiro, **imports devem ser feitos dentro das funções**.

```python
# ✅ BOM: Importação contida, não quebra o app se 'google.adk' não estiver instalado.
def minha_funcao_de_tool():
    from google.adk.runners import Runner # Importa SÓ quando a função é chamada
    # ...

# ❌ RUIM: Import no topo do arquivo quebra todos que importarem este módulo.
from google.adk.runners import Runner # NUNCA FAÇA ISSO EM tools/
```

## 5. Todo Número Exibido Carrega Sua Fonte (P-002)

Nenhum número pode aparecer para o usuário final sem seu carimbo de origem. Isso garante auditabilidade e transparência.

- **Formato:** `Valor · Base · Fonte · Janela de Tempo`
- **Exemplo:** "60.165 habitantes · 105 setores (raio do centróide) · IBGE Censo 2022"
- **Proxy:** Se um número é um proxy (ex: renda per capita derivada), a metodologia deve ser explícita na nota de rodapé ou na seção de metodologia do relatório.
- **Mapa operacional:** `docs/metodologia/data_lineage.md` (fonte → tabela → agente).

## 5.1 UI/Chat: Carimbos + Consistência Visual (P-002 aplicado no frontend)

Quando uma informação sai para o usuário (principalmente em chat e cards), o frontend vira parte da auditabilidade.

- **Carimbo não é opcional:** qualquer número, ranking, contagem, selo ou afirmação “determinística” precisa de carimbo exibível (ou no mínimo acessível via UI, ex.: popover).
  - **Exemplos que precisam carimbo:** “15 concorrentes”, “R$ 27.876 de aluguel”, “payback 32 meses”, “saturação ALTO”, “maioria feminina 35–59”.
  - **Exemplos de carimbo mínimo:** `valor · base · fonte · janela` + `município/UF` quando aplicável.
- **Uma fonte → uma renderização:** o mesmo dado (ex.: total de concorrentes) não pode aparecer com estruturas diferentes em páginas diferentes; isso destrói autoridade.
  - Se existir `outputs.total_concorrentes_analisados`, todos os lugares usam o mesmo campo + mesma regra de exibição.
- **Chat não pode “inventar defaults”:** se um campo vem do input (ex.: `genero_alvo`), o chat/UI deve refletir o input; inferência demográfica é outro campo (ex.: `demografia_bairro.sexo_idade`), com carimbo.

## 5.2 Mudança de design em frontend exige evidência visual (anti-“AI slop”)

Mudança de layout/estilo sem registro visual vira decisão perdida. Regras mínimas:

- **Ler a fonte do design do frontend antes de mexer em UI.**
  - Ex.: no repo `gym-insight-hub`, fonte de verdade é `docs/frontend/CLAUDE.md` (paleta, tipografia, logo, estrutura).
- **Toda mudança de design deve gerar evidência visual versionada.**
  - Preferência: artifact HTML auto-contido em `docs/frontend/artifacts/<YYYY-MM-DD>-<slug>/index.html` (ou screenshot) + link no changelog do repo.
  - Regra vale para **landing** (`gym-insight-hub`) e para o **app logado** (`frontend/` deste monorepo).

## 6. LLM Narra, Tools Calculam

Número, score e veredito **nunca** vêm do LLM. Cálculo = `parametros_metodologia` + tools/banco.
O LLM narra, classifica texto livre e organiza saída. Se o LLM conflitar com tool (ex.: resumo A6,
gaps ERRC, viabilidade A4), **a tool sobrescreve** no pós-processamento.

Prompt que pede métrica ou veredito ao modelo é defeito de produto — corrigir prompt **e** garantir
tool/override no código. Determinismo não vem de temperatura baixa.

**RAG / material delimitado:** se a informação não está no bloco recuperado, o agente deve
abster-se — não completar com conhecimento geral (consultores landing, curador).

Craft de prompt (formato JSON, Gemini contexto-último, checklist de PR): ver
`docs/metodologia/prompts/guia_prompts_pipeline.md`.

## 7. Deploy — Canônico (sem GitHub Actions)

**Não usar** `.github/workflows/pages.yml` para publicar front (billing quebrado — ignorar).
**GitHub Actions de Pages não está operante** — push em `main` **não** garante deploy. Após merge, **disparar deploy Cloudflare manualmente** (API `POST …/deployments` ou Wrangler).

| Camada | Onde sobe | Como |
|---|---|---|
| **Frontend produto** (`frontend/` deste monorepo) | **Cloudflare Pages** (projeto CF `gymsite`) | Git build Pages (`root_dir=frontend`) **ou** `cd frontend` → build → `npx wrangler pages deploy ./dist --project-name gymsite` · config: `frontend/wrangler.jsonc` |
| **Landing + degustação** | **Cloudflare Pages** (projeto CF `gym-insight-hub`, repo separado) | push/`merge` `main` no repo hub **+** redeploy CF (Actions morto) · rota canônica `/degustacao` |
| **Backend API** (`api.py`, agents, tools) | **Google Cloud Run** `us-central1` | trigger Cloud Build `gymsite-api` em `main` **ou** `gcloud run deploy gymsite-api` |
| **Worker pipeline** | **Cloud Run** `gymsite-worker` | **mesma imagem** da API após rebuild — não auto-deploya; ver `CLAUDE.md` |

**Mudou `agents/` / `tools/` / `api.py` / motor financeiro / `parametros_metodologia`?** → **Cloud Run obrigatório** (código vive na imagem). Seed/`ALTER` só no Supabase **não** entrega lazy-`param`, `clear_param_cache` nem defaults novos no processo. Após rebuild `gymsite-api`, **atualizar `gymsite-worker` com a mesma imagem** (worker não auto-deploya).

Projeto GCP produção: `gen-lang-client-0106729343` (nome "Navi Vectra"). **Não** confundir com `gen-lang-client-0662901510` (`gymsite-api` órfão).

`cloudbuild.frontend.yaml` (Cloud Run para front) é **legado** — não é o caminho canônico; front do monorepo = Wrangler/Pages.

### Gotcha banco — schema `gymsite` ≠ `public` (views)

Projeto Supabase prod: `epgedaiukjippepujuzc` (`https://epgedaiukjippepujuzc.supabase.co`).

Com `GYMSITE_SCHEMA_SEP=1` (prod):

| Onde | O quê |
|---|---|
| `gymsite.<tabela>` | **Tabela real** — `CREATE` / `ALTER` / `ADD COLUMN` / upsert via `tools.db_schema.tbl()` |
| `public.<tabela>` | **View de compat** (PostgREST) — `ALTER TABLE … ADD COLUMN` **falha** (não é tabela) |

**Antes de migration:** confirmar no catálogo (`pg_class.relkind`: `r`=tabela, `v`=view). Padrão de view desatualizada: recrear `CREATE OR REPLACE VIEW public…` como em `db/migrations/20260713_user_projects_consultor_v2_columns.sql`.

**Erro real (2026-07-15):** `ALTER TABLE public.parametros_metodologia ADD COLUMN categoria` → view. Fix: `ALTER TABLE gymsite.parametros_metodologia …`.

App/writers: **sempre** `tbl(sb, "…")` — nunca assumir `public` quando a flag SEP está ON.

### Gotchas Cloudflare Pages (Vite)

1. **`VITE_*` precisa existir no build.** Com `root_dir=frontend`, env do painel CF **pode não** chegar ao subprocesso do Vite. Canônico: `build_command` grava `.env.production` (publishable key) **antes** de `npm run build`. Script: `scripts/fix-cf-pages-gymsite-build.ps1` (`-Redeploy` opcional).
2. **Publishable ≠ JWT legado.** Supabase desabilitou anon JWT (`UNAUTHORIZED_DISABLED_LEGACY_KEY`). Usar `sb_publishable_*` em preview **e** production (`VITE_SUPABASE_ANON_KEY`).
3. **Hub:** push `main` sozinho não basta. Redeploy:

```powershell
# Token: CLOUDFLARE_API_TOKEN ou oauth wrangler (~/.wrangler/config/default.toml)
# Account 361e9e1383bfa8e95e1db54e6c2a3bba — projeto gym-insight-hub
Invoke-RestMethod -Method POST `
  -Uri "https://api.cloudflare.com/client/v4/accounts/361e9e1383bfa8e95e1db54e6c2a3bba/pages/projects/gym-insight-hub/deployments" `
  -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
  -Body (@{ branch = "main" } | ConvertTo-Json)
```

Mesmo padrão para projeto `gymsite` (app logado).

## 8. Domínios — Não Confundir

| Projeto Cloudflare | Domínio | App |
|---|---|---|
| `gym-insight-hub` | `gymsite.com.br` / `www` | Landing + degustação (chat consultores, lead) |
| `gymsite` | `getgymsite.com.br` | App logado (dashboard, relatórios — **este monorepo** `frontend/`) |

Backend API: Cloud Run → custom domain `api.getgymsite.com.br` (ou URL `gymsite-api.vectracargo.com.br` até DNS finalizar). CORS e `VITE_API_BASE` devem apontar pro host API **de produção**, não pro domínio da landing.

**Erro comum:** tratar `gymsite.com.br` (marketing) como app logado, ou publicar o monorepo no projeto CF da landing.

## 9. Repositórios Git e Branches

### Repositórios (não confundir)

| Papel | GitHub | Clone local típico | CF / deploy |
|---|---|---|---|
| **App logado** (API, pipeline A0–A9, `frontend/` dashboard) | https://github.com/Marcelo-Rosas/gymsite | `gymsite_intelligence/` | CF `gymsite` → `getgymsite.com.br` · API Cloud Run |
| **Site** (landing + degustação `/degustacao`, chat 5 agentes) | https://github.com/Marcelo-Rosas/gym-insight-hub | `gym-insight-hub/` | CF `gym-insight-hub` → `gymsite.com.br` / `www` |

**Trunk:** `main` nos dois repos. PR → `main`. Sem long-lived `develop`.

**Degustação (hub, jul/2026):** rota canônica `/degustacao`. Legado `/?abrir=diagnostico-interno|chat|analise|formulario` redireciona via `beforeLoad`. Cards `/agentes` → `/degustacao?agente=`. Helper: `src/lib/degustacaoUrls.ts`.

### Convenção de nomes

| Prefixo | Uso |
|---|---|
| `feat/` | feature |
| `fix/` | bug |
| `docs/` | só documentação |
| `chore/` | tooling, CI, refactor sem comportamento |
| `test/` | só testes |
| `preview/` | **deploy de preview** (ver abaixo) |

### Branches de preview (CF Pages)

Preview **não** fica solto em `feat/*` antigo. Padrão:

| Padrão | Repo | Exemplo | URL preview (CF) |
|---|---|---|---|
| `preview/site-{secao}` | gym-insight-hub | `preview/site-agentes` | branch deploy no projeto `gym-insight-hub` |
| `preview/app-{secao}` | gymsite | `preview/app-relatorio` | branch deploy no projeto `gymsite` |
| `preview/user-{slug}` | qualquer | `preview/user-marcelo` | sandbox pessoal — **deletar** após review |

Regra: preview nasce de `main` atualizado; merge ou descarte em **≤ 14 dias**; não acumular `cursor/*` órfão.

### Higiene pós-merge

Após PR merged em `main`:

1. `git fetch --prune`
2. Se `ahead=0` vs `origin/main` → **deletar** branch remota: `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/{branch}`
3. Apagar branch local: `git branch -d {branch}`

Branches com `ahead>0` e PR fechado sem merge → revisar em 1 semana; cherry-pick ou delete.

**Squash merge:** branch pode aparecer “unmerged” no git mesmo merged — confiar no PR `MERGED` + `ahead=0`, não só `--no-merged`.

### Estado das branches (auditoria 2026-07-13; refresh pós-`/degustacao`)

Snapshot envelhece — re-rodar comando da seção “Comandos úteis” antes de delete em lote.

**gymsite** — muitas remotas só histórico (`ahead=0`) → candidatas a delete.

| Branch | Nota | Ação |
|---|---|---|
| `cursor/cloud-agent-*` | preview órfão / PR aberto | rebase, fechar ou `preview/app-*` |
| `feat/*` `fix/*` já merged (`ahead=0` ou lixo squash) | já em `main` | **delete** remota+local |

**gym-insight-hub** — `/degustacao` em `main` (`536d73c`+); CF deploy **manual** pós-push.

| Branch | Nota | Ação |
|---|---|---|
| `feat/canonical-redirect` | PR #9 merged | **delete** |
| `feat/lgpd-privacidade` | PR #27 merged | **delete** |
| `fix/title-gymsite` | PR #29 merged | **delete** |

⚠️ **Redirect legado (aberto):** PR #9 hub apontou `301 getgymsite.com.br → gymsite.com.br`. §8 define papéis **separados** (`getgymsite` = app logado; `gymsite.com.br` = landing). **Não** unificar DNS sem decisão explícita — revisar redirect CF antes de `preview/app-*`.

### Comandos úteis

```bash
# Listar branches só histórico (gymsite, no clone)
git fetch --prune && python -c "
import subprocess
for b in subprocess.check_output(['git','for-each-ref','refs/remotes/origin','--format=%(refname:short)'], text=True).split():
    if b in ('origin','origin/HEAD') or b.endswith('/main'): continue
    a=subprocess.check_output(['git','rev-list','--count','origin/main..'+b], text=True).strip()
    if a=='0': print(b.replace('origin/',''))
"

# Deletar remota (exemplo)
gh api -X DELETE repos/Marcelo-Rosas/gymsite/git/refs/heads/fix/cap-chat-fail-closed
```

---
*Este documento é a fonte canônica de governança. Em caso de conflito com outras instruções, P-000 prevalece.*

---

## 10. Catálogo de Skills e Fluxos de Trabalho

Esta seção serve como um guia central para o agente sobre como e quando utilizar o conjunto de skills disponíveis para executar tarefas de engenharia, produto, design, operações e produtividade.

### 10.1 Engenharia de Software

**`architecture`**
- **Descrição:** Cria ou avalia um registro de decisão de arquitetura (ADR).
- **Quando Usar:** Ao escolher entre tecnologias, documentar uma decisão de design com trade-offs, ou revisar uma proposta de arquitetura.
- **Exemplo de Uso:** "Devemos usar Kafka ou SQS para nosso barramento de eventos? Crie um ADR para essa decisão."

**`code-review`**
- **Descrição:** Revisa um trecho de código ou Pull Request em busca de falhas de segurança, performance, correção e manutenibilidade.
- **Quando Usar:** Ao receber um link de PR, um trecho de código para análise, ou um pedido genérico de revisão.
- **Exemplo de Uso:** "Revise este PR para possíveis problemas de segurança antes do merge."

**`debug`**
- **Descrição:** Conduz uma sessão de depuração estruturada (Reproduzir, Isolar, Diagnosticar, Corrigir) para encontrar a causa raiz de um bug.
- **Quando Usar:** Ao receber uma mensagem de erro, um stack trace, ou uma descrição de comportamento inesperado.
- **Exemplo de Uso:** "Estou recebendo um `NullPointerException` nesta função, me ajude a debugar."

**`deploy-checklist`**
- **Descrição:** Gera um checklist de verificação pré-deploy para garantir a segurança e a qualidade da entrega.
- **Quando Usar:** Antes de um deploy em produção, especialmente se envolver migrações de banco de dados ou feature flags.
- **Exemplo de Uso:** "Estamos preparando o deploy da versão 2.3. Gere um checklist de pré-deploy para nós."

**`documentation`**
- **Descrição:** Cria ou melhora documentação técnica, como READMEs, documentação de API e runbooks operacionais.
- **Quando Usar:** Quando for solicitado para documentar uma função, um serviço ou um projeto.
- **Exemplo de Uso:** "Documente este endpoint da API, incluindo exemplos de request e response."

**`incident-response`**
- **Descrição:** Guia a equipe durante um incidente, desde a triagem e classificação de severidade (SEV) até a criação de um postmortem sem culpa.
- **Quando Usar:** Quando um incidente de produção é relatado.
- **Exemplo de Uso:** "Produção está fora do ar! Inicie o protocolo de resposta a incidentes SEV1."

**`system-design`**
- **Descrição:** Desenha a arquitetura de um novo sistema ou serviço a partir de requisitos funcionais e não-funcionais.
- **Quando Usar:** Para projetar um novo microsserviço, um novo recurso complexo ou uma nova plataforma.
- **Exemplo de Uso:** "Desenhe a arquitetura para um sistema de notificações em tempo real."

**`test-and-qa`**
- **Descrição:** Gera casos de teste (unitários, integração, etc.) e planos de teste formais (QAP) para uma funcionalidade.
- **Quando Usar:** Ao desenvolver um novo recurso ou para garantir a cobertura de testes de uma área crítica.
- **Exemplo de Uso:** "Crie os casos de teste para a funcionalidade de login com dois fatores."

### 10.2 Gestão de Produto

**`brainstorm`**
- **Descrição:** Atua como um parceiro de debate (sparring partner) para explorar ideias de produto, desafiar premissas e aprofundar o raciocínio estratégico.
- **Quando Usar:** Em fases iniciais de descoberta, ao explorar um novo problema ou uma oportunidade de mercado.
- **Exemplo de Uso:** "Vamos fazer um brainstorm sobre como podemos usar IA para melhorar nosso produto."

**`competitive-brief`**
- **Descrição:** Cria um dossiê de análise competitiva, comparando produtos, posicionamento e estratégias de concorrentes.
- **Quando Usar:** Para informar a estratégia de produto, preparar materiais para investidores ou decidir onde diferenciar.
- **Exemplo de Uso:** "Crie um dossiê competitivo comparando nosso produto com o Concorrente X e Y."

**`metrics-review`**
- **Descrição:** Analisa métricas de produto, identifica tendências, gera insights e recomenda ações estratégicas.
- **Quando Usar:** Para revisões semanais, mensais ou trimestrais de métricas, ou para investigar uma queda/pico inesperado.
- **Exemplo de Uso:** "Analise as métricas de engajamento do último mês e me diga o que você encontrou."

**`roadmap-update`**
- **Descrição:** Cria, atualiza e reprioriza um roadmap de produto usando frameworks como Now/Next/Later.
- **Quando Usar:** Durante o planejamento trimestral, ao adicionar uma nova iniciativa ou quando as prioridades mudam.
- **Exemplo de Uso:** "Adicione a iniciativa 'Suporte a SSO' ao roadmap e me diga o que precisamos mover para 'Later'."

**`sprint-planning`**
- **Descrição:** Guia o planejamento de um sprint, estimando capacidade, definindo metas e priorizando o backlog.
- **Quando Usar:** No início de cada novo ciclo de desenvolvimento (sprint).
- **Exemplo de Uso:** "Vamos planejar o próximo sprint. Temos 3 engenheiros disponíveis e 2 semanas."

**`stakeholder-update`**
- **Descrição:** Redige atualizações de status de projeto, adaptando a mensagem para a audiência correta (executivos, engenheiros, clientes).
- **Quando Usar:** Para comunicação regular sobre o progresso de um projeto ou para escalar um risco.
- **Exemplo de Uso:** "Escreva um update executivo para o projeto Phoenix, que está com status Amarelo."

**`synthesize-research`**
- **Descrição:** Processa dados brutos de pesquisa (entrevistas, surveys) e os transforma em temas, insights e recomendações acionáveis.
- **Quando Usar:** Após a coleta de dados de uma pesquisa com usuários.
- **Exemplo de Uso:** "Sintetize estas 5 transcrições de entrevistas e me apresente os principais temas."

**`write-spec`**
- **Descrição:** Transforma uma ideia ou problema em um Documento de Requisitos de Produto (PRD) estruturado.
- **Quando Usar:** Quando um novo recurso é aprovado para desenvolvimento e precisa ser especificado.
- **Exemplo de Uso:** "Escreva a especificação para uma nova funcionalidade de 'exportar para CSV'."

### 10.3 Operações

**`capacity-plan`**
- **Descrição:** Analisa a carga de trabalho de uma equipe, prevê a utilização e identifica gargalos de recursos.
- **Quando Usar:** Durante o planejamento trimestral ou quando uma equipe se sente sobrecarregada.
- **Exemplo de Uso:** "Crie um plano de capacidade para a equipe de design para o Q4, considerando os projetos X e Y."

**`change-request`**
- **Descrição:** Cria uma solicitação de mudança formal (Change Request) com análise de impacto, risco e plano de rollback.
- **Quando Usar:** Ao propor uma mudança em um sistema de produção que requer aprovação formal (CAB).
- **Exemplo de Uso:** "Preciso atualizar a versão do nosso banco de dados em produção. Crie uma solicitação de mudança para isso."

**`compliance-tracking`**
- **Descrição:** Rastreia requisitos de conformidade (SOC 2, ISO 27001, etc.) e prepara a equipe para auditorias.
- **Quando Usar:** Ao se preparar para uma auditoria ou ao gerenciar o status de conformidade de um produto.
- **Exemplo de Uso:** "Gere um relatório de status de conformidade para nossa preparação para a auditoria SOC 2."

**`process-doc`**
- **Descrição:** Documenta um processo de negócio em um Procedimento Operacional Padrão (POP/SOP), incluindo matriz RACI e fluxograma.
- **Quando Usar:** Para formalizar um processo que vive no conhecimento de poucas pessoas ou para treinar novos membros da equipe.
- **Exemplo de Uso:** "Documente o nosso processo de onboarding de novos clientes."

**`process-optimization`**
- **Descrição:** Analisa um processo existente, identifica desperdícios e gargalos, e propõe um estado futuro mais eficiente.
- **Quando Usar:** Quando um processo é percebido como lento, caro ou propenso a erros.
- **Exemplo de Uso:** "Analise nosso processo de reembolso de despesas e sugira melhorias."

**`risk-assessment`**
- **Descrição:** Identifica, avalia e planeja mitigações para riscos operacionais, culminando em um Registro de Riscos (Risk Register).
- **Quando Usar:** Ao iniciar um novo projeto, avaliar um novo fornecedor ou tomar uma decisão estratégica.
- **Exemplo de Uso:** "Faça uma avaliação de riscos para o lançamento do nosso novo aplicativo móvel."

**`runbook`**
- **Descrição:** Cria um guia operacional passo a passo para tarefas recorrentes ou procedimentos de emergência.
- **Quando Usar:** Para documentar tarefas que a equipe de plantão (on-call) precisa executar de forma confiável.
- **Exemplo de Uso:** "Crie um runbook para reiniciar o servidor de aplicação em produção."

**`status-report`**
- **Descrição:** Gera um relatório de status de projeto conciso para a liderança, com KPIs, riscos e decisões necessárias.
- **Quando Usar:** Para atualizações semanais ou mensais sobre a saúde de um projeto.
- **Exemplo de Uso:** "Gere o relatório de status semanal para o projeto Alpha."

**`vendor-review`**
- **Descrição:** Avalia uma proposta de fornecedor, analisando o Custo Total de Propriedade (TCO), riscos e pontos de negociação.
- **Quando Usar:** Ao decidir sobre um novo fornecedor, renovar um contrato ou comparar alternativas.
- **Exemplo de Uso:** "Avalie esta proposta da DataCorp para um novo software de BI."

### 10.4 Design

**`accessibility-review`**
- **Descrição:** Audita um design ou página web em conformidade com as diretrizes WCAG 2.1 AA.
- **Quando Usar:** Antes do handoff para engenharia, para garantir que o design é acessível.
- **Exemplo de Uso:** "Faça uma auditoria de acessibilidade nesta tela de login."

**`design-critique`**
- **Descrição:** Fornece feedback de design estruturado sobre usabilidade, hierarquia visual e consistência.
- **Quando Usar:** Em qualquer estágio do processo de design para obter uma segunda opinião qualificada.
- **Exemplo de Uso:** "Critique este mockup para o nosso novo dashboard."

**`design-handoff`**
- **Descrição:** Gera uma especificação técnica detalhada a partir de um design finalizado para a equipe de engenharia.
- **Quando Usar:** Quando um design está pronto para ser implementado.
- **Exemplo de Uso:** "Crie a especificação de handoff para esta nova tela de perfil de usuário."

**`design-system`**
- **Descrição:** Audita, documenta ou estende um Design System.
- **Quando Usar:** Para manter a consistência do sistema, documentar um novo componente ou propor um novo padrão.
- **Exemplo de Uso:** "Audite nosso design system em busca de valores de cor hardcoded."

**`user-research`**
- **Descrição:** Planeja e guia a execução de pesquisas com usuários, desde a criação do plano e roteiro até a condução.
- **Quando Usar:** Quando é preciso entender as necessidades, dores e motivações dos usuários.
- **Exemplo de Uso:** "Crie um plano de pesquisa para descobrir por que os usuários estão abandonando o carrinho de compras."

### 10.5 Produtividade

**`memory-management`**
- **Descrição:** (Skill interna) Define como o agente gerencia seu conhecimento sobre o jargão, pessoas e projetos do usuário.
- **Quando Usar:** Usada automaticamente pelo agente para decodificar e armazenar informações.
- **Exemplo de Uso:** (Agente, internamente) "O usuário disse 'PSR'. Consultando `CLAUDE.md`, isso significa 'Pipeline Status Report'."

**`start`**
- **Descrição:** Inicializa o sistema de produtividade, criando os arquivos necessários e iniciando o processo de aprendizado da memória.
- **Quando Usar:** Na primeira vez que o sistema é configurado.
- **Exemplo de Uso:** "/start"

**`task-management`**
- **Descrição:** (Skill interna) Define como o agente manipula o arquivo `TASKS.md`.
- **Quando Usar:** Usada automaticamente pelo agente para adicionar, completar ou listar tarefas.
- **Exemplo de Uso:** (Agente, internamente) "O usuário disse 'adicione uma tarefa'. Vou anexar ao `## Active` em `TASKS.md`."

**`update`**
- **Descrição:** Sincroniza as tarefas e a memória do agente com fontes externas e atividades recentes.
- **Quando Usar:** Para manter a lista de tarefas e o conhecimento do agente atualizados.
- **Exemplo de Uso:** "/update --comprehensive"

### 10.6 Fluxo de Trabalho: Revisão de Projeto em Andamento

Quando solicitado a fazer uma revisão geral de um projeto, utilize uma combinação de skills para uma análise 360°.

1.  **Estratégia e Produto (`roadmap-update`, `metrics-review`):** Comece entendendo os objetivos. "Qual é o roadmap atual para este projeto?" e "Quais são as métricas de sucesso e como elas estão performando?".
2.  **Arquitetura e Design (`architecture`, `system-design`):** Avalie a fundação técnica. "Me mostre os principais ADRs deste projeto." ou "Como a arquitetura suporta os requisitos não-funcionais?".
3.  **Código e Qualidade (`code-review`, `test-and-qa`):** Mergulhe na implementação. "Aponte-me para um PR recente de uma funcionalidade crítica para eu revisar." e "Qual é a estratégia de testes para este serviço?".
4.  **Processos e Operações (`deploy-checklist`, `incident-response`):** Verifique a maturidade operacional. "Como é o processo de deploy para produção?" e "Me conte sobre o último incidente de produção que vocês tiveram."
5.  **Documentação (`documentation`):** Avalie a sustentabilidade do conhecimento. "Me mostre o README do repositório."
