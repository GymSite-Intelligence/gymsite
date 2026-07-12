---
name: react-tanstack
description: Guias procedimentais para React 18, Vite, TanStack Router e Query. Use para lidar com rotas, chamadas de API, paginação e mutações de estados no frontend.
---

# ⚛️ React & TanStack Performance

Evite gerar lógicas pesadas de estado local para dados assíncronos. Utilize as ferramentas corretas instaladas no projeto.

## 🔄 Diretrizes Procedimentais
* **Busca de Dados:** Use `@tanstack/react-query` para gerenciar o cache da API. Sempre invalide o cache após mutações (Ex: após gerar um novo relatório de viabilidade).
* **Roteamento:** `@tanstack/react-router` para controle de páginas. Garanta tipagem estrita nos parâmetros de busca de URLs.
* **Tabelas de Oportunidades:** Use `@tanstack/react-table` estruturado com componentes customizados do `shadcn`.
* **Proibições:** Proibido usar `alert()`. Notificações devem ser disparadas via `sonner`.