# Design — Spec C: polígono de bairro (IBGE + híbrido) unificando A2 e A3a

**Data:** 2026-08-06  
**Âmbito:** Uma régua espacial de bairro para demografia (A2) e concorrência Maps (A3a)  
**Humano:** Marcelo  
**Abordagem:** Um spec, **2 waves** (W1 IBGE + fallback; W2 tapa-buraco INDE/município)  
**Depende de:** Ops P0 W1 carimbos já no PDF (rótulo honesto); malha IBGE Censo 2022 bairros (FTP/gpkg); espelho `censo_setor` / `censo_setor_idade_sexo`  
**Pesquisa:** PDF *Da Malha Federal ao Bairro Local — Estratégia Híbrida…* (IBGE → INDE → municipal; CIB = nomes; Plano Diretor PDF ≠ primário)

**Nome:** Spec C = **este** documento. Não confundir com VEC-378 OSM (geocode Nominatim) nem com “sector intel” do Ops P0 — esses continuam specs separadas.

---

## 1. Problema (produto)

Hoje o relatório usa **três réguas** em volta do centróide:

| Métrica | Agente | Régua atual | Ex. Cocó |
|---|---|---|---|
| População / domicílios | A2 | Raio fixo **1,5 km** | ~105 setores · ~60 mil hab |
| Idade × sexo | A2 | Setores mais próximos até `pop_alvo` | ~183 setores |
| Concorrentes Maps | A3a | Raio canônico **1,0 km** | N no círculo |

Números não fecham (105 ≠ 183; soma faixas 15+ ≠ pop total). Zoneamento urbano (LUOS/KMZ) mostra polígonos de **zona especial**, não o contorno do bairro — “USO GERAL · Coco” cola o **nome** do bairro no fallback fora-de-zona.

Usuário quer: habitantes, faixa etária×sexo e concorrência na **mesma extensão** que se aproxima do bairro.

---

## 2. Meta / fora de escopo

### Meta

- Resolver polígono oficial (quando existir) e usá-lo em **A2 e A3a** na mesma entrega (decisão **B**).
- Gate Maps = **point-in-polygon** (decisão **1**).
- Sem polígono → **fallback** aos raios atuais + carimbo explícito.
- Cobertura: malha IBGE (~17,5k bairros; **não** 5.570 municípios; TO/DF tipicamente sem malha) + suplemento híbrido na W2.

### Fora (v1 / este spec)

| Item | Destino |
|---|---|
| Vetorizar Plano Diretor / PDF raster → polígono | Fora (caro, frágil; PDF pesquisa confirma) |
| CIB como provedor de geometria | Fora — só dicionário de nomes em wave futura opcional |
| OSM / Nominatim como fonte de polígono de bairro | VEC-378 = geocode; não malha bairro |
| Mudar contrato A0 (`market_context`) | A0 não produz pop/Maps; só contexto |
| Fila nacional de bundles / sector intel URLs | Spec depois (Ops P0 eixo A / residual) |
| Trocar zoneamento LUOS por polígono de bairro | Zoneamento continua só “academia pode abrir?” |
| Dual carimbo Maps (polígono **e** R=1000 obrigatório no PDF) | Fora W1 — um N canônico + fonte |

---

## 3. Decisões aprovadas

| # | Escolha |
|---|---|
| Empacotamento | Spec C, **2 waves** |
| Consumidores | **A2 + A3a** juntos (B) |
| Gate Maps | **Point-in-polygon** (1) |
| Fonte primária W1 | IBGE *Arquivo geoespacial de Bairros* Censo 2022 (gpkg/shp) |
| Fallback W1 | Sem match → pop `raio_m=1500`; Maps `RAIO_CONCORRENCIA_CANONICO_M=1000` |
| Híbrido | W2 = INDE/IDE estadual + portais municipais críticos (DF/TO + praças GymSite sem malha) |
| Agregação demografia | Setores cujo **centróide** cai **dentro** do polígono → mesma lista pra pop **e** pirâmide |
| Match nome | `id_municipio` + `bairro_norm` (mesmo espírito `renda_bairro` / `_norm_busca`); preferir `CD_BAIRRO` se disponível no espelho |
| Storage W1 | Espelho processável em runtime (Supabase geometria **ou** gpkg/arquivo versionado no batch — detalhe no plano; critério: A2/A3a não baixam FTP por relatório) |
| Rótulo produto | “polígono IBGE do bairro (Censo 2022)” — **nunca** “limite oficial da prefeitura” só porque veio IBGE |

---

## 4. Waves

### Wave 1 — IBGE + resolver + A2 + A3a + carimbos

**Ingest / espelho**

- Baixar malha bairros IBGE 2022 (Brasil ou por UF sob demanda do batch).
- Persistir atributos mínimos: `cd_bairro`, `nm_bairro`, `id_municipio`, geometria (WGS84), `as_of` / ano malha.
- Job de carga determinístico + teste de sanidade (CE contém Cocó/Coco; contagem ≈ ordem 17k).

**Resolver compartilhado** (ex. `tools/bairro_poligono.py` — nome final no plano)

- Input: `cidade`, `uf`, `bairro`, `id_municipio` (se já resolvido).
- Output: `{ polygon | None, cd_bairro, nm_bairro, fonte: "ibge_bairro" | None, area_km2? }`.
- Sem hit → `None` (não inventar polígono).

**A2 — demografia**

- Se polígono: agregar `censo_setor` / idade×sexo com centróide **dentro** do polígono → **um** `n_setores`, pop e segmentos da **mesma** lista.
- Remover (ou deixar só como fallback) o caminho “fill até `pop_alvo`” quando polígono ok.
- Se `None`: manter `demografia_setor_censo(..., raio_m=1500)` + perfil atual; carimbo `raio_fallback`.

**A3a — Maps**

- Com polígono: após recall SearchAPI, **inclusão** = point-in-polygon (lat/lng do place). Não usar R=1000 como gate de inclusão nesse caso.
- Sem polígono: manter `RAIO_CONCORRENCIA_CANONICO_M=1000` (conferência-fontes §9).
- Carimbo: `N · polígono IBGE bairro · SearchAPI` **ou** `N · raio 1000 m do centróide · SearchAPI`.

**PDF / front**

- Texto demografia alinhado a Ops P0: base rotulada; se polígono, citar polígono IBGE + `n_setores` único.
- Nota 105 vs 183 **some** quando ambas as bases forem polígono; permanece só no fallback / legado.

**Exemplo de uso:** relatório Cocó — mesma contagem de setores na pop e no quadro idade×sexo; academias só as com pin dentro do contorno IBGE do Cocó.

### Wave 2 — Híbrido tapa-buraco (INDE / municipal)

- Catálogo mínimo de adapters (DF, TO, e 1–N praças GymSite sem malha IBGE).
- Mesmo contrato do resolver: `fonte=inde_*|prefeitura_*`.
- Sem adapter → continua fallback raio.
- Preview + smoke por praça adicionada.

---

## 5. Aceite

### W1

- [ ] Cocó (ou golden CE): polígono match; `n_setores` pop == `n_setores` pirâmide
- [ ] Teste unitário: ponto dentro/fora do polígono; setor fora não entra na soma
- [ ] Teste A3a: place fora do polígono excluído mesmo com dist &lt; 1000 m; place dentro incluído mesmo se dist &gt; 1000 m (se recall trouxe)
- [ ] Sem polígono (município fictício / TO stub): fallback raio + carimbo `raio_fallback`
- [ ] PDF/preview: copy sem “população oficial do bairro” sem base; com polígono, carimbo IBGE
- [ ] `PIPELINE_AGENTES.md` + `conferencia-fontes-pipeline.md` atualizados (fonte A2/A3a)

### W2

- [ ] Pelo menos 1 adapter real (ex. DF **ou** DataRio/GeoSampa se priorizado) com teste de match
- [ ] Resolver escolhe IBGE antes de municipal quando ambos existem (prioridade explícita no código)

### Fora do “pronto Spec C”

- Cobertura 100% dos 5.570 municípios  
- CIB dicionário nacional  
- Paridade bit-a-bit com N Maps legado R=1000  

---

## 6. Ordem / dependências

1. **W1** — não bloqueia em VPS BR nem Ops P0 W3  
2. **W2** — depois W1 estável + lista de buracos reais do produto  

Ops P0 W3 (ingest RFB) e Spec C W1 podem rodar em paralelo.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Match nome falha (Cocó vs Coco) | `bairro_norm` + aliases; teste golden CE |
| IBGE aproxima bairro via setores (não = lei municipal) | Rótulo “IBGE Censo 2022”; não vender como prefeitura |
| N concorrentes muda vs relatórios antigos | Aceite consciente; carimbo novo; golden Cocó no preview |
| Recall SearchAPI ainda usa hint de bairro / bbox | Manter recall; só o **gate** de inclusão muda |
| Gpkg grande em runtime | Espelho filtrado por município / batch pré-carga |
| W2 explode em N adapters | Cap explícito: só buracos que geram relatório pago |

---

## 8. Referências

- IBGE Malhas — Arquivo geoespacial de Bairros (Censo 2022) · geoftp `.../censo_2022/bairros/`  
- `tools/censo_setor_tools.py` · `tools/perfil_sexo_idade_tools.py` · `tools/competitor_tools.py` (`RAIO_CONCORRENCIA_CANONICO_M`)  
- `tools/zoneamento_tools.py` — LUOS ≠ bairro  
- `.agent/rules/conferencia-fontes-pipeline.md` §9  
- `docs/arquitetura/PIPELINE_AGENTES.md`  
- `docs/superpowers/specs/2026-08-06-ops-p0-geocode-cub-carimbos-design.md`  
- PDF pesquisa híbrida (Downloads do usuário, 2026-08-06)  
- `.agent/rules/spec-self-review.md` · `.agent/rules/preview-aprovacao.md`

---

## Self-review

**Data:** 2026-08-06  
**Resultado:** ok (após checklist)

| Check | Achado |
|---|---|
| Placeholder | Nenhum TBD aberto; storage “Supabase **ou** arquivo” deixado ao plano de implementação (critério de aceite fixo: sem FTP por relatório) |
| Consistência | B + point-in-polygon + híbrido W1/W2 alinhados a §3–§4 |
| Escopo | 2 waves; fora explícito (Plano Diretor, CIB geom, A0, OSM bairro) |
| Ambiguidade | Spec C ≠ VEC-378 ≠ sector intel — nomeado em cabeçalho |
| Aceite | Checklist W1/W2 testável (§5) |
| Fora | §2 tabela |

Correções neste passo: esclarecer colisão de nome “C” com OSM no Ops P0 (apontar este arquivo como Spec C canônica de polígono).
