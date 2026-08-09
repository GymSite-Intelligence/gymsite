# Design — Absorção / Margem Fresca (capacidade × parque × pool)

**Data:** 2026-08-07  
**Âmbito:** Estimar se a unidade proposta cabe em **alunos frescos** do polígono ou precisa **roubar** do parque ativo, cruzando teto operacional (`matriculas_realista`) × capacidade instalada por tier × pool demográfico.  
**Humano:** Marcelo  
**Abordagem:** Ponte estudo→GymSite · Wave W2 (sinais determinísticos leves)  
**Depende de:** Spec Matriz (`2026-08-07-matriz-demo-saturacao-modelo-design.md`) · Spec C polígono · A4 `matr_m2_*` · A2 pop polígono  
**Estudo de referência:** *Da Demografia à Concorrência* (framework modelo / saturação / absorção) — SOV e qualidade percebida **fora** desta wave

**Nome:** Spec Absorção (não substitui Matriz; Matriz escolhe modelo; Absorção diz se há margem de alunos).

---

## 1. Problema (produto)

Hoje o relatório tem:
- `matriculas_realista` = área × `matr_m2_{modelo}_realista` (A4)
- `parque_ativo` ≈ contagem CNPJ / academias (cidade ou lista Maps)
- demografia / pop no polígono (A2 + Spec C)

**Falta** o elo do estudo: saturação = capacidade de **absorção** do mercado, não só N academias. Sem isso, não dá pra responder: “ainda tem aluno fresco no bairro ou o crescimento da unidade = roubar do parque?”

---

## 2. Meta / fora

### Meta

1. Função determinística `absorcao_margem_fresca(...)` → `teto_unidade`, `capacidade_parque_estimada`, `pool_demografico`, `margem_fresca`, rótulo `fresco|misto|roubo` + carimbos.
2. Mix Low/Mid/Premium via `contar_mix` / `classificar_tier_concorrente` (já na Matriz) — **não** reinventar tier.
3. Área proxy do concorrente **por tier** (benchmark franquia), não um único 1500 m² genérico.
4. PDF/UI: quadro curto (Demografia / Competitiva → Absorção → Quadro Modelo).
5. Quem monta: **A9** (junto Matriz); A4/PDF leem state.

### Fora (v1)

| Item | Destino |
|---|---|
| Share of wallet / SOW / PoW, churn aluguel 40% | Fora — sem fonte estável (estudo cita; GymSite não inventa) |
| m² real por concorrente (Maps) | Fora — proxy franquia |
| Alunos reais por CNPJ / POS | Fora |
| Qualidade / mystery shop | Fora (estudo cita; não há pipeline) |
| Canibalização rede própria | Spec depois |
| Inventar números no LLM | Proibido — só tool + `param()` |
| **Diagrama de Voronoi** (áreas de influência / Thiessen) | **Fora W2a** — ver §4 W2.1 e §7.1 |

---

## 3. Decisões travadas

| # | Escolha |
|---|---|
| Proxy capacidade parque | **B** — N × capacidade por tier do mix |
| `area_proxy_low_m2` | **1000** — Smart Fit mín. franquia ≥950 + Panobianco Padrão 900–1000 |
| `area_proxy_mid_m2` | **1500** — Ultra média ~1500 + Bluefit tip. / faixa útil |
| `area_proxy_premium_m2` | **2000** (placeholder calibrável; Bodytech/Cia — W2.1 se faltar evidência) |
| `area_proxy_nicho_desconhecido_m2` | **1250** — meio-termo low↔mid |
| Densidade matrículas | Reusar `matr_m2_{tier}_realista` de `parametros_metodologia` |
| Nicho / desconhecido | Contam com área 1250 × `matr_m2_mid_realista` |
| Base espacial | Mesmo conjunto PIP polígono Spec C que a Matriz (fallback raio + carimbo) |
| Pool | `pop_poligono × penetração` — `penetracao_bairro_ab` se perfil A/B; senão `penetracao_geral` (já existem) |
| Rótulos | `fresco` / `misto` / `roubo` (copy PT no PDF; ids EN no state) |
| Onde mora | `tools/absorcao_margem_fresca.py` — Matriz **não** embute a fórmula |
| Quem chama | A9 `attach_*` → state; PDF adapter lê |

### Fórmula

```
mix = contar_mix(concorrentes_poligono)   # low, mid, premium, nicho, desconhecido

cap_parque =
    mix.low     * area_proxy_low_m2     * matr_m2_low_realista
  + mix.mid     * area_proxy_mid_m2     * matr_m2_mid_realista
  + mix.premium * area_proxy_premium_m2 * matr_m2_premium_realista
  + (mix.nicho + mix.desconhecido)
                * area_proxy_nicho_desconhecido_m2
                * matr_m2_mid_realista

pool = pop_poligono * penetracao_efetiva

teto = area_candidato_m2 * matr_m2_{modelo_cenario}_realista
# modelo_cenario = modelo recomendado Matriz/A4 do cenário em análise

margem_fresca = pool - cap_parque

se margem_fresca >= teto     → fresco
se 0 < margem_fresca < teto  → misto
se margem_fresca <= 0        → roubo
```

### Exemplo numérico (ilustrativo)

Mid, unidade 1.500 m² → teto = 1500 × 1,4 = **2.100**.  
Parque: 4 Low + 2 Mid + 1 Premium →  
`4×1000×2,2 + 2×1500×1,4 + 1×2000×0,6` = 8.800 + 4.200 + 1.200 = **14.200**.  
Pool: pop × penetração (carimbo). Margem = pool − 14.200 → rótulo.

### Carimbo obrigatório (cada número)

| Campo | Exemplo de carimbo |
|---|---|
| `teto_unidade` | valor · área×matr/m² · ACAD/param · modelo |
| `capacidade_parque_estimada` | valor · N×tier×área_proxy×matr/m² · **proxy franquia** · não medido |
| `pool_demografico` | valor · pop×penetração · IBGE polígono + param penetração |
| `margem_fresca` | valor · pool−cap_parque · derivada |

Copy UI/PDF: linguagem de estudo (“margem de alunos frescos” / “absorção do parque”). Sem jargon interno (`SearchAPI`, `matriz_override`).

---

## 4. Waves

### W2a — Core determinístico + state + testes
- Params novos em `parametros_metodologia.py` (áreas proxy + fontes).
- `tools/absorcao_margem_fresca.py` + unit tests (fixture Cocó / mix sintético).
- A9 attach no mesmo passo da Matriz (bloco irmão no state).
- Conferência fontes: atualizar `.agent/rules/conferencia-fontes-pipeline.md` + `PIPELINE_AGENTES.md` § breve.

### W2b — PDF / app logado
- Seção Absorção no HTML PDF (após competitiva / antes ou junto Quadro Modelo).
- Card curto no detalhe do relatório (se já houver bloco Matriz).

### W2c — Calibração premium / penetração (opcional)
- Ajustar `area_proxy_premium_m2` com evidência Bodytech/Bio Ritmo.
- Revisar penetração só se auditoria mostrar bias sistemático.

### W2.1 / W3 — Voronoi (evolução espacial — **não** bloqueia W2a)

**Smoke (aprovado 2026-08-07):** ver `docs/superpowers/specs/2026-08-07-voronoi-smoke-design.md` — medir clássico+ponderado no JSON; nota PDF/app só clássico; **não** muda rótulo/veredito/`base_espacial`.

- Módulo `tools/voronoi_atratividade.py` (`scipy.spatial.Voronoi` / shapely).
- Ligar Voronoi no veredito / “melhor score fica” = wave **depois** do smoke.

---

## 5. Contratos (state)

```python
# state["absorcao_margem_fresca"]  (proposta)
{
  "teto_unidade": int,
  "modelo_teto": "low"|"mid"|"premium",
  "area_candidato_m2": float,
  "capacidade_parque_estimada": int,
  "mix": {"low": int, "mid": int, "premium": int, "nicho": int, "desconhecido": int},
  "pool_demografico": int,
  "penetracao_efetiva": float,
  "margem_fresca": int,
  "rotulo": "fresco"|"misto"|"roubo",
  "carimbos": { ... },  # valor · base · fonte · janela por métrica
  "area_proxy_usada": {"low": 1000, "mid": 1500, "premium": 2000, "nicho_desconhecido": 1250},
  # W2a: só poligono_ibge | raio_fallback
  # W2.1+: + voronoi | voronoi_ponderado
  "base_espacial": "poligono_ibge"|"raio_fallback"|"voronoi"|"voronoi_ponderado",
}
```

---

## 6. Riscos / mitigações

| Risco | Mitigação |
|---|---|
| Proxy área ≠ unidade real | Label **proxy**; params calibráveis; nunca apresentar como medido |
| Penetração nacional no polígono | Usar pair geral vs A/B já existente; carimbo |
| Double-count studio boutique vs full gym | Mix Matriz já classifica; nicho → 1250×mid |
| Parque cidade vs bairro | Só lista PIP polígono (Spec C) |
| Inflar cap_parque com 1500 em Low | Travado: Low = **1000** |

---

## 7. Ligação ao estudo (corroboração)

### 7.1 Estudo × SPEC — convergência

| Dimensão | Estudo (Oceano Azul → Deserto / Demografia→Concorrência) | SPEC Absorção 2026-08-07 | Lacuna / nota |
|---|---|---|---|
| Objetivo | 4 quadrantes → modelo ideal | Absorção quantitativa (fresco vs roubo do parque) | Complementares: Matriz = modelo; Absorção = margem de alunos |
| Oferta | Densidade, mix tier, saúde/fechamento | Mix tier × área_proxy × matr/m² | W2a simples; m² Maps / churn marca = fora |
| Demanda | Demo + renda; sugere SOW/PoW | `pool = pop × penetração` | SOW fora W2 (sem fonte) |
| Território | SIG / raio atratividade (ex. 2,5 km) | Spec C PIP polígono IBGE + fallback raio | **Voronoi não está no estudo nem em W2a** |

Estudo **não cita** Diagrama de Voronoi. Spec Absorção W2a também **não**. Voronoi = evolução GymSite (§4 W2.1): célula de influência × setores IBGE para não superestimar `pool` onde a pop está mais perto de outro concorrente; ponderação opcional por `area_proxy_*`.

GymSite: Matriz = quadrante/modelo; Absorção = **proxy quantitativo** de “ainda cabe aluno fresco?”.

---

## 8. Critérios de aceite

1. Teste: mix conhecido + área + pop → `cap_parque`, `teto`, `margem`, `rotulo` batem fórmula (golden).
2. Low usa 1000, Mid 1500, nicho/desc 1250 — assert nos testes de param.
3. Sem LLM inventando números; attach A9 só monta payload da tool.
4. PDF/UI mostra carimbo em teto, parque e pool.
5. Docs de fontes atualizados na mesma PR da W2a.
6. W2a: `base_espacial` ∈ {`poligono_ibge`,`raio_fallback`} apenas — **sem** código Voronoi.

---

## Self-review (2026-08-07)

- [x] Sem placeholders TBD críticos (premium 2000 marcado calibrável).
- [x] Sem contradição com Matriz (reusa mix; módulo separado).
- [x] Escopo W2a/b/c explícito; SOV fora; **Voronoi explícito em W2.1/W3**.
- [x] Números travados: 1000 / 1500 / 1250 / premium 2000 placeholder.
- [x] Tabela estudo×SPEC + smoke Voronoi só na wave espacial (melhor score fica).
