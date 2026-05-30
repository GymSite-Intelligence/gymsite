---
name: workspace-governance
description: Governance rules for the GymSite Intelligence workspace. These rules apply to ALL tasks regardless of which skill is active.
---

# Workspace Governance Rules

These rules apply universally to every task in the GymSite Intelligence project.

## 1. Code Quality Standards

### Python
- **Line length:** 100 characters max
- **Functions:** ≤30 lines, ≤4 parameters
- **Files:** ≤300 lines (split if larger)
- **Nesting:** ≤3 levels deep
- **Type hints:** Mandatory on all functions and class attributes
- **Docstrings:** Google style (Args, Returns, Raises)
- **Imports:** `isort` order (stdlib → third-party → local)

### TypeScript/React
- **Line length:** 100 characters max
- **Components:** Prefer named functions over arrow functions
- **Props:** Always typed with interface
- **Hooks:** Custom hooks for business logic, never in components
- **State:** Use `useState` for local, TanStack Query for server
- **Effects:** Minimal `useEffect`, prefer event handlers

## 2. File Organization

### Backend
```
tools/
  maps_tools.py           ← OK
  maps.py                 ← OK (simple)
  utils/maps_helpers.py   ← OK (if multiple helpers)
  utils.py                ← AVOID (dumping ground)
```

### Frontend
```
components/
  ui/                     ← shadcn components (never modify)
  prospeccao/             ← domain-specific components
  layout/                 ← shell components
hooks/
  useProspeccao.ts        ← domain hook
  useRelatorioDetail.ts   ← domain hook
```

## 3. Naming Conventions

| Context | Convention | Example |
|---|---|---|
| Python functions | `snake_case` | `calcular_score_match` |
| Python classes | `PascalCase` | `RelatorioPDFBuilder` |
| TS/JS functions | `camelCase` | `useOportunidades` |
| TS/JS components | `PascalCase` | `OportunidadeDrawer` |
| TS interfaces | `PascalCase` | `ProspeccaoFilters` |
| Constants | `UPPER_SNAKE` | `TICKET_MEDIO` |
| Environment vars | `UPPER_SNAKE` | `SUPABASE_URL` |

## 4. Prohibited Patterns

### Python
- ❌ `print()` in production code
- ❌ Bare `except:` clauses
- ❌ Mutable default arguments: `def foo(x=[])`
- ❌ `from module import *`
- ❌ Implicit Optional: `def foo(x: str = None)` → use `str | None`
- ❌ Global state (use dependency injection or context)

### TypeScript
- ❌ `any` type (use `unknown` + narrowing)
- ❌ `console.log()` in production
- ❌ Inline styles (use Tailwind classes)
- ❌ Nested ternaries beyond 2 levels
- ❌ `useEffect` without dependency array

## 5. Documentation Requirements

Every module/file must have:
1. **Module docstring** explaining purpose
2. **Complex functions** docstrings
3. **TODO comments** with issue reference: `# TODO(#42): refactor this`
4. **Architecture Decision Records** in `docs/` for major changes

## 6. Testing Expectations

- New features → add tests
- Bug fixes → add regression test first
- Critical paths → integration tests (FastAPI TestClient, Playwright)

## 7. Git Hygiene

- Commits in English, present tense: "Add prospecting pagination"
- One logical change per commit
- No WIP commits in PRs
- Rebase before merging to keep linear history
