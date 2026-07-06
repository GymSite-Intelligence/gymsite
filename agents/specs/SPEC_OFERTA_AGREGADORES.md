# SPEC — Captação de oferta via agregadores (Wellhub · Gurupass · TotalPass)

> Criada 2026-07-07 com SONDAGEM AO VIVO das três fontes (evidências abaixo). Objetivo:
> consertar o GAP manco do relatório — "serviços entregues" quase vazio, ERRC com falso
> CRIAR, preço sem fonte — com captura DETERMINÍSTICA (zero LLM nesta camada).
> É a camada 3 do offer_mapper (site → Instagram → agregadores) e absorve a Task #9.

## 1. O que cada fonte entrega (sondado em 07/07, caso Cocó)

| Fonte | Render | Captura via | O que entrega (visto ao vivo) |
|---|---|---|---|
| **Wellhub** ★ | **HTML puro (SSR)** | httpx direto | Modalidades ("O que você pode fazer": Crossfit, Boot Camp…), **comodidades** (ar-condicionado, bioimpedância, estacionamento, vestiário, wi-fi…), **tier + preço** (Gold R$ 319,99/mês), **rating próprio** (CT Greenlife: 4,86 · 1.843 avaliações!), horários (24h), telefone, endereço, **handle do Instagram**, e BÔNUS: vizinhos com distância e tier ("REK CrossFit 596m · Gold") |
| **Gurupass** | SSR parcial | httpx direto | Modalidades + **grade horária por modalidade** (Muay Thai 2ª/4ª 19:20…), endereço, meta-description rica. **PREÇOS vêm por JS ("Loading…") — NÃO capturáveis com httpx** |
| **TotalPass** | **JS puro** (página vem vazia) | snippets Google com `site:` | Só via SearchAPI: `site:totalpass.com "<nome>"` — snippet confirma presença na rede e plano; ou Playwright FORA do caminho crítico (flag, mesmo padrão LISTINGS_PLAYWRIGHT) |

Armadilha de matching descoberta na sondagem: o Gurupass lista o VS Club como
**Aldeota** (nosso relatório: Cocó). Matching por **nome + cidade**, nunca por bairro.

## 2. Desenho do script — `tools/agregadores_fetcher.py`

Determinístico, fail-soft por concorrente, sem LLM. Fluxo por concorrente:

1. **Descoberta da URL do parceiro** (1× por concorrente, cacheada): SearchAPI
   `site:wellhub.com/pt-br/search/partners "<nome>" <cidade>` (idem gurupass
   `/detalhes-da-academia/`). Aceita o resultado SÓ se o título casa o nome
   (fuzzy leve por _norm_txt) — regra anti-falso-positivo, ver §4.
2. **Fetch**: httpx GET na URL do parceiro (Wellhub/Gurupass). TotalPass: sem fetch;
   usa o próprio snippet da descoberta.
3. **Parser por domínio** (regex/seletores sobre texto, testável com fixture HTML):
   - `_parse_wellhub(html)` → {modalidades[], comodidades[], tier_agregador{plano,
     preco_mensal}, rating_wellhub{nota, n}, horarios, instagram_handle, telefone}
   - `_parse_gurupass(html)` → {modalidades[], grade_horaria{}, endereco}
   - `_parse_totalpass_snippet(snippet)` → {presente: bool, plano_minimo?}
4. **Normalização pro contrato existente** (NADA de chave nova solta — lição do
   `servicos_entregues` da sugestão A3):
   - modalidades → `_detectar_modalidades` → chaves canônicas → entram em
     `oferta_concorrentes.<chave>.modalidades` (o A9 já consome — Task #8).
   - comodidades → mapa fixo amenity→catálogo (bioimpedância→`avaliacao`;
     kids→`area_kids`) + lista crua `comodidades` (alimenta confronto com DORES:
     "anuncia ar-condicionado" × reclamação de climatização).
   - **preço de agregador NUNCA vira preço de balcão**: campo separado
     `tier_agregador {plano, preco_mensal, fonte}`. É sinal de POSICIONAMENTO
     (aceitar só Gold ⇒ premium), não ticket. No PDF, coluna própria com rótulo
     "tier corporativo (Wellhub) — não é mensalidade de balcão".
   - `fontes` ganha "wellhub"/"gurupass"/"totalpass" e `confiabilidade_fonte` +0.2
     quando ≥1 agregador confirma (fonte estruturada > keyword de site).
5. **Cache em disco por URL** (mesmo padrão `_outscraper_cache`), TTL 30 dias.
   Custo: 1–2 chamadas SearchAPI por concorrente NOVO; zero nas rodadas seguintes.

## 3. Onde pluga

- `competitor_offer_mapper.mapear_oferta_concorrente` chama a camada 3 depois de
  site+IG (mesmo objeto OfertaMapeada; sem mudar assinatura da macro — cirúrgico).
- Com a Task #8 (praça inteira), o CT Greenlife entra elegível e sai com:
  crossfit/bootcamp/condicionamento + bioimpedância + Gold 319,99 + IG handle.
- PDF: "Planos e preços da concorrência" ganha coluna FONTE (site oficial / agregador
  tier / promo); "Ticket por segmento" ganha os serviços reais; divergência de rating
  (Google 3,9·64 × Wellhub 4,86·1.843 pro mesmo CT) exibida com as duas fontes.

## 4. Regras anti-lixo (lições da sugestão A3 rejeitada)

- Keyword SÓ conta em página CUJO título/URL casa o nome do concorrente. Snippet
  solto de dorking "OR" não conta NUNCA (o OR força keyword em todo resultado —
  inverteria o bug: de "ninguém oferece" pra "todo mundo oferece").
- Vocabulário ÚNICO: `MODALIDADES_KEYWORDS`/`_SERVICOS_CATALOGO`. Nenhuma lista
  paralela hardcoded.
- Saída SÓ no contrato `oferta_concorrentes` (consumido pelo A9/ERRC desde a #8).
- Respeitar robots/ToS: páginas públicas de perfil, sem login, sem app, rate ≤1 rps.

## 5. Aceitação (caso Cocó)

1. CT Greenlife: modalidades incluem Crossfit; comodidades incluem bioimpedância;
   tier Gold 319,99 com fonte "wellhub"; IG handle capturado.
2. VS Club: muay thai + natação + hidro via Gurupass (match apesar do bairro Aldeota).
3. ERRC do Cocó re-rodado: "Crossfit — oportunidade de CRIAR" NÃO aparece.
4. Nenhum preço de agregador exibido como mensalidade de balcão (rótulo obrigatório).
5. Segunda rodada do mesmo bairro: zero chamadas novas (cache).

## 6. Fora de escopo

- Login/área logada dos agregadores (ToS); Playwright no caminho crítico; preços de
  balcão do Gurupass (JS — só com Playwright fora do crítico ou API futura).
