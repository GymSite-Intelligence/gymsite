# Design — CARTO híbrido (warehouse + endpoint logado + iframe)

**Data:** 2026-08-27  
**Âmbito:** Usar a conta CARTO (`gcp-us-east1.app.carto.com`, DW `carto_dw`) em três fases: laboratório (Workflows/Builder), número de teste numa API autenticada, iframe do Builder no Explorar **só para sessão logada**. Relatório PDF, chat do consultor e Explorar anônimo **não** mudam neste ciclo.  
**Humano:** Marcelo  
**Relacionado:** [2026-08-26-explorar-maplibre-design.md](./2026-08-26-explorar-maplibre-design.md) (basemap MapLibre; **esta spec revoga** a proibição de iframe do Builder)  
**Docs CARTO:** [Overview developers](https://docs.carto.com/carto-for-developers/overview), [Workflows](https://docs.carto.com/carto-user-manual/workflows.md), [Named Sources](https://docs.carto.com/carto-user-manual/developers/named-sources.md), [Data Observatory](https://docs.carto.com/carto-user-manual/data-observatory.md)

---

## 1. Problema

O GymSite já cruza IBGE, Maps, MRLR e isócrona ORS no produto. A conta CARTO está ligada (plugin/MCP no Cursor, 1 conexão BigQuery gerida, 2 mapas no Builder — um sem título, um demo de varejo EUA). **Não há Workflows.** O Explorar usa CARTO só como estilo de mapa, não como analítica.

Queremos enriquecer dados e rotas SQL/fluxo **sem** misturar fonte: o warehouse **produz** tabela; o GymSite **exibe** com carimbo. Dump Receita/CKAN entram quando existirem no BQ — não bloqueiam a Fase A.

---

## 2. Decisões travadas

| # | Escolha |
|---|---|
| Abordagem | **Híbrido** (não Builder-no-centro, não warehouse-só-lab) |
| Ordem | **A → B → C**. Não pular fase |
| Números | Sempre **valor · base · fonte · janela**. LLM não calcula. Sem tabela = sem número (erro explícito) |
| Aluguel / MRLR | Intocado. CARTO não vira fonte de aluguel |
| Isoline produto | Continua **ORS**. LDS CARTO não no mesmo clique do Explorar; MCP isoline só Cursor |
| MapLibre | Permanece no Explorar (rua, iso, pins) |
| Iframe Builder | **Permitido** neste ciclo (override da spec 2026-08-26 §1/§2) |
| Quem vê B e C | Só **app logado** (Bearer Supabase, mesmo padrão de `chat` / `explorar` autenticado). Anônimo e PDF: não |
| Endpoint B | **Exclusivo de teste**, não alimenta A0–A9 nem PDF |
| Primeiro recorte A | **Uma cidade** (ex. Fortaleza) a partir de pontos já geocodificados no pipeline, importados em `carto_dw` `shared` |
| Primeiro fluxo | `gym_hex_cidade`: ponto → H3 → `n_academias` → tabela estável |
| Primeiro número B | Contagem no hex (ou recorte acordado) dessa cidade |
| Observatory / Receita | Depois da A estável; não no aceite da A |
| Mapa demo EUA | Não usar como dado de produto |
| Privacidade embed C | Iframe só logado; mapa compartilhado para embed **restrito** ou público consciente — nunca vazar mapa privado no Explorar anônimo |

---

## 3. Arquitetura

```
[Cursor MCP / Builder]     [carto_dw BigQuery]
        │                         │
        │  A: Workflow + mapa     │  tabelas shared + DO
        ▼                         ▼
   mapa Builder ──────────► tabela gym_hex_* (estável)
                                  │
                    B: GET autenticado GymSite
                                  │
                    C: iframe Explorar (logado)
                                  │
              (fora deste ciclo) PDF / A6 / anônimo
```

| Unidade | Faz | Depende |
|---|---|---|
| `carto_dw` | Guarda pontos, hex, saída do fluxo | Import / Observatory |
| Workflow `gym_hex_cidade` | Receita SQL reexecutável | Pontos com lat/lng |
| Builder map (produto) | Hex + pins da cidade A | Tabela estável |
| `GET` teste logado | Devolve contagem + carimbo | Tabela; JWT |
| Explorar MapLibre | Fluxo lead / iso ORS | Spec 2026-08-26 |
| Explorar iframe | Aba/modo “Camadas CARTO” | Sessão + URL embed |
| Named source | Opcional se o front chamar Maps/SQL API | Token CARTO; **não** obrigatório se B for só backend→BQ |

Não extrair um motor de mapa genérico para `/mapa` (Google dos relatórios).

---

## 4. Fase A — laboratório (sem site)

**Entrega:** fluxo no CARTO + mapa Builder **privado** (equipe). Plugin Cursor lista a tabela e (quando publicado) roda o fluxo via MCP.

**Dados:** importar recorte de concorrentes/pontos já geocodificados (uma cidade) para `shared`. Data Observatory só **cruzar** se já houver subscription BR; senão pular.

**Fluxo:** pontos → H3 → contar → gravar tabela com `hex`, `n_academias`, `cidade`, `fonte`, `gerado_em`. Não só `workflows_temp`.

**Fora da A:** iframe, API GymSite, PDF, geocode LDS em massa, dump Receita.

**Aceite A:** abrir Builder, ver hex + pins da cidade; reexecutar o fluxo sem retrabalho; MCP encontra a tabela.

---

## 5. Fase B — endpoint exclusivo logado

**Entrega:** um `GET` (path a fixar no plano, ex. `/api/carto/hex-count`) no backend FastAPI.

**Auth:** `Authorization: Bearer` + `sb.auth.get_user` (mesmo espírito de `backend/routers/chat.py` / trechos autenticados de `explorar.py`). 401 sem token válido.

**Contrato (mínimo):** query `cidade` e/ou `lat`+`lng`; resposta JSON com `n_academias` (ou equivalente), `hex` se aplicável, `fonte` (nome do fluxo/tabela), `gerado_em`, `base` (ex. “H3 da tabela gym_hex_cidade”). Sem linha na tabela: **4xx/404** com mensagem, corpo **sem** campo numérico de contagem.

**UI:** tela ou painel **só logado** que chama esse GET e mostra o JSON/bloco. Não liga em `site_agent`, PDF nem degustação pública.

**Leitura da tabela:** backend GymSite consulta BQ `carto_dw` (credencial de serviço, não a chave do browser) **ou** réplica periódica do recorte no Supabase — uma das duas no plano de implementação; o contrato HTTP não muda.

**Aceite B:** logado + tabela ok → número + carimbo; logado + tabela vazia/fora → erro, sem número; deslogado → 401.

---

## 6. Fase C — iframe no Explorar logado

**Entrega:** no `/explorar`, com sessão, modo ou aba **Camadas CARTO**: iframe do mapa Builder da Fase A (não o demo EUA). Chrome GymSite em volta.

**Anônimo:** iframe **não** monta; Explorar igual hoje (lead + MapLibre).

**Iso:** não disparar isoline LDS do Builder no mesmo controle da isócrona ORS.

**Aceite C:** logado vê o recorte da cidade A no iframe; deslogado não vê iframe; MapLibre e Analisar continuam no modo rua.

---

## 7. Fora deste ciclo

- Injetar o número CARTO no PDF / A6 / A9  
- Iframe ou endpoint para anônimo  
- Substituir MapLibre pelo Builder  
- CNAE Receita / CKAN como fonte da A (ficam backlog quando o ficheiro estiver no BQ)  
- Segundo número (renda Observatory)  
- Alterar MRLR, SearchAPI de aluguel, Places como fallback de concorrentes  

---

## 8. Self-review

**Data:** 2026-08-27  

| Check | Resultado |
|---|---|
| Placeholder | Path HTTP exato do GET fica no **plano**, não bloqueia aceite da spec |
| Consistência | MapLibre permanece; iframe só logado; PDF fora; MRLR fora; ORS vs LDS separado |
| Escopo | Três fases, uma spec; implementação em planos por fase |
| Ambiguidade | “App logado” = JWT Supabase no GymSite, não login CARTO do cliente |
| Override | Spec MapLibre 2026-08-26: iframe Builder **passou a permitido** aqui, só C logado |
| Aceite | A/B/C com critérios testáveis |
| Fora | §7 explícito |
