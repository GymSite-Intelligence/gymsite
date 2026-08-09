# Design — Voronoi smoke (medir antes de ligar)

**Data:** 2026-08-07  
**Âmbito:** Comparar pool Absorção (bairro/polígono) vs pool na **célula Voronoi** da unidade proposta — sem mudar rótulo fresco/roubo nem veredito  
**Humano:** Marcelo  
**Abordagem:** Smoke dual (clássico + ponderado no JSON); nota curta no PDF/app só com clássico  
**Depende de:** Absorção W2a + pool etário; Spec C polígono + `censo_setor` (lat/lng); concorrentes com coords  
**Pai:** `docs/superpowers/specs/2026-08-07-absorcao-margem-fresca-design.md` §4 W2.1

---

## 1. Problema (produto)

Absorção hoje usa **todo** o polígono do bairro (ou raio) como pool. Onde já há várias academias, parte da população “pertence” mais perto do concorrente — o pool do bairro **superestima** aluno fresco.

Queremos **medir** essa diferença antes de ligar Voronoi no veredito.

---

## 2. Decisões aprovadas

| # | Escolha |
|---|---|
| Modo | **C** — medir antes de ligar (não muda rótulo / Oceano / TRANSICAO) |
| UI | **2** — nota curta PDF + card React; sem seção comparativo completa |
| Variantes | **C** — clássico + ponderado no JSON; **nota usa só clássico** |
| Pool smoke | Escalar `pool_primario` atual × (`pop_célula` / `pop_bairro`) |
| `base_espacial` | Continua `poligono_ibge` \| `raio_fallback` — **não** grava `voronoi` ainda |

---

## 3. Meta / fora

### Meta

1. `tools/voronoi_atratividade.py` — células clássica e ponderada (peso ∝ `area_proxy_*` do tier), clip no ring do bairro.
2. Pop na célula = soma `censo_setor.pessoas` cujo centróide cai na célula da **unidade proposta**.
3. Anexar `voronoi_smoke` em `absorcao_margem_fresca` no attach A9 (após pool atual).
4. PDF + card: uma nota vernáculo com potencial Voronoi clássico e % vs bairro.
5. Falhas → `status=indisponivel` (sem nota), Absorção atual intacta.

### Fora (esta wave)

| Item | Destino |
|---|---|
| Mudar `rotulo` / veto Oceano com base Voronoi | Wave “ligar” depois do smoke |
| `base_espacial=voronoi` / `voronoi_ponderado` | Idem |
| “Melhor score fica” (auto-escolha polígono vs Voronoi) | Pós-smoke, métrica a fechar |
| Reagregar pirâmide idade×sexo só na célula | Feito (abordagem 2) — `metodo_pool=piramide_celula`; escala = fallback |
| Mapa Voronoi no PDF | Fora |
| Trocar `capacidade_parque` pelo mix só na célula | Fora (modo B rejeitado) |

---

## 4. Fluxo

```
candidato (lat,lng) + concorrentes (lat,lng)
        │
        ├─ <2 pontos úteis ou sem ring → status=indisponivel
        │
        ▼
scipy Voronoi (clássico) + variante ponderada (peso area_proxy tier)
        │
        ▼
célula da unidade ∩ polígono bairro (shapely)
        │
        ▼
setores censo_setor_idade_sexo (bbox): centróide ∈ célula
        │
        ├─ pirâmide na célula → estoque_form × interesse × pen  (preferido)
        └─ sem colunas idade → escala pool_ref × pop_célula / pop_bairro
        │
        ▼
state absorcao_margem_fresca.voronoi_smoke = {...}
PDF/app: nota só se status=ok (números clássicos)
```

---

## 5. Contrato `voronoi_smoke`

```python
{
  "status": "ok" | "indisponivel",
  "motivo": str | None,  # ex. sem_coords | sem_poligono | poucos_pontos | sem_setores
  "pop_bairro": int,
  "pop_celula": int,
  "pop_celula_ponderada": int | None,
  "pool_ref": int,                 # = pool_primario atual
  "pool_voronoi": int | None,      # clássico (pirâmide ou escala)
  "pool_voronoi_ponderado": int | None,
  "delta_pct": float | None,       # (pool_voronoi - pool_ref) / pool_ref
  "n_sites": int,                  # pontos no diagrama
  "n_setores_celula": int | None,
  "peso_candidato": float | None,  # area_proxy do modelo da unidade
  "metodo_pool": "piramide_celula" | "escala_pop" | None,
  "estoque_primario_celula": int | None,  # só se pirâmide
  "carimbo": str,                  # valor · base · fonte · janela
}
```

Rótulo Absorção, margem, veto Oceano: **inalterados** nesta wave.

---

## 6. Copy (nota — vernáculo)

Exemplo (delta negativo típico):

> **Leitura espacial (experimental):** se usássemos a área de influência entre academias (Voronoi clássico), o potencial no público do formulário seria cerca de **X alunos** (**Y%** em relação ao bairro inteiro). O veredito fresco/roubo **ainda** usa o bairro. Medição interna — não muda a decisão nesta versão.

Proibido na nota: `pool`, `pen.`, IDs de param, `scipy`.

---

## 7. Waves

### W2.1a — Core smoke + attach

- Módulo + testes TDD (2 sites, clip, escala, indisponivel).
- Hook após `absorcao_margem_fresca` no attach (não falha o attach se Voronoi quebrar).
- Docs: PIPELINE + conferência uma linha.

### W2.1b — PDF + card React

- Nota no HTML builder + `AbsorcaoMargemFrescaCard`.
- Preview `gerar_html` + abrir browser; preview UI se mudar card.
- Teste HTML asserta “experimental” / “Voronoi” vernáculo + ausência de mudança de rótulo.

### W2.1c — (fora) Ligar / melhor score

- Só depois Marcelo ver deltas reais em praças piloto.

---

## 8. Critérios de aceite

1. Com fixture 2 academias + setores stub → `pool_voronoi` ≠ `pool_ref` (ou igual se pop igual) e `delta_pct` coerente.
2. Sem lat/lng candidato → `indisponivel`, Absorção igual ao pré-smoke.
3. `rotulo` e `veredito_posicionamento` idênticos com/sem smoke ok.
4. PDF/app: nota só se `status=ok`; copy sem jargão de engenharia.
5. Ponderado presente no JSON quando ok; nota **não** cita o número ponderado.
6. Docs atualizados na mesma PR.

---

## Self-review (2026-08-07)

- [x] Sem TBD crítico (escala pop; peso = area_proxy; clip = Spec C ring).
- [x] Sem contradição com Absorção/pool: smoke paralelo; `base_espacial` não vira voronoi.
- [x] Escopo W2.1a/b explícito; ligar/melhor-score/mapa fora.
- [x] Decisões C / 2 / C registradas.
- [x] Carimbo + vernáculo alinhados a `leitura-executiva-pdf.md`.
