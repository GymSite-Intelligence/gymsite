# A9 PDF — Smoke Test de Validação (Selos + Charts Fase A/B)

> Como validar os elementos visuais novos do relatório PDF do A9 — **programático**
> (asserts) e **visual** (inspeção do PDF de amostra). Cobre o que está construído até
> agora: selos de confiança + 3 charts Fase A/B. Atualizar ao adicionar visual novo.
>
> ⚠️ **Nota 2026-07-03:** os selos estão em main (PR #36). As 3 charts Fase A/B
> (`chart_gauge_veredito`, `chart_radar_perfil`, `chart_receita_resultado_cenarios`)
> ainda vivem SÓ na branch `feat/a9-pdf-report` (pdf/charts.py de lá) — port exige merge
> manual com a charts.py da main, que evoluiu independente.

## O que está construído

| Elemento | Arquivo | Dado (contrato) |
|----------|---------|-----------------|
| Selos de confiança (3 níveis) | `pdf/badges.py` + mapa `tools/confianca_dado.py` | `param_meta.categoria` / tier — sem fonte real |
| Gauge de veredito | `pdf/charts.py::chart_gauge_veredito` | `score_bairro` + `veredito` (✅ READY) |
| Radar do perfil | `pdf/charts.py::chart_radar_perfil` | `scores[]` 3 eixos (🔧 ADAPTER, já no model) |
| Colunas receita × resultado | `pdf/charts.py::chart_receita_resultado_cenarios` | `cenarios[].receita_mensal/lucro_mensal` (✅ READY) |

**Ainda NÃO construídos** (Fase B — exigem estender `pdf/models.py`+`adapters.py`):
DRE (`custos_detalhados`), tornado (`sensibilidade`), scatter-distância (`distancia_km`).
**Bloqueado:** scatter-preço (A3c desabilitado, GymSite #127). Ver `docs/A9_DATA_CONTRACT.md`.

> ⚠️ Rodar TODOS os comandos a partir do **repo root** (`gymsite_intelligence/`).
> Fora dele dá `ModuleNotFoundError: No module named 'tools'` / `file not found`.
> `cd C:\Users\marce\gymsite_intelligence` antes.

## 1. Validação programática (CI-friendly)

```bash
# asserts: cada visual renderiza PNG/PDF válido + edge cases (None/poucos eixos)
python -m pytest tools/test_pdf_charts_fase_a.py tools/test_confianca_dado.py -q
```
Esperado: **10 passed**. Cobre:
- mapa `categoria→nível` (benchmark/calibracao→ESTIMATIVA, aberto→PROJEÇÃO, sem-param→MEDIDO);
- `agregar_nivel` = menor confiança das entradas;
- cada chart gera PNG (`\x89PNG`) > 1 KB;
- degradação: `score=None` → gauge None; `< 3 eixos` → radar None; cenários vazios → None.

## 2. Validação visual (inspeção humana)

```bash
# gera PDF de amostra com dados FAKE (não toca pipeline/Supabase)
python -m tools.smoke_pdf_visuais build/smoke_pdf_visuais.pdf
# abre o PDF gerado e confere o checklist abaixo
```

### Checklist visual

**Selos:**
- [ ] 3 selos lado a lado: `DADO MEDIDO` (TEAL, ponto cheio) · `ESTIMATIVA` (ORANGE, meio) · `PROJEÇÃO` (SLATE, vazado).
- [ ] Pill arredondado (raio = metade da altura), texto MAIÚSCULO Helvetica-Bold, ícone à esquerda.
- [ ] Cor do texto/borda/ícone = foreground da variante; fundo = versão clara da mesma matiz.

**Gauge de veredito:**
- [ ] Semicírculo 0–10, arco preenchido proporcional ao score, número grande central + "/ 10".
- [ ] Cor do arco = cor do veredito (INVESTIGAR MAIS = laranja `#EA580C`); rótulo do veredito acima.

**Radar:**
- [ ] Polígono de 3 eixos (Demográfico / Competitivo / Viabilidade), escala 0–10, área TEAL translúcida.

**Colunas receita × resultado:**
- [ ] 3 cenários (Econômico / Padrão / Premium), 2 barras cada (receita TEAL + resultado verde/vermelho por sinal), linha do zero.

### Impressão P&B (acessibilidade — badge spec §7)
- [ ] Imprimir/visualizar em escala de cinza: os 3 selos ainda se distinguem **pela FORMA do ícone** (cheio/meio/vazado), não só pela cor.

## 3. Critérios de aprovação

| Critério | Como |
|----------|------|
| Sem exceção no render | smoke script sai `OK: ... bytes` (exit 0) |
| Degradação graciosa | dado ausente → visual omitido, nunca crash (cobre pytest) |
| Cores = identidade | conferem `pdf/theme.py` (TEAL/ORANGE/SLATE/VEREDITO_COLORS) |
| Sem fonte real citada | nenhum nome de provedor nos selos/notas |

## 4. Notas
- O `build/` é artefato (gitignored) — o PDF de amostra não é versionado.
- Para validar com dado REAL (não fake): rodar o pipeline de um relatório e gerar o PDF via
  `pdf/builder.py` (integração dos selos/charts no builder ainda é a próxima fatia).
