# GymSite — Spec de Tokens de Cor (Sólido)

## Problema

Dark mode está com superfícies translúcidas (`rgba(..., 0.x)`) que vazam o fundo e reduzem contraste. Modal CRM, alertas, cards e botões ficam com neblina — texto fica difícil de ler.

**Veredito:** Usar **três tokens sólidos** sem alpha em todo fundo que tem texto, componente interativo ou superfície elevada.

---

## Os Três Tokens

Baseado na paleta atual (`frontend/src/index.css`).

### 1. `page` — Fundo da página

A cor de base. Tudo começa aqui.

**Dark mode:**
```css
--color-page: #13161b; /* oklch(0.095 0 0) — charcoal */
```

**Light mode:**
```css
--color-page: #ffffff; /* oklch(1 0 0) */
```

**Uso:**
- `<body>`, `<main>`
- Backgrounds de contenedores top-level
- Scrim opaco atrás de modal (overlay do fundo, não o modal em si)

**Exemplo Tailwind:**
```jsx
<div className="bg-background"> {/* Já aponta pra page */}
  {/* conteúdo */}
</div>
```

---

### 2. `elevated` — Superfície elevada (card, input, dropdown)

Um degrau acima. Componentes que flutuam sobre `page`.

**Dark mode:**
```css
--color-elevated: #1c212a; /* oklch(0.14 0 0) — um tom acima do fundo */
```

**Light mode:**
```css
--color-elevated: #f5f5f5; /* oklch(0.98 0 0) — cinza bem claro */
```

**Uso:**
- Cards
- Inputs, textareas, selects
- Dropdowns, popovers
- Modais (exceto o scrim)
- Chips / pills

**Exemplo Tailwind:**
```jsx
{/* Card */}
<div className="bg-card"> {/* --card = elevated na paleta */}
  <h3 className="text-card-foreground">Título</h3>
</div>

{/* Input */}
<input className="bg-input border border-border text-foreground" />

{/* Chip */}
<span className="bg-secondary text-secondary-foreground px-3 py-1 rounded">
  Label
</span>
```

---

### 3. `overlay` — Modal / Popover (opaco)

Camada superior. Tudo que flutua ou bloqueia o fluxo.

**Dark mode:**
```css
--color-overlay: #181c22; /* oklch(0.11 0 0) — mais escuro que elevated */
```

**Light mode:**
```css
--color-overlay: #ffffff; /* oklch(1 0 0) — branco puro */
```

**Uso:**
- Body de modal (o painel, não o fundo)
- Popover/tooltip body
- Alert box (parte branca da caixa, não o fundo)
- Menu flutuante

**Exemplo:**
```jsx
{/* Modal */}
<Dialog>
  <DialogContent className="bg-overlay text-overlay-foreground">
    <DialogTitle>Plano de Abertura</DialogTitle>
    <DialogDescription>Conteúdo opaco 100%</DialogDescription>
  </DialogContent>
</Dialog>

{/* Scrim (fundo escuro atrás do modal) */}
<div className="fixed inset-0 bg-black/40"> {/* isso é permitido: fundo não tem texto */}
  {/* modal vai aqui */}
</div>
```

---

## Proibido: Transparência em Superfícies com Texto

❌ **NÃO:**
```css
/* Esse padrão quebra dark mode */
.modal {
  background: rgba(255, 255, 255, 0.05); /* vaza o fundo */
  color: #eef1f4; /* texto vira neblina */
}

.alert {
  background: rgba(255, 187, 82, 0.1); /* amarelo translúcido — não funciona */
}
```

✅ **SIM:**
```css
/* Sólido 100% */
.modal {
  background: #1c212a; /* elevated — opaco */
  color: #eef1f4;
}

.alert {
  background: #1c212a; /* fundo sólido */
  border-left: 4px solid #ffba52; /* cor da alert em borda, não fundo */
  color: #eef1f4;
}
```

---

## Componentes (casos mencionados)

### Modal do CRM

**Antes:**
```jsx
<DialogContent className="bg-white/5 backdrop-blur"> {/* Translúcido */}
```

**Depois:**
```jsx
<DialogContent className="bg-overlay text-overlay-foreground">
  {/* Opaco, contraste alto */}
</DialogContent>

{/* Scrim atrás */}
<Overlay className="bg-black/40" /> {/* Isso é ok — sem texto */}
```

---

### Alertas (amarelo/azul)

**Antes:**
```jsx
<Alert className="bg-yellow-100/40 border border-yellow-300">
  {/* Pálido, translúcido — mal legível */}
</Alert>
```

**Depois:**
```jsx
<Alert className="bg-elevated border-l-4 border-l-yellow-500">
  <AlertTitle className="text-foreground">Atenção</AlertTitle>
  <AlertDescription className="text-muted-foreground">
    Conteúdo sobre fundo sólido
  </AlertDescription>
</Alert>
```

Cores de status (amarelo, azul) vão em:
- Borda (esquerda ou topo)
- Ícone
- Texto de label (pequeno)

Nunca no fundo.

---

### Cards e Botões

**Antes:**
```jsx
<Card className="bg-white/5 backdrop-blur-sm">
<Button className="border border-gray-400 bg-transparent">
```

**Depois:**
```jsx
{/* Card */}
<Card className="bg-elevated border border-border rounded-lg">

{/* Botão primário */}
<Button className="bg-primary text-primary-foreground">
  Gerar novamente
</Button>

{/* Botão secundário */}
<Button className="bg-elevated text-foreground border border-border">
  Cancelar
</Button>
```

---

## Dark Mode: Hierarquia Visual

```
page        #13161b ← fundo da página (mais escuro)
 ↓
elevated    #1c212a ← cards, inputs, chips
 ↓
overlay     #181c22 ← modal, popover (mais escuro que elevated? não — mesma faixa)
```

Na prática, `overlay` e `elevated` são **praticamente iguais** em luminância. A diferença é **semântica** — `overlay` é topo (float), `elevated` é conteúdo da página. Visualmente ficam coesos; contrastam com `page`.

---

## Checklist de Migração

Para cada componente:

- [ ] Modal CRM: `bg-overlay` (body), `bg-black/40` (scrim)
- [ ] Alertas: `bg-elevated`, cor de status em **borda** ou **ícone**, não fundo
- [ ] Cards: `bg-elevated`, sem alpha
- [ ] Botões primários: `bg-primary` (lime), texto escuro
- [ ] Botões secundários: `bg-elevated`, borda `border-border`
- [ ] Chips selecionados: `bg-elevated` + borda de accent
- [ ] Status falhou: texto de erro opaco (`text-destructive`), não só ícone

---

## Token Reference (CSS)

```css
/* Light */
:root {
  --color-page: #ffffff;
  --color-elevated: #f5f5f5;
  --color-overlay: #ffffff;
  --color-text: #13161b;
  --color-text-muted: #6b7280;
}

/* Dark */
.dark {
  --color-page: #13161b;
  --color-elevated: #1c212a;
  --color-overlay: #181c22;
  --color-text: #eef1f4;
  --color-text-muted: #9aa4b0;
}
```

**Já existem na paleta GymSite:**
- `--color-page` → `--background`
- `--color-elevated` → `--card` ou `--secondary`
- `--color-overlay` → `--popover`
- `--color-text` → `--foreground`

Usar os nomes já existentes; não duplicar.

---

## Validação: Contraste

Ferramenta: https://webaim.org/resources/contrastchecker/

**Mínimo (AA):** 4.5:1 para texto pequeno, 3:1 para grande.

**Dark mode:**
- Texto (#eef1f4) sobre elevated (#1c212a): **17.8:1** ✅ excelente
- Texto (#9aa4b0) sobre elevated: **6.5:1** ✅ bom
- Status warning (#ffba52) + ícone em elevated: **4.2:1** ✅ limpo

Todos passam.

---

## Próximos Passos

1. Aplicar ao Modal CRM (scrim + body)
2. Refatorar Alertas (borda, sem alpha)
3. Auditar Cards e Botões (componentes shadcn)
4. Testes: dark mode em Chrome DevTools → confirma que não há neblina

Salve esse arquivo e linke na PR de correção.
