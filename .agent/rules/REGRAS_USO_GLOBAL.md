# Regras de Uso Global — GymSite Intelligence

> **Derivado de:** [P-000_REGRA_MESTRA_MUDANCA.md](P-000_REGRA_MESTRA_MUDANCA.md)  
> **Status:** Ativo · uso diário por agentes e humanos  
> **Conflito:** P-000 prevalece sobre este resumo. Este arquivo **não substitui** a regra mestra.

---

## 1. O que é este documento

Card operacional das regras que valem **em todo o repo** (`gymsite_intelligence`):

- código, schema, pipeline A0–A9, tools, frontend, deploy
- complementa (não duplica) `processo-mudanca.md` (UX/schema P-001…P-010) e `workspace.md` (qualidade de código)

**Dois conjuntos de P-00x — não misturar:**

| Conjunto | Arquivo | Significado |
|---|---|---|
| **P-000 §1–§9** | `P-000_REGRA_MESTRA_MUDANCA.md` | Governança técnica (fontes, carimbo, deploy, LLM) |
| **P-001…P-010** | `processo-mudanca.md` | Produto/UX (mobile-first, FK, soft delete, vocabulário) |
| **Âncoras internas P-000** | tags `(P-001)` fontes, `(P-002)` carimbo, `(P-004)` ler-fonte | **Só dentro do P-000** — IDs diferentes dos de produto |

---

## 2. Checklist — antes de qualquer mudança

Use como gate mental. Se algum item falhar, pare e leia a fonte.

| # | Regra | Ação mínima |
|---|---|---|
| 1 | **Minimalismo cirúrgico** | Diff só no pedido. Sem refactor adjacente, sem “melhoria” especulativa. |
| 2 | **Ler a fonte (P-004)** | Abrir código/schema/API real antes de afirmar comportamento. |
| 3 | **Hierarquia de fontes (P-001)** | Tier 0 > Tier 1 > Tier 2. MRLR = aluguel viabilidade. LLM ≠ número. |
| 4 | **Lazy imports em `tools/`** | Dependências pesadas **dentro** da função, nunca no topo do módulo. |
| 5 | **Carimbo em todo número (P-002)** | `valor · base · fonte · janela` (+ município/UF se regulatório). |
| 6 | **LLM narra, tools calculam (§6)** | Métrica/veredito = tool ou override determinístico. |
| 7 | **Deploy canônico (§7–§8)** | Front = CF Pages; API/worker = Cloud Run `us-central1`; domínios separados. |
| 8 | **Repo certo (§9)** | `gymsite` = app logado; `gym-insight-hub` = landing/degustação. |
| 9 | **Teste fecha a etapa** | Backend: `.venv/Scripts/python.exe -m pytest`. Front: `npx tsc --noEmit`. |

---

## 3. Regras por tipo de trabalho

### 3.1 Código Python / backend

- Funções e arquivos em **inglês**; domínio na UI em PT-BR (`workspace.md`).
- Dinheiro no banco: **centavos (integer)**. Datas: **timestamptz UTC**.
- Comentário só quando registra **decisão** ou armadilha não óbvia — não repete o código.
- Antes de alterar `agents/*.py`, `tools/*_tools.py` ou contrato de relatório:
  1. [conferencia-fontes-pipeline.md](conferencia-fontes-pipeline.md)
  2. [pipeline-fontes-deterministicas.md](pipeline-fontes-deterministicas.md)
- **Não conformidade em tool (custo/fonte/fallback):** [auditoria-tools.md](auditoria-tools.md) (Draft→Approved, 5 Whys + `.mmd`) sob guarda-chuva [auditoria-conformidade.md](auditoria-conformidade.md).

### 3.2 Pipeline / agentes A0–A9

| Invariante | Fonte |
|---|---|
| Aluguel viabilidade | `aluguel_mrlr.py` no A4 — **nunca** SearchAPI/portais/LLM |
| Concorrentes / Maps | SearchAPI primário; Places fallback |
| Obra CAPEX | CUB/SINAPI via `obra_regua.py`; `tipo_obra` adaptação \| bruta |
| Taxas municipais | `legal_fees_pilot` quando cidade no piloto |
| Número no PDF/UI | Tool/banco + carimbo — A6 lê `*_pronto` (snapshot), não eco LLM |

Nova fonte, tabela ou tool → atualizar `docs/metodologia/data_lineage.md` no mesmo PR.

### 3.3 Frontend / UI / chat

- Tokens de design (`bg-primary`, `text-foreground`) — sem hex solto (`.cursor/rules/frontend-*`).
- **Carimbo visível** em número, ranking, payback, saturação, aluguel (`P-000 §5.1`).
- **Uma fonte → uma renderização** — mesmo campo, mesma regra em todas as telas.
- Chat **não inventa default** — reflete `input_params`; inferência = outro campo + carimbo.
- Mudança de layout: evidência visual versionada (`docs/frontend/artifacts/` ou screenshot).

### 3.4 Banco / migrations

- Schema real em `db/migrations/` — **ler antes** de query ou migration.
- **Pegadinha schema split (prod `epgedaiukjippepujuzc`):** tabelas em `gymsite.*` (e `shared.*`); `public.*` costuma ser **view**. `ALTER TABLE public…` em view **quebra**. DDL → schema real (`gymsite`/`shared`). Escritas → `tools.db_schema.tbl()`. Confirmar `relkind` antes. Ver P-000 §7.
- Seed `parametros_metodologia` (`python -m tools.parametros_seed`) atualiza **banco**; mudança em `tools/parametros_metodologia.py` / `financial_tools.py` exige **Cloud Run** (API + mesma imagem no worker).
- Vocabulário de domínio = tabela seedada (P-008 produto), não enum espalhado.
- Referência = **FK** (P-009). N:N = tabela associativa desde o dia 1 (P-010).
- Soft delete + auditoria (P-007) quando entidade de domínio.

### 3.5 Deploy e ambientes

| Camada | Destino | Disparo |
|---|---|---|
| `frontend/` (app logado) | CF Pages projeto `gymsite` → `getgymsite.com.br` | Build + `wrangler pages deploy` ou redeploy CF manual |
| Landing / degustação | CF `gym-insight-hub` → `gymsite.com.br` | Push `main` **+** redeploy manual (Actions morto) |
| API + pipeline | Cloud Run `gymsite-api` / `gymsite-worker` | Cloud Build ou `gcloud run deploy` |
| GCP produção | `gen-lang-client-0106729343`, região `us-central1` | Worker = **mesma imagem** da API após rebuild |

**Não confundir:** `getgymsite.com.br` (app) ≠ `gymsite.com.br` (marketing).

**Act-on / tools:** mudou `agents/` · `tools/` · `parametros_metodologia` → Cloud Run **sim**. Só seed SQL → Cloud Run **não**.

### 3.6 Git e branches

- Trunk: **`main`**. Commits: Conventional Commits, inglês.
- Preview: `preview/site-*` (hub) ou `preview/app-*` (monorepo); vida ≤ 14 dias.
- Após merge: `git fetch --prune`; branch com `ahead=0` → deletar remota/local.
- Dados pesados (`docs/produto/brand/`) — commit separado (push HTTPS estoura).

---

## 4. Hierarquia de dados (resumo P-001)

```
Tier 0 — Determinístico (sempre ganha)
  MRLR, IBGE, RFB, parametros_metodologia, CUB/SINAPI curado, legal_fees_pilot

Tier 1 — API paga estruturada
  SearchAPI, Google Places (preenche gap do Tier 0)

Tier 2 — Qualitativo
  google_search (A7), Kimi (A0), RAG — contexto e narrativa, NUNCA OPEX/TIR/VPL
```

**Calibração financeira (A4):** CVM/IR (SMFT3, Bluefit) > ACAD/Sebrae > calibração GymSite com carimbo em `parametros_metodologia.py`.

**Fora do A4:** score de imóvel, NBR/lotação, veredito de ponto — não alimentam viabilidade financeira.

---

## 5. Formato de carimbo (P-002)

**Obrigatório** em relatório, PDF, chat e cards quando houver número ou exigência regulatória.

```
Valor · Base · Fonte · Janela
```

Exemplos:

- `60.165 hab · 105 setores (raio centróide) · IBGE Censo 2022`
- `374,20 BRL/m² · CUB 1969,47 m² × fator 0,19 · SindusCon-CE · jun/2026`
- `IT bombeiros · m² área · IT-11 CBMRJ · Rio de Janeiro/RJ · 2024`

Proxy (renda per capita, etc.) → rotular explicitamente como proxy na nota.

Mapa vivo: `docs/metodologia/data_lineage.md` + `tools/parametros_metodologia.py`.

---

## 6. LLM vs determinismo (§6)

| Pode LLM | Não pode LLM |
|---|---|
| Narrar seções A6/A9 | Calcular payback, margem, CAPEX, aluguel |
| Classificar texto livre | Escolher modelo recomendado ou score |
| Organizar markdown | Inventar concorrente, população, taxa municipal |
| Justificativa template (A4) | Completar RAG além do bloco recuperado |

Conflito tool vs LLM → **tool vence** no pós-processamento.

---

## 7. Mapa “o que ler quando”

| Situação | Ler primeiro |
|---|---|
| Qualquer mudança | Este arquivo + [P-000](P-000_REGRA_MESTRA_MUDANCA.md) §1–§6 |
| UX, formulário, FK, mobile | [processo-mudanca.md](processo-mudanca.md) |
| Qualidade código, naming, git | [workspace.md](workspace.md) |
| Pipeline / fontes Maps/aluguel/obra | [conferencia-fontes-pipeline.md](conferencia-fontes-pipeline.md) |
| Conformidade global (ciclo gaps) | [auditoria-conformidade.md](auditoria-conformidade.md) |
| NC em tool (5 Whys / custo API) | [auditoria-tools.md](auditoria-tools.md) |
| Agente específico A0–A9 | `.agent/skills/gymsite-pipeline/SKILL.md` + `agents/specs/SPEC_A*.md` |
| Deploy / env / CF gotchas | P-000 §7–§8 + `CLAUDE.md` |
| Lineage de dados | `docs/metodologia/data_lineage.md` |
| Prompt craft | `docs/metodologia/prompts/guia_prompts_pipeline.md` |

Skills: carregar **só** a relevante em `.agent/skills/<nome>/SKILL.md` — nunca o catálogo inteiro de uma vez.

---

## 8. Anti-padrões (nunca)

- Assumir comportamento de lib/API/schema “de memória”
- Refatorar fora do escopo “porque estava feio”
- `from google.adk...` no topo de arquivos em `tools/`
- Search Grounding ou LLM para aluguel OPEX ou defaults financeiros
- Número na UI sem carimbo ou sem campo canônico no JSON
- Deploy front só com push (sem redeploy CF quando necessário)
- Publicar monorepo no projeto CF da landing
- `npm run dev` / `npm run build` como “teste” de tipo (usar `tsc`)
- Commit de `.env`, secrets ou assets de marca pesados junto com código

---

## 9. Comunicação com o Marcelo (produto)

Erro → explicar **o que quebrou na prática** antes do jargão.  
Melhoria → dar **exemplo de uso** para quem usa o produto.

Detalhe técnico (arquivo, função, erro exato) vem **depois** da frase simples.

---

*Última sincronização com P-000: 2026-07-14. Atualizar este resumo quando P-000 ganhar seção nova.*
