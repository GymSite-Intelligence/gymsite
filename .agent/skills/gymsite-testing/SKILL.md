---
name: gymsite-testing
description: Testes automatizados para GymSite Intelligence. Use ao criar, modificar ou depurar testes de backend (pytest), testes de frontend (Vitest/Playwright), ou testes de integração. NÃO use para lógica de negócio, endpoints REST ou componentes UI sem testes.
---

# GymSite Intelligence — Testes

## Contexto da Stack

- **Backend:** pytest (async, fixtures, monkeypatch)
- **Frontend unit:** Vitest (vem com Vite)
- **Frontend E2E:** Playwright (browser automation)
- **Mock:** `unittest.mock` (Python) / `msw` (Frontend)
- **Cobertura:** pytest-cov / Vitest coverage

## Estrutura de Testes

```
backend (Python):
├── tests/
│   ├── test_distance_matrix.py
│   └── test_vertex_setup.py
├── test_cobertura_a0.py          # Testes de agente A0
├── test_deep_research.py
├── test_geofence_eusebio.py
├── test_renda_eusebio.py
└── test_resolver_cidade.py

frontend (React):
frontend/src/
├── __tests__/                    # (criar se necessário)
│   ├── hooks/useProspeccao.test.ts
│   └── components/StatusBadge.test.tsx
└── e2e/
    └── prospeccao.spec.ts        # Playwright E2E
```

## Padrões de Teste

### Python — pytest

```python
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

@pytest.fixture
def mock_supabase(monkeypatch):
    """Mock do cliente Supabase para testes isolados."""
    class FakeClient:
        def table(self, name):
            return FakeTable()
    class FakeTable:
        def select(self, *args): return self
        def eq(self, **kwargs): return self
        def execute(self):
            return {"data": [{"id": "1", "status": "novo"}]}
    monkeypatch.setattr("api._supabase_client", lambda: FakeClient())

def test_listar_oportunidades(mock_supabase):
    response = client.get("/api/prospeccao/oportunidades?cidade=Fortaleza")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["status"] == "novo"

@pytest.mark.asyncio
async def test_buscar_academias():
    from tools.competitor_tools import buscar_academias
    result = buscar_academias("Aldeota", "Fortaleza", raio_metros=1000)
    assert "concorrentes" in result
    assert isinstance(result["concorrentes"], list)
```

### Frontend — Vitest

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProspeccaoPage } from '@/routes/ProspeccaoPage'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const createTestQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } }
})

describe('ProspeccaoPage', () => {
  it('renders filters and table', () => {
    const queryClient = createTestQueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <ProspeccaoPage />
      </QueryClientProvider>
    )
    expect(screen.getByText('Prospecção CNPJ × CNO')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Fortaleza')).toBeInTheDocument()
  })
})
```

### E2E — Playwright

```typescript
import { test, expect } from '@playwright/test'

test('prospecção - fluxo completo', async ({ page }) => {
  await page.goto('/prospeccao')
  await expect(page.getByText('Prospecção CNPJ × CNO')).toBeVisible()
  
  // Filtrar por cidade
  await page.getByPlaceholder('Fortaleza').fill('Fortaleza')
  await page.getByRole('button', { name: /executar/i }).click()
  
  // Verificar toast de sucesso
  await expect(page.getByText('Prospecção iniciada')).toBeVisible()
  
  // Abrir drawer
  await page.locator('table tbody tr').first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
})
```

## Fixtures Reutilizáveis

### Python

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def event_loop():
    """Fixture para testes async com pytest-asyncio."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_oportunidade():
    return {
        "id": "uuid-test",
        "cnpj": "12.345.678/0001-99",
        "cidade": "Fortaleza",
        "uf": "CE",
        "status": "novo",
        "prioridade": "alta",
        "score_match": 0.85,
        "created_at": "2026-05-29T00:00:00Z",
    }
```

## Mock de APIs Externas

```python
# Nunca chame Google Maps ou Apollo em testes!
@pytest.fixture
def mock_google_maps(monkeypatch):
    def fake_distance_matrix(*args, **kwargs):
        return {"rows": [{"elements": [{"distance": {"value": 1500}}]}]}
    monkeypatch.setattr(
        "googlemaps.Client.distance_matrix",
        fake_distance_matrix
    )
```

## Comandos

```bash
# Backend
pytest                              # Rodar todos
pytest -x                          # Parar no primeiro erro
pytest -k "test_prospec"           # Filtrar por nome
pytest --cov=tools --cov-report=html  # Cobertura

# Frontend
npm run test                       # Vitest watch mode
npm run test:run                   # Vitest CI mode
npm run test:e2e                   # Playwright
npx playwright test --headed       # Playwright com browser visível
```

## Anti-padrões

- ❌ Não teste implementação — teste comportamento
- ❌ Não use `time.sleep()` em testes — use `asyncio.wait_for()` ou fixtures
- ❌ Não deixe testes dependentes de ordem — cada teste deve ser isolado
- ❌ Não ignore falhas intermitentes — flakiness é um bug
- ❌ Não teste bibliotecas de terceiros (teste SEU código)

## Cobertura Mínima

| Camada | Cobertura Mínima | Foco |
|---|---|---|
| Backend API | 80% | Endpoints críticos (relatórios, prospecção) |
| Backend Tools | 60% | Funções puras (scoring, parsing) |
| Frontend Hooks | 70% | TanStack Query hooks |
| Frontend Components | 50% | Componentes complexos (Drawer, tabelas) |
| E2E | 5 cenários | Fluxos críticos (login → relatório → PDF) |
