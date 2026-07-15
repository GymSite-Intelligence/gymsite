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
