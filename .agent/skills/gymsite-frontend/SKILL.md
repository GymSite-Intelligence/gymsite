---
name: gymsite-frontend
description: Desenvolvimento frontend React para GymSite Intelligence. Use ao criar páginas, componentes, hooks, rotas ou estilos. NÃO use para backend Python, schemas Pydantic ou lógica de pipeline.
---

# GymSite Intelligence — Frontend

## Contexto da Stack

- **Framework:** React 19 + TypeScript
- **Roteamento:** TanStack Router (code-based, NÃO file-based)
- **State/Cache:** TanStack Query (React Query)
- **UI:** shadcn/ui + Tailwind CSS
- **Ícones:** Lucide React
- **Build:** Vite

## Estrutura de Pastas

```
frontend/src/
├── components/
│   ├── ui/              # shadcn/ui (Button, Input, Select, Drawer, etc.)
│   ├── layout/          # AppShell, Sidebar, RequireAuth
│   ├── prospeccao/      # StatusBadge, PrioridadeBadge, OportunidadeDrawer
│   └── ...
├── hooks/
│   └── useProspeccao.ts  # TanStack Query hooks
├── routes/
│   └── ProspeccaoPage.tsx # Páginas (code-based routing)
├── lib/
│   ├── supabase.ts       # Cliente Supabase
│   └── nav-items.ts      # Itens do sidebar
├── router.tsx            # Registro de rotas TanStack
└── main.tsx              # Entry point
```

## Padrões de Código

### Hook TanStack Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export function useOportunidades(filters: ProspeccaoFilters) {
  return useQuery({
    queryKey: ['prospeccao', 'oportunidades', filters],
    queryFn: () => fetchOportunidades(filters),
  })
}

export function usePatchStatusOportunidade() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: patchStatus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prospeccao'] })
    },
  })
}
```

### Página com Filtros + Paginação

```typescript
const [page, setPage] = useState(0)
const pageSize = 20

const { data, isLoading } = useOportunidades({
  cidade,
  status,
  limit: pageSize,
  offset: page * pageSize,
})
```

### Rota TanStack (code-based)

```typescript
const prospeccaoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/prospeccao',
  component: ProspeccaoPage,
})
```

### Toast (Sonner)

```typescript
import { toast } from 'sonner'

toast.success('Status atualizado!')
toast.error('Erro ao salvar.')
```

## Componentes shadcn/ui Disponíveis

| Componente | Uso típico |
|---|---|
| `Button` | Ações primárias/secundárias |
| `Input` | Filtros de texto |
| `Select` | Dropdowns (status, prioridade) |
| `Drawer` | Detalhes de item selecionado |
| `Skeleton` | Loading states |
| `Badge` | Status/Prioridade |
| `Table` | Listagens (usamos HTML puro para controle total) |

## Tailwind — Classes Padrão

```tsx
<div className="container max-w-6xl py-8 space-y-6">
  <h1 className="text-2xl font-semibold tracking-tight">Título</h1>
  <p className="text-sm text-muted-foreground">Subtítulo</p>
  <div className="rounded-md border">
    {/* tabela */}
  </div>
</div>
```

## Regras de Ouro

1. **NUNCA modifique `router.tsx`** sem registrar a rota em `routeTree.addChildren()`
2. **Sempre invalide queries** após mutações (`queryClient.invalidateQueries`)
3. **Use `useMemo`** para ordenação/filtering client-side em listagens grandes
4. **Lazy loading** de componentes pesados via `React.lazy()`
5. **Nunca hardcode URLs de API** — use `API_BASE` de `@/lib/supabase`

## Anti-padrões

- ❌ Não use `alert()` — use `toast` do Sonner
- ❌ Não use `window.location` — use `useNavigate()` do TanStack Router
- ❌ Não coloque lógica de negócio complexa nos componentes — extraia para hooks
- ❌ Não use `any` em TypeScript — defina interfaces em `models/schemas.ts`
