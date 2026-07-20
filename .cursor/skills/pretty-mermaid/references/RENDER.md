# Render SVG / ASCII (beautiful-mermaid)

Use only when user asks for SVG, ASCII, theme batch, or file export. Day-to-day GymSite = MermaidChart Preview on `.mmd`.

## Single

```bash
node scripts/render.mjs \
  --input diagram.mmd \
  --output diagram.svg \
  --format svg \
  --theme tokyo-night
```

ASCII:

```bash
node scripts/render.mjs --input diagram.mmd --format ascii --use-ascii
```

## Batch

```bash
node scripts/batch.mjs \
  --input-dir ./diagrams \
  --output-dir ./rendered \
  --format svg \
  --theme tokyo-night \
  --workers 4
```

## Themes

```bash
node scripts/themes.mjs
```

Dark: `tokyo-night`, `github-dark`, `dracula`, `nord`.  
Light: `github-light`, `zinc-light`, `catppuccin-latte`.

Custom:

```bash
node scripts/render.mjs --input d.mmd --bg "#1a1b26" --fg "#a9b1d6" --accent "#7aa2f7" --output c.svg
node scripts/render.mjs --input d.mmd --transparent --output t.svg
```

## Decision tree

1. Author/update flow → write `.mmd` (SKILL.md) → Preview.
2. Need SVG for docs → `render.mjs` + theme.
3. Need README plain → ASCII.
4. Many files → `batch.mjs`.

## Troubleshoot

| Error | Fix |
|---|---|
| `Cannot find module 'beautiful-mermaid'` | `npm install` in skill dir that vendors scripts |
| Parse error | validate vs SHAPES.md; test mermaid.live |
| File not found | absolute path |

Scripts live under this skill’s `scripts/` when vendored; if missing, Preview-only is enough for GymSite.
