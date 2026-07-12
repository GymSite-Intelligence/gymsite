---
description: Diretrizes de paleta de cores, tokens de design e estilização para o ecossistema frontend.
globs: "src/frontend/**/*, apps/web/**/*, **/*.tsx, **/*.ts, **/*.css, **/*.scss"
alwaysApply: false
---

# 🎨 Diretrizes de Design & Paleta de Cores

Sempre utilize a paleta de cores oficial do projeto descrita abaixo. Evite usar cores "hardcoded" soltas (ex: `bg-[#1a1a1a]`) se houver um token correspondente no Tailwind ou CSS Variáveis.

## 🎨 Paleta de Cores Oficial
> Paleta canônica GymSite (tema escuro é o padrão). Definida em `frontend/src/index.css` (OKLCH) e exposta ao Tailwind v4 via `@theme inline`.

* **Primary (Cor Principal — LIME):** `#84cc01` (Ex: `bg-primary` / `text-primary`; sobre lime use texto escuro `#13161b`)
* **Secondary (Secundária):** `#1c212a`
* **Accent/Destaque:** `#84cc01`
* **Background (Fundo):** `#13161b`
* **Card:** `#181c22` (base) / `#1c212a` (elevado)
* **Text (Texto Principal):** `#eef1f4`
* **Muted (Texto Secundário):** `#9aa4b0`
* **Border (Bordas/Linhas):** `#2b323d`

## 📏 Regras de Aplicação
* Certifique-se de que o contraste entre a cor de texto e a cor de fundo atenda aos critérios de acessibilidade (WCAG AA).
* Ao criar novos componentes, consuma as cores preferencialmente através do arquivo de configuração do Tailwind (`tailwind.config.js`).