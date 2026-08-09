# Design — Explorar no mapa (`/explorar`)

**Data:** 2026-08-07  
**Âmbito:** Entrada didática mapa-first (paridade UX OndeAbrir) · motor GymSite (Absorção / Maps / carimbo) — **sem** score 0–10 deles  
**Humano:** Marcelo  
**Depende de:** Absorção + pool etário; SearchAPI/Maps concorrentes; Spec C polígono (quando UF tiver gpkg); VEC-378 isócronas reais (ORS/Valhalla)  
**Pai conversa:** clone UI OndeAbrir · auditoria PDF Bessa/Cocó · Voronoi smoke

---

## 1. Problema (produto)

App GymSite hoje é **forte no motor, pesado na entrada**. OndeAbrir ganha em didática: mapa full-bleed → endereço → lente espacial → Analisar → PDF.

Queremos a **mesma clareza de entrada**, sem copiar a metodologia otimista (score inflado, raio misturado, “poucos concorrentes” com 6 rivais a &lt;500 m).

---

## 2. Decisões travadas (desta conversa)

| # | Escolha |
|---|---|
| Superfície | Nova rota mapa-first — **não** redesenhar Consultor inteiro nesta wave |
| Acesso | **Mesmo path** `www.gymsite.com.br/explorar`: anônimo = 1 pesquisa/e-mail + Turnstile; logado = full. Chat especialistas = `/degustacao`. Sem `/degustacao/explorar`. |
| Vertical | Dropdown do form: **Academia · Studio · Crossfit · Pilates** (`tipo_negocio` + gate Maps) |
| Veredito | **Absorção** (fresco / misto / roubo) + carimbos — **proibido** score 0–10 estilo OndeAbrir |
| Mapa base | OSM/CARTO (ou equivalente barato) + atribuição ODbL |
| Tema mapa | **Os dois** (claro + escuro) sempre no toggle; **usuário define** · persiste `localStorage` (`explorar-map-style`) · 1ª visita fallback claro (didático, não lock de marca) · Satélite também no segmented |
| Chrome UI | Painéis flutuantes (Controles, busca, barra, resultados) = paleta **site** carvão+lime (`GYMSITE_PALETTE`, opaca) · **não** herdam tema claro/escuro/geo do app nem o tile OSM |
| Camadas | **Mesma UI OndeAbrir:** `Mapa de calor` **e** `Área de influência` (ambos opção selecionável) · sob influência: toggle **a pé \| carro** · Legenda `Google Maps (N)` |
| Concorrentes no mapa | Pins **SearchAPI/Google Maps** (lat/lng reais) — legenda com N (sempre on; não é toggle de camada no print) |
| Lente espacial W1 | Pills barra inferior: **500 m · 1 km · polígono bairro (IBGE)** quando disponível |
| Isócrona / influência | **Visual = OndeAbrir:** 3 polígonos 5 / 10 / 15 min (verde · amarelo · laranja, borda tracejada) + legenda canto inf. esquerdo · a pé/carro muda o recorte · círculo azul da **lente** (500 m / 1 km / bairro) convive por cima · **real:** ORS (`ORS_API_KEY`) ou Valhalla OSM.de — sem polígono mock |
| Heatmap | UI W1 (toggle); dados demográficos W2/W3 — se off/on sem dados, estado vazio ou “em breve”, sem inventar calor falso |
| Aluguel / financeiro | Não inventar faixa R$ 35–65; se mostrar, **MRLR** ou omitir na degustação |
| PDF | Opcional W2 — resumido com mesmos números do JSON (fonte única) |

---

## 3. Experiência (1 composição)

### Viewport 1 — mapa

- Mapa edge-to-edge (default tema: validar preview; candidatos claro didático vs escuro marca)
- Busca endereço → **autocomplete Places ao digitar** → geocode → **pin candidato**
- Barra inferior:
  - Tipo: dropdown Academia / Studio / Crossfit / Pilates (mesmo enum do formulário)
  - Lente: `500m` \| `1km` \| `Bairro` (IBGE)
  - CTA **Analisar** (ativo só com pin)
- Degustação: mesmo fluxo visual; após N análises / gate e-mail — espelhar regras atuais do site (não afrouxar)

### Painel flutuante **Controles** (layout = OndeAbrir — travado)

Estrutura **exata** (3 blocos, nesta ordem):

1. **ESTILO DO MAPA** — segmented 3: `Claro` \| `Escuro` \| `Satélite` (um ativo)
2. **CAMADAS** — lista selecionável (radio/highlight de linha, não só checkbox solto):
   - `Mapa de calor` — opção sempre visível
   - `Área de influência` — opção sempre visível; **quando ativa**, sub-controle indentado logo abaixo:
     - segmented 2 ícones: **a pé** \| **carro** (um ativo)
3. **LEGENDA** — ponto vermelho + texto `Google Maps (N)` (N = rivais no recorte)

**Regras UI**

- Manter **os dois** (`Mapa de calor` e `Área de influência`) como opções — não remover calor do menu
- Só um estilo de mapa ativo por vez
- Sub a pé/carro **só aparece** com `Área de influência` selecionada (igual print)
- Tokens GymSite (lime) no selected state — estrutura idêntica, cor de marca nossa
- Preview de referência: `docs/superpowers/previews/2026-08-07-explorar-w1.html` + print OndeAbrir anexado na conversa

### Camada **Área de influência** (desenho no mapa = OndeAbrir)

Dois overlays **juntos** (não ou/ou):

1. **Isócronas 5 / 10 / 15 min** — 3 anéis irregulares (não círculo), fill semitransparente, borda tracejada  
   - 5 min = verde · 10 min = amarelo/tan · 15 min = laranja/pêssego  
   - Toggle **a pé** vs **carro** troca o tamanho/forma do recorte (mesmo job que OndeAbrir)  
   - Legenda flutuante inf. esquerdo: quadrados de cor + `5 min` / `10 min` / `15 min`  
2. **Círculo da lente** — azul, regular, vem da barra inferior (`500 m` / `1 km` / anel bairro) — base da Absorção, não do tempo

`Mapa de calor` on → esconde isócronas + legenda de tempo (pins Maps ficam).

**Proibido:** vender o mock W1 como tempo real de rua. Label honesto no produto até ORS (W2). Visual, porém, já é o de 3 faixas — **não** só um círculo teal.

### Após Analisar — painel lateral (não dashboard)

Ordem didática (1 job por bloco):

1. **Quem ainda pode matricular** — card Absorção (rótulo + 5 blocos já aprovados; Voronoi card 6 só se `status=ok`)
2. **Concorrentes no recorte** — lista curta nome · dist · rating (mesmo N dos pins)
3. **Base espacial** — uma linha: “números desta análise: polígono Cocó / raio 1 km · IBGE · …”
4. CTA secundário: abrir relatório completo / Consultor

**Proibido no painel:** score composto 0–10 · “oportunidade clara” genérico · aluguel heurístico · POF como se fosse alunos.

---

## 4. Fluxo de dados

```
endereço
  → geocode (Nominatim / IBGE centróide; SearchAPI só pins)
  → pin (lat,lng)
  → resolver bairro + ring Spec C (se UF/gpkg)
  → SearchAPI Maps academia no recorte (raio ou bbox ring)
  → demografia setores no recorte (idade×sexo se possível)
  → absorcao_margem_fresca (+ voronoi_smoke se coords + ring + ≥2 sites)
  → painel + (opcional) PDF do mesmo JSON
```

**Invariantes**

- Número exibido = tool/banco + **carimbo** (valor · base · fonte · janela)
- Aluguel viabilidade = MRLR (se entrar) — nunca SearchAPI listing price
- Contagem concorrentes = pin no recorte (tipo/status) — sem gate string bairro como filtro único
- Uma base por tela: se lente = bairro, todos os blocos usam bairro; se 1 km, todos 1 km — **não** misturar 500 m rivais + score 2 km

---

## 5. Três abordagens (escolhida)

| | Abordagem | Prós | Contras |
|---|---|---|---|
| A | Só landing marketing com mock | Rápido | Não gera lead real |
| B | **`/explorar` autenticado + degustação anônima com cap** (recomendada · **aprovada**) | Didático + motor real + aquisição | Escopo front+wire+gate |
| C | Substituir Consultor por mapa | UX limpa | Quebra fluxo conversacional |

**Escolha: B.**

---

## 6. Waves

### W1 — Clone didático + Absorção

- Rota `/explorar` (logado) + entrada degustação (cap/lead existente)
- Mapa OSM + pin + pills raio/bairro
- Painel **Controles** completo (estilo 3 + camadas calor/influência + legenda) — UI paridade print
- Estilo claro/escuro funcional; satélite se tile barato (senão botão disabled com tooltip)
- `Área de influência` on → **3 faixas 5/10/15 + círculo da lente** (isócrona real ORS/Valhalla; sem blob mock)
- `Mapa de calor` on → empty state / “em breve” até W2 (toggle permanece)
- Analisar → Absorção + pins Maps no recorte
- Sem PDF; sem score 0–10

### W2 — Paridade espacial OndeAbrir (honesta)

- Isócronas reais a pé/carro (VEC-378) — **feito no Explorar** (ORS/`ORS_API_KEY` ou Valhalla OSM.de)
- Heatmap demográfico ligado ao toggle
- PDF resumido (mesmo JSON)
- Geocode Nominatim + fallback

### W3 — Fora deste spec

- Voronoi “ligar” no veredito
- Bordas cross-bairro em produção
- 23 tipos de negócio

---

## 7. Copy / vernáculo

- Falar: alunos potenciais · academias no mapa · bairro / raio · disputa com o parque  
- Não falar: score 5.8 · pool · pen. · scipy · payload  

Checklist presencial (seção 06 OndeAbrir) = **inspiração** W2: gerar itens a partir do relatório (ex. “confirme aluguel vs teto MRLR”), não checklist genérico eterno.

---

## 8. Sucesso

- Usuário coloca pin e em &lt;30 s entende: **rótulo Absorção** + **quantas academias no mapa** + **qual base espacial**
- Mesmo endereço Cocó **não** vira “oportunidade clara” se Absorção = roubo
- Preview HTML ou rota local aprovada por Marcelo antes de merge

---

## 9. Aberto

Nada crítico no W1.

1. ~~Acesso~~ → **degustação + logado** (travado 2026-08-07)  
2. ~~Duas versões de mapa~~ → **claro + escuro**; usuário escolhe (travado 2026-08-08)  
3. ~~Camada influência~~ → **3 faixas 5/10/15 + círculo lente** (aprovado 2026-08-08)  
4. ~~Default tema~~ → **não forçar um só**; preferência do usuário neste aparelho (travado 2026-08-08)
5. ~~Chrome vs tema do app~~ → painéis flutuantes = paleta site (carvão+lime opaca); tile OSM continua escolha do usuário (travado 2026-08-08)

**Plano W1 aprovado 2026-08-08** (`docs/superpowers/plans/2026-08-07-explorar-mapa-w1.md`).

---

## 10. Self-review

- [x] Sem TBD crítico no W1 (desenho 5/10/15 no W1; ORS real W2; tema = usuário escolhe)
- [x] Sem misturar score OndeAbrir com Absorção
- [x] Carimbo / base única por lente
- [x] Degustação reusa cap existente (não funil paralelo)
- [x] Fora de escopo listado (W3)
