# Design — Pool etário em duas camadas (Absorção)

**Data:** 2026-08-07  
**Âmbito:** Corrigir `pool_demografico` da Absorção: não tratar pop total nem 100% da faixa Core como “ativos”; usar estoque etário × interesse fitness × penetração academia; três bases no PDF (primário / secundário / total).  
**Humano:** Marcelo  
**Abordagem:** Patch em `tools/absorcao_margem_fresca.py` (abordagem 1)  
**Depende de:** Spec Absorção (`2026-08-07-absorcao-margem-fresca-design.md`) · Spec C pirâmide · params form `publico_fitness_idade_*` · `penetracao_potencial_fitness`  
**Nome:** Spec Pool Etário (extensão Absorção W2a.1 — não substitui Matriz)

---

## 1. Problema

Hoje Absorção W2a faz:

```
pool = pop_poligono × penetracao_(geral|bairro_ab)
```

Isso:
1. Ignora faixas etárias do formulário e da pirâmide PDF  
2. Sugere que “25–39 · Core = 18.420” seriam todos ativos — **falso** (Core = estoque IBGE, rótulo de faixa, não matrícula)  
3. Esconde população ativa **fora** do gancho do form (Jovem / Maduro / Silver), necessária pra escolher modelo

---

## 2. Meta / fora

### Meta

1. Duas camadas de taxa: `penetracao_potencial_fitness` (interesse) × penetração academia (`penetracao_geral` | `penetracao_bairro_ab`).  
2. Três pools: **primário** (faixas do formulário) · **secundário** (resto 15+) · **total** (primário+secundário).  
3. `margem_fresca` + rótulo `fresco|misto|roubo` calculados no **pool primário** vs `capacidade_parque`.  
4. Pool secundário = sinal de **modelo** (copy/carimbo), não decide fresco/roubo.  
5. Carimbo em cada número; PDF via `gerar_html` + abrir preview.

### Fora

| Item | Destino |
|---|---|
| Assumir 100% da faixa = aluno | Proibido |
| Voronoi | Spec Absorção W2.1 |
| Mudar regras de quadrante Matriz | Fora — só nota/carimbo Absorção→modelo |
| SOW / PoW | Fora |
| Recalcular A4 ticket só com pool etário | Spec depois |

---

## 3. Decisões travadas

| # | Escolha |
|---|---|
| Camadas | **C** — estoque × interesse × pen_academia |
| Estoque primário | Faixas do **formulário** (`publico_fitness_idade_min/max` / input_params) mapeadas nas faixas IBGE do PDF (15–24, 25–39, 40–59, 60+) |
| Estoque secundário | Soma faixas 15+ **não** cobertas pelo form |
| Rótulo Absorção | Só vs **pool_primario** |
| Secundário no PDF | Três linhas de pool + nota “informa modelo” |
| Core dominante | **Não** zera ativos nas outras faixas |
| Onde mora | Estender `absorcao_margem_fresca` + attach (pirâmide + idades form no state) |
| Fallback sem pirâmide | `pool_primario = pop_total × interesse × pen_acad` + carimbo `fallback_pop_total` |

### Mapeamento idade form → faixas IBGE

Faixas canônicas PDF: `15-24`, `25-39`, `40-59`, `60+`.

- Intervalo form `[idade_min, idade_max]` (default params 25–40) **intersecta** cada faixa; faixa entra no primário se interseção não vazia.  
- Default 25–40 → primário inclui **25–39** e **40–59** (40 na interseção).  
  - Se produto quiser **só Core** no form, setar max=39 no formulário.  
- Faixas 15+ sem interseção → secundário.

### Fórmula

```
interesse = param("penetracao_potencial_fitness")  # 0.40
pen_acad  = penetracao_bairro_ab se perfil A/B else penetracao_geral

estoque_primario   = sum(segmentos[f].total for f in faixas_form)
estoque_secundario = sum(segmentos[f].total for f in faixas_15mais - faixas_form)
estoque_total_15   = estoque_primario + estoque_secundario

pool_primario   = round(estoque_primario   * interesse * pen_acad)
pool_secundario = round(estoque_secundario * interesse * pen_acad)
pool_total      = round(estoque_total_15   * interesse * pen_acad)

# compat: pool_demografico = pool_primario (rótulo / margem)
margem_fresca = pool_primario - capacidade_parque_estimada
rótulo = fresco | misto | roubo  # mesma regra Absorção vs teto
```

### Exemplo (Cocó ilustrativo)

| Base | Estoque | ×0,40 ×0,10 (A/B) → pool |
|---|---|---|
| Primário form 25–40 ≈ 25–39+40–59 | 18.420+12.100 = 30.520 | ~1.221 |
| Secundário 15–24+60+ | 7.850+8.200 = 16.050 | ~642 |
| Total 15+ | 46.570 | ~1.863 |

(Números pirâmide do preview; carimbar fontes reais.)

---

## 4. Contrato state (delta Absorção)

Campos novos / renomeados em `absorcao_margem_fresca`:

```python
{
  # existentes…
  "pool_demografico": int,          # = pool_primario (compat)
  "pool_primario": int,
  "pool_secundario": int,
  "pool_total_15mais": int,
  "estoque_primario": int,
  "estoque_secundario": int,
  "faixas_primario": list[str],     # ex. ["25-39","40-59"]
  "faixas_secundario": list[str],
  "interesse_fitness": float,       # penetracao_potencial_fitness
  "penetracao_efetiva": float,      # pen academia
  "margem_fresca": int,             # pool_primario - cap
  "rotulo": "fresco"|"misto"|"roubo",
  "carimbos": { … },
  "nota_modelo_secundario": str,    # copy curta p/ PDF
}
```

---

## 5. PDF / preview

- Seção Absorção: linhas teto · cap parque · **pool primário** · pool secundário · pool total · margem · leitura.  
- Nota: Core/form = gancho; outras faixas ativas existem; secundário guia modelo (Jovem/Maduro/Silver), não fresco/roubo.  
- Preview = `gerar_html` + abrir browser (regra `preview-aprovacao.md`).

---

## 6. Waves

### W2a.1 — Fórmula + attach + testes
- Map form→faixas; três pools; rótulo no primário; golden Cocó-like.  
- Conferência §9.2 + PIPELINE uma linha.

### W2a.2 — PDF + preview `gerar_html`
- Tabela + nota; abrir browser.

### Fora desta spec
- `rotulo==roubo` derruba Oceano Azul (spec veredito — pedir se quiser na sequência).

---

## 7. Critérios de aceite

1. 18.420 Core **não** vira pool sem × interesse × pen_acad.  
2. Três pools no state e no PDF.  
3. Rótulo usa só `pool_primario`.  
4. Sem pirâmide → fallback + carimbo.  
5. Testes TDD; preview `gerar_html` aberto.

---

## Self-review (2026-08-07)

- [x] Sem TBD crítico (mapeamento 25–40 → 25–39+40–59 explícito).  
- [x] Consistente com Absorção (cap parque / teto iguais).  
- [x] Escopo W2a.1/2; Matriz/Voronoi/Oceano fora.  
- [x] Core ≠ exclusão de outras faixas — escrito.
