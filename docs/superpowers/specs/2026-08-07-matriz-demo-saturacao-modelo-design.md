# Design — Matriz Demografia × Saturação → Modelo de Negócio Adequado

**Data:** 2026-08-07  
**Âmbito:** Cruzar potencial demográfico (A2 / polígono) com oferta instalada (A3a/A3b) para recomendar modelo (low/mid/premium/nicho) sem “armadilha demográfica”  
**Humano:** Marcelo  
**Abordagem:** Um spec, **3 waves** (W1 matriz + leitura; W2 veto A4; W3 sinais A0 CNPJ)  
**Depende de:** Spec C W1 polígono IBGE (`2026-08-06-spec-c-bairro-poligono-ibge-design.md`) — mesma régua espacial pop × concorrentes; headroom A9 já existente (`tools/posicionamento_renda.py`, `docs/metodologia/posicionamento_headroom_premium.md`)

**Nome:** Spec Matriz (não é Spec C; Spec C = polígono). Consome Spec C + A2 + A3 + A0 facts.

---

## 1. Problema (produto)

Hoje o relatório pode sugerir **Premium** só porque a renda/idade “batem”, mesmo com Bio Ritmo/Bodytech saturando o polígono — ou ignorar praça mid com vácuo de oferta.

Já existe:
- A2 → renda, idade×sexo, pop  
- A3a → lista Maps (Spec C → PIP)  
- A3b → `nivel_saturacao` (ainda misturado raio km / contagem bairro), gaps, oferta  
- A9 → headroom + zonas 1–5 → `OCEANO_AZUL` / `TRANSICAO` / `VERMELHO`  
- A4 → 3 cenários $ + `modelo_recomendado` por renda/payback  

**Falta:** bloco explícito **mix Low/Mid/Premium + N/10k hab no polígono + quadrante** que (1) narra “Modelo Adequado” e (2) **veta** Premium no A4 quando o quadrante for Armadilha de Renda.

---

## 2. Meta / fora

### Meta

1. Função determinística `matriz_demo_saturacao(...)` → quadrante + modelo sugerido + carimbos.  
2. PDF/UI: seção curta **antes** da leitura executiva / junto ao posicionamento.  
3. A4: se Armadilha → não recomendar Premium generalista (nicho ou Mid-High).  
4. Mesma base espacial: polígono IBGE quando houver; senão fallback raio (carimbo).

### Fora (v1)

| Item | Destino |
|---|---|
| Share of wallet 60%, churn aluguel 40%, SOV Google | Fora — sem fonte estável |
| Canibalização rede própria VECTRA | Spec depois |
| Âncora shopping como gate hard | Heurística opcional W3+ |
| Mudar contrato A0 qualitativo / inventar saturação no LLM | Proibido |
| Recalcular ERRC do zero | A9 gaps ficam; matriz só condiciona modelo/veredito |
| Cobertura 100% municípios sem polígono | Fallback raio + carimbo |

---

## 3. Decisões

| # | Escolha |
|---|---|
| Onde mora a matriz | Módulo `tools/matriz_demo_saturacao.py` — **não** dentro de A0/A2 |
| Quem chama W1 | A9 (monta bloco + narra) + A6/PDF leem state |
| Eixo X (demo) | A2 / `demografia_bairro`: renda_pc ou percentil, faixa dominante 25–39 / 40+, pop, `censo_base` |
| Eixo Y (comp) | A3a N no polígono + A3b mix tier (ticket/rede) + rating médio |
| Saturação primária W1 | **N academias / 10k hab** no polígono (não só densidade/km² do raio 3 km) |
| Mix | Contagem `{low, mid, premium, nicho, desconhecido}` por heurística determinística (rede conhecida + ticket) |
| 4 quadrantes | Oceano Azul · Guerra de Preço · Armadilha de Renda · Deserto Viável |
| Ligação A9 legado | Quadrante **refina** zona/veredito; não apaga headroom — se conflito, carimbo `matriz_override` |
| A4 W2 | Armadilha → `modelo_recomendado` ≠ premium generalista; prefer mid ou flag nicho |
| A0 W3 | Só facts: baixas/aberturas 24m bairro + flag rede âncora no parque |

### Quadrantes (regras W1 — limiares em `param()`)

| Quadrante | Demo (X) | Comp (Y) | Modelo sugerido |
|---|---|---|---|
| **Oceano Azul** | Alta renda (percentil ≥ mid/premium) + adultos | N/10k baixo **ou** mix sem Premium + rating fraco | Premium / Mid-High |
| **Armadilha de Renda** | Alta renda | Mix com ≥2 Premium **ou** N/10k alto no segmento premium | Hiper-nicho / Mid-High — **não** Premium genérico |
| **Guerra de Preço** | Renda média/baixa | Mix dominado Low + N/10k alto | Low ultra-eficiente **ou** nicho; evitar Mid genérico |
| **Deserto Viável** | Qualquer / média | N baixo mas demo fraca ou red flag CNPJ | Teste leve / investigar “por quê vazio” |

Limiares numéricos exatos → `parametros_metodologia` (ex. `matriz_n_per_10k_alto`, `matriz_premium_min_armadilha=2`). Sem hardcode solto no agente.

---

## 4. Waves

### Wave 1 — Matriz + leitura (A2×A3 → A9/PDF)

**Compute**

- Input: `demografia_bairro` (pop, renda, percentil se houver, `censo_base`), `concorrentes_brutos` / detalhados (lat/lng, rating, ticket/rede).  
- Filtrar concorrentes no mesmo polígono (reusar Spec C `ring` / `gate_espacial`) ou fallback `classificar_saturacao_bairro`.  
- Classificar cada um em tier → mix.  
- `n_per_10k = N / (pop/10000)`.  
- Emitir:

```text
matriz_demo_saturacao: {
  quadrante, modelo_sugerido, n_poligono, n_per_10k,
  mix: {low, mid, premium, nicho, desconhecido},
  rating_medio, censo_base, fonte_espacial,
  acao_estrategica,  # 1 frase template
  carimbo: "valor · base · fonte · janela"
}
```

**A9 / PDF**

- Seção “Modelo de Negócio Adequado” (template, sem LLM inventar N).  
- Leitura executiva: 4–6 bullets (demo · mix · quadrante · modelo · risco · veredito).  
- Preview HTML em `docs/superpowers/previews/`.

**Exemplo de uso:** Cocó rico + 3 Premium no polígono → Armadilha → “não abrir Premium genérico; nicho ou Mid-High”.

### Wave 2 — Veto A4

- `analise_financeira` / escolha de `modelo_recomendado` lê `matriz_demo_saturacao.quadrante`.  
- Se Armadilha e cenário premium “ganharia” só por renda → rebaixar com `justificativa_matriz`.  
- Teste: bairro rico + mix premium → recomendado ≠ premium (ou premium só com flag nicho).

### Wave 3 — Sinais A0 (opcional na mesma spec, wave separada)

- Baixas/aberturas 24m no bairro (já no parque CNPJ) → red flag “rotatividade”.  
- Flag `rede_ancora_presente` (lista fechada Smart Fit / Bio Ritmo / Bodytech / …).  
- Entram como modificadores do quadrante (não substituem N/10k).

---

## 5. Aceite

### W1

- [ ] Unit: Oceano Azul (alta renda, 0 premium, N/10k baixo) → quadrante certo  
- [ ] Unit: Armadilha (alta renda, ≥2 premium) → Armadilha + modelo ≠ premium genérico  
- [ ] Unit: mesma pop+N → `n_per_10k` reproduzível  
- [ ] Sem polígono → fallback + `fonte_espacial=raio_fallback`  
- [ ] Preview HTML aprovado Marcelo  
- [ ] `PIPELINE_AGENTES.md` + conferencia-fontes: matriz como fonte do modelo narrado  

### W2

- [ ] Teste A4: Armadilha impede `modelo_recomendado=premium` genérico  
- [ ] Carimbo na justificativa do cenário  

### W3

- [ ] Teste: baixas_24m altas elevam Deserto/red flag sem mudar pop  

---

## 6. Ordem

1. Spec C W1 estável (polígono) — **pré-requisito forte** para N/10k honesto  
2. Matriz W1  
3. A4 W2  
4. A0 W3  

Ops P0 W3 (RFB VPS) paralelo OK.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Tier mix errado (Smart Fit classificado mid) | Tabela de redes + ticket; `desconhecido` explícito |
| Pop polígono ≠ N Maps (bases) | Exigir Spec C; senão carimbo dual |
| Conflito headroom OCEANO vs Armadilha | Precedência: **Armadilha vence** se mix premium ≥ limiar |
| A4 e A9 divergem | W2 alinha A4 à matriz; A8 coerência já existe — estender |

---

## 8. Referências

- Input humano 2026-08-07 (matriz demografia × saturação)  
- `docs/metodologia/posicionamento_headroom_premium.md`  
- `tools/posicionamento_renda.py` · `tools/competitor_tools.py` (`classificar_saturacao*`)  
- Spec C: `docs/superpowers/specs/2026-08-06-spec-c-bairro-poligono-ibge-design.md`  
- `docs/arquitetura/PIPELINE_AGENTES.md`  
- `.agent/rules/conferencia-fontes-pipeline.md` · `spec-self-review.md` · `preview-aprovacao.md`

---

## Self-review

**Data:** 2026-08-07  
**Resultado:** ok

| Check | Achado |
|---|---|
| Placeholder | Limiares via `param()` — nomes citados; valores exatos no plano de implementação |
| Consistência | 3 waves; Armadilha vence headroom; Spec C pré-req |
| Escopo | Cabe em um plano; SOV/churn/canibalização fora |
| Ambiguidade | Matriz ≠ Spec C; quem chama = A9 W1, A4 W2 |
| Aceite | Checklist W1–W3 testável |
| Fora | §2 tabela |

Correções neste passo: nenhuma material após checklist.
