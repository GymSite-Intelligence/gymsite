# Processo de Mudança — Regra Mestra (alwaysApply)

> Adotada em 2026-06-10. Toda mudança de código, schema ou UX neste repositório segue esta regra.
> Origem: template de engenharia sênior fornecido pelo Marcelo. Seções de stack adaptadas à realidade do GymSite Intelligence (ver "Adaptação ao GymSite" no fim).

## Princípios Invioláveis

- **Linguagem do domínio, não do software** (P-001): UI fala na linguagem que o usuário fala no dia-a-dia — nunca "entidade", "registro", "submeter".
- **Mobile-first real** (P-002): tela primária é o celular do usuário no contexto real de uso. Web é versão adaptada para escritório.
- **Defaults inteligentes e auto-save** (P-003): o usuário não toca em "Salvar" durante construção de rascunho. Decisão consciente única: "Concluir" ou "Descartar".
- **Filtragem proativa** (P-004): mostrar somente itens elegíveis para a ação, em vez de mostrar tudo e alertar depois.
- **Validação no servidor** (P-005): cliente é cosmético. Toda regra de negócio é re-validada no backend.
- **Estado refletido na URL** (P-006): filtros, seleção, aba ativa e etapa de wizard ficam em query params. F5 mantém estado.
- **Soft delete e auditoria por padrão** (P-007): nada é apagado de verdade. Eventos importantes geram log append-only.

## Regras Gerais de Código

- SEMPRE TypeScript no frontend; Python tipado (Pydantic) no backend.
- Nomes descritivos: `isLoading`, `hasError`, `handleConfirmarAcao`.
- kebab-case para arquivos e pastas novos no frontend.
- Idioma do domínio (PT-BR) para entidades — manter consistência.
- SOLID, Clean Code, DRY (componentes de domínio reutilizáveis).
- NUNCA escrever comentários no código.
- NUNCA rodar `npm run dev`/`npm run build` para testar. Usar `npx tsc --noEmit` (frontend) e testes/`python -m` (backend).
- Valores monetários SEMPRE em centavos (integer) no banco. Display via `formatCurrency()`.
- Unidades físicas na menor unidade (integer) no banco. Converter no display.
- Datas no banco como `timestamptz` (UTC). Display com formatação local.

## Glossário do Domínio

Termos PROIBIDOS na UI: "registro", "entidade", "submeter", "validação", "transação", "objeto", "instância", "tenant", "request", "payload", "slot", "pipeline", "stub", "output_key", "session.state", "token", "async", "worker", "queue", "cron", "deploy", "schema", "trigger", "commit".

Glossários por módulo: ver `docs/arquitetura/AGENTE_CONSULTOR_CONVERSACIONAL.md` e `docs/arquitetura/MODULO_EXECUCAO_E_GESTAO_PROJETO.md`.

## Padrões Arquiteturais

- **P0 — Ciclo de Vida com Rascunho:** Rascunho → Confirmado → Estornado | Descartado. Auto-save ≤ 300 ms. Filtragem proativa na seleção.
- **P1 — Operações com Cascatas:** cascatas explícitas na MESMA transação. Falha em qualquer cascata = rollback completo.
- **P2 — Estado Calculado em Runtime:** NÃO armazenar estado derivável — calcular a partir de datas/saldos. Movimentações append-only.
- **P3 — Telas Analíticas:** read-only, cálculo em runtime com cache curto (5–15 min pesados; ≤ 1 min KPIs operacionais).

Mapear cada módulo novo a um destes padrões ANTES de codar.

## Banco de Dados

Toda entidade de domínio tem:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `user_id`/`org_id` quando aplicável — RLS filtra em TODA query
- `deleted_at TIMESTAMPTZ` — soft delete (P-007)
- `created_at` / `updated_at`
- Status via CHECK constraint ou enum

Auditoria: eventos importantes (confirmar workflow, concluir tarefa de alto valor, aceitar sugestão IA, convite/remoção de membro) gravam evento em tabela `auditoria_eventos` append-only com snapshot antes/depois.

## Backend (FastAPI)

- Schema Pydantic para todo request.
- Regras de negócio SEMPRE re-validadas no backend (P-005).
- Operações com cascata são transacionais.
- Mensagens de erro em linguagem do domínio: "Falta dizer quanto você gastou", não "Validation failed".
- Rate limiting em endpoints sensíveis (conversação, execução de ferramenta).
- Observabilidade: tempo, tokens e custo logados por ferramenta.

## Frontend (React)

- shadcn/ui sempre que possível; React Hook Form + Zod em formulários.
- React Query: hooks de query em `hooks/`, exportar query keys, invalidar TODAS as queries afetadas por cascatas.
- Estado em URL (P-006): filtros, abas, seleção, etapa de wizard em query params. Persistir só etapas navegáveis.
- Listagens com seleção: itens já selecionados aparecem PRIMEIRO.
- Toasts: linguagem do domínio; erros orientam correção; ações reversíveis usam Desfazer ≥ 5s; irreversíveis pedem confirmação explícita.
- Acessibilidade: botões primários ≥ 56×56 dp em fluxos de campo; contraste ≥ 4.5:1 (≥ 7:1 em condições adversas); ícone solo proibido em ação primária; botões primários na metade inferior (1 mão).

## Performance

- Auto-save ≤ 300 ms. Dashboard TTI ≤ 2s em 4G.
- Paginação/virtualização em listagens > 1.000 itens.
- Debounce 300ms em buscas.

## Segurança

- Validação em todos os endpoints. Nunca confiar em cálculo do client.
- RLS no nível mais baixo. Soft delete por padrão. Histórico imutável.

## Pendências críticas

Ao encontrar decisão pendente durante implementação, PERGUNTAR ao usuário antes de assumir default.

## Adaptação ao GymSite (substitui a stack do template)

| Template original | GymSite Intelligence (real) |
|---|---|
| Next.js 16 App Router + Server Actions | React 19 + Vite + TanStack Router; backend FastAPI (Python 3.12) |
| Next Safe Action | Endpoints FastAPI + Pydantic |
| Drizzle ORM + `drizzle-kit push` (sem migrations) | Supabase PostgreSQL + migrations SQL versionadas em `db/migrations/` (manter migrations — regra do drizzle NÃO se aplica) |
| Auth a definir | Supabase Auth + RLS (`auth.uid()`) |
| dayjs / react-hot-toast / tabler icons | Seguir o que já existe no frontend; não introduzir lib duplicada |

Princípios (P-001..P-007) e padrões (P0–P3) aplicam-se integralmente. Mecânica de implementação segue a stack real acima.
