# Índice de Pressão Migratório-Concorrencial (IPM)

Cruzamento **mortalidade de CNPJs** × **aberturas** × **saldo migratório** na escala local (bairro / RA / setor), CNAE 9313-1/00.

Objetivo: achar o **ponto doce** (demanda populacional cresce mais rápido que a oferta absorve) sem cair na armadilha de “bairro que cresce = abrir academia”.

---

## 1. Matriz de interseção (4 cenários)

Eixos principais na prática:

| | Mortalidade baixa (churn &lt; 1,5% trim.) | Mortalidade alta (churn &gt; 2,5% trim.) |
| --- | --- | --- |
| **Imigração alta** (+ saldo migratório) | **A — Ponto doce** · abertura tipicamente alta | **C — Ilusionismo** · abertura tipicamente alta |
| **Emigração / estagnação** (− ou ~0) | **B — Fortaleza consolidada** · abertura baixa | **D — Decadência / evasão** · abertura baixa |

> Abertura alta/baixa entra como **terceiro eixo** (e, empiricamente, costuma correlacionar com imigração). Sempre reportar as três variáveis; não colapsar só em 2D.

### A — Ponto doce (oportunidade ouro)

- Condição: migração + · abertura alta · mortalidade baixa  
- Leitura: demanda cresce mais rápido que a oferta satura  
- Decisão: **entrar rápido** (greenfield com tese clara)

### C — Armadilha do ilusionismo (risco)

- Condição: migração + · abertura alta · **mortalidade alta**  
- Leitura: “falsa oportunidade” — ponto caro, capex errado, canibalização  
- Decisão: **só com diferenciação extrema ou caixa ≥ 24 meses**

### B — Fortaleza consolidada (substituição)

- Condição: migração ~ · abertura baixa · mortalidade baixa  
- Leitura: adensado, operadores protegidos, pouco greenfield genérico  
- Decisão: **M&A / assumir operação antiga**, não abrir do zero

### D — Decadência / evasão (zona amarela)

- Condição: migração − · abertura baixa · mortalidade alta (souvent veteranos ≥ 5 anos)  
- Leitura: perda de demanda jovem; academias maduras fecham  
- Decisão: **evitar greenfield**; se já opera → pivot (sênior / boutique / ticket)

---

## 2. Fórmula $IPM$

$$
IPM = \frac{\text{Saldo migratório líquido (novos moradores no período)}}{(\text{Aberturas} \times 1{,}5) + (\text{Baixas} \times 0{,}5)}
$$

| Faixa | Sinal | Leitura |
| --- | --- | --- |
| $IPM &gt; 1\,500$ | Verde | Sub-atendido — gente nova &gt;&gt; eventos de oferta |
| $500 \le IPM \le 1\,500$ | Amarelo | Equilíbrio — sucesso depende de preço/posicionamento |
| $IPM &lt; 500$ ou negativo | Vermelho | Saturação / canibalização — briga por carteira |

### Cuidados de implementação

1. **Unidades:** numerador = pessoas; denominador = eventos CNPJ. Thresholds **não são universais** — calibrar por escala (RA vs município vs setor) e horizonte (trimestre vs ano).  
2. **Pesos 1,5 / 0,5:** aberturas pesam mais (pressão competitiva nova); baixas pesam menos (já saíram do parque). Documentar se recalibrar via `param()`.  
3. **Sem saldo migratório local:** **não inventar IPM**. Usar proxy (habite-se, ligações novas) rotulado, ou classificar só mortalidade × abertura e marcar migração `unknown`.  
4. **Churn vs mortalidade absoluta:** thresholds 1,5% / 2,5% são **trimestrais** na série Top 3 GymSite; não misturar com taxa anual sem converter.

---

## 3. Fontes de dados

| Camada | Fonte | Papel |
| --- | --- | --- |
| Oferta CNPJ | Receita CNAE 9313-1/00 (loop GymSite) | Aberturas, baixas, vida, CEP/bairro |
| Renda / demografia | IBGE Censo · PDAD DF (IPEDF) | Capacidade de pagar; RA no DF |
| Migração oficial | Censo / PDAD tempo de residência · origem | Saldo migratório estrutural |
| **Proxy curto prazo** | **MCMV (Min. Cidades) UH entregues/contratadas** · habite-se · lig. água/energia | Adensamento; numerador IPM com `migracao_fonte=mcmv_proxy` |

### Habitação → ficha (`habitacao`)

Helpers: `scripts/lib/mcmv_ibge.py`

1. `filter_rows_by_ibge` — match `cod_ibge` 6↔7 dígitos (`310.620` ≡ `3106200`)  
2. `consolidate_habitacao_estoque` → bloco JSON:

```json
"habitacao": {
  "status": "ok",
  "cod_ibge": "5300108",
  "fonte": "MCMV — Ministério das Cidades",
  "n_empreendimentos": 12,
  "unidades_total": 4500,
  "unidades_entregues": 1200,
  "proxy_para_ipm": 1200,
  "nota": "Proxy de adensamento — não é saldo migratório demográfico"
}
```

3. `withIntersecao(ficha)` lê `habitacao.proxy_para_ipm` se `saldo_migratorio` ausente → `migracao_fonte=mcmv_proxy`.

**Calibração:** thresholds IPM (1500/500) foram pensados em **pessoas**. Com UH MCMV, tratar faixas como **provisórias** até recalibrar por município.

---

## 4. Contrato do agente redator / blog

Todo post que use IPM (ou a matriz) **deve responder**:

1. População do recorte **cresce, estável ou encolhe?** *(migração / proxy)*  
2. Mercado **absorve aberturas sem quebrar veteranos?** *(mortalidade × abertura)*  
3. **Onde está a janela real?** *(quadrante A/B/C/D + IPM se calculável)*

### Template MD (bloco opcional)

```markdown
## Interseção oferta × demanda

| Eixo | Sinal | Evidência |
| --- | --- | --- |
| Migração | + / ~ / − / ? | … |
| Abertura | alta / baixa | N entrantes · taxa entrada X% |
| Mortalidade | alta / baixa | churn Y% · % ≥5 anos |

**Quadrante:** A | B | C | D (ou parcial se migração `?`)  
**IPM:** valor | n/d (sem saldo migratório)
```

---

## 5. Exemplo — Brasília Q1 2026 (parcial)

Dados disponíveis (ficha `brasilia-df.json` + PDAD renda):

| Eixo | Valor | Classificação provisória |
| --- | --- | --- |
| Mortalidade | churn **2,67%** · 17 baixas · **52,9% ≥ 5 anos** | **Alta** (+ saída madura) |
| Abertura | 31 entrantes · entrada **4,87%** · razão 1,8 abert./baixa | **Alta** |
| Migração | densidade 4.818→4.712 (parque ↑) · **sem saldo migratório por RA** | **`?` unknown** |

**Leitura:** eixo horizontal = mortalidade alta + abertura alta → candidato a **C (ilusionismo)** *se* imigração alta, ou **D** *se* população estagna/encolhe.  
**Sem migração por RA, IPM não fecha.** Próximo dado: PDAD tempo de residência / habite-se DF / proxy energia.

Clusters n≥2 (Asa Norte vs Samambaia) já mostram **dois mercados de renda**; IPM futuro deve ser **por RA**, não só DF agregado.

---

## Changelog

- 2026-08-04 — Spec inicial (matriz A–D, fórmula IPM, contrato blog, case Brasília parcial).
