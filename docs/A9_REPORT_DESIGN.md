# A9 — Design do Relatório PDF (Skills + Identidade Visual)

Estrutura de design do relatório do agente A9 (estrategista de posicionamento),
ancorada na identidade visual real do projeto: a paleta do PDF (`pdf/theme.py`),
a paleta do site (`frontend/src/index.css`) e os assets de marca.

## Fonte da identidade visual

- PDF (ReportLab): `pdf/theme.py` — paleta em HEX, fontes Helvetica/Helvetica-Bold,
  builder server-side em `pdf/builder.py` + `pdf/charts.py` + `pdf/models.py`.
- Site (Tailwind): `frontend/src/index.css` — tema escuro
  "corporate authority" em oklch, fontes DM Sans / IBM Plex Mono.
- Assets (logo de marca: pino de mapa em trilhas de circuito, metade
  verde-limão / metade grafite, e heatmap do Brasil). Os arquivos NÃO estão
  versionados no repo; o builder os resolve em runtime via
  `pdf.builder._logo_path()` / `_heatmap_path()`, nesta ordem: variável de
  ambiente (`GYMSITE_PDF_LOGO` / `GYMSITE_PDF_HEATMAP`), depois `pdf/assets/`
  (`logo-gymsite.png` / `brazil-heatmap.jpg`), depois
  `frontend/src/assets/`. Se nenhum existir, a imagem é omitida sem quebrar o PDF.

## Paleta de cores (referência das cores do site)

Cores já definidas no PDF (`theme.py`):

| Token | HEX | Uso |
|-------|-----|-----|
| NAVY | #1B2A4A | títulos, faixas de capa |
| CHARCOAL | #0F172A | grafite escuro (texto forte, metade do logo) |
| TEAL | #0D9488 | destaque/acento |
| TEAL_LIGHT | #CCFBF1 | fundo de destaque suave |
| TEAL_DARK | #115E59 | acento escuro |
| ORANGE | #E8751A | call-outs / chamada de atenção |
| SLATE / MUTED | #64748B | texto secundário |
| TEXT | #1E293B | corpo de texto |
| BORDER | #E2E8F0 | linhas e divisórias |
| ROW_ALT | #F8FAFC | zebra de tabelas |
| CARD_BG | #F1F5F9 | fundo de cartões |

Cores semânticas e de veredito (`theme.py`):

| Token | HEX | Uso |
|-------|-----|-----|
| SUCCESS / APROVADO | #16A34A | veredito positivo |
| WARNING / APROVADO COM RESSALVAS | #CA8A04 | atenção |
| INVESTIGAR MAIS | #EA580C | revisar |
| DANGER / REPROVADO | #DC2626 | risco/reprovação |

Cor de marca do logo (do site, já registrada em `theme.py`):

- LIME (primário do site): oklch(0.88 0.22 135) — verde-limão da marca;
  aproximação HEX para o PDF: cerca de #A3E635 / #9ACD32.
- LIME_GLOW: oklch(0.92 0.2 130) — variação clara para realces.
- PETROLEUM: oklch(0.42 0.08 210) e PETROLEUM_DEEP: oklch(0.22 0.04 215) —
  azul-petróleo, alinhado ao NAVY/TEAL do PDF.

Implementado: LIME (`#A3E635`), LIME_GLOW (`#BEF264`), PETROLEUM (`#0E5C66`) e
PETROLEUM_DEEP (`#08323A`) já estão em `theme.py`, então o PDF usa o mesmo
verde-limão da marca como acento (a capa e o rodapé já consomem essas cores).

## Tipografia

- PDF: Helvetica / Helvetica-Bold (padrão ReportLab, já em uso).
- Site: DM Sans (texto) / IBM Plex Mono (mono). Se quiser fidelidade total,
  embutir DM Sans como TTF no ReportLab; caso contrário, manter Helvetica como
  fallback corporativo (atual).

## Uso dos assets no relatório

Status: já implementado em `pdf/builder.py` (resolução defensiva dos assets).

- logo-gymsite.png: topo/rodapé de cada página (`_header_footer`) ao lado do
  nome da marca, e centralizado na capa (`_cover_block`).
- Capa: fundo grafite/petróleo (CHARCOAL/PETROLEUM_DEEP) com o logo centralizado
  e o verde-limão (LIME) como faixa de acento — espelhando o split do logo.
- brazil-heatmap.jpg: imagem de contexto na abertura da seção de mercado
  (`_market_section`), com legenda. Se o asset não existir, é omitida.

## Estrutura de seções do PDF (preenchida pelas skills do A9)

1. Capa — logo, título do estudo, praça/bairro analisado, data e selo de
   veredito (cor de VEREDITO_COLORS).
2. Sumário executivo — veredito de posicionamento + 3-5 bullets de decisão.
3. Mercado e localização — demografia/renda do bairro (A2) + heatmap.
4. Concorrência — mapa e tabela de concorrentes (A3/A3c), saturação e gap.
5. Financeiro — 3 cenários (Econômico / Padrão / Premium, de MODELO_LABEL),
   payback, ponto de equilíbrio, alertas (A4/A6).
6. Posicionamento (núcleo do A9) — arquétipo recomendado e headroom de renda.
7. Go-to-market / Marketing — ICP local, canais, proposta de valor.
8. Recomendações e próximos passos — ações priorizadas.

## Mapeamento skills -> seção -> cor

- Skill consultor de academias -> seções 2, 6, 8 -> NAVY/CHARCOAL + LIME (acento).
- Skill marketing/GTM -> seção 7 -> TEAL/PETROLEUM + ORANGE (call-outs).
- Skill interpretação financeira -> seção 5 -> tabelas com ROW_ALT/CARD_BG e
  cores semânticas (SUCCESS/WARNING/DANGER) por cenário e por alerta.
- Skill report-builder (PDF contract) -> todas -> consome `pdf/models.py` e
  monta as seções em `pdf/builder.py`/`charts.py`.

## Princípios de design

- Tema claro no miolo do relatório (fundo branco, texto TEXT) para impressão;
  capa e dividers em tema escuro (CHARCOAL/PETROLEUM) para impacto de marca.
- Verde-limão (LIME) usado com parcimônia, só como acento/realce — nunca em
  blocos grandes de texto, para preservar legibilidade.
- Gráficos (charts.py) seguindo chart-1..chart-5 do site para consistência.
