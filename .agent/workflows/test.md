---
description: Run the complete test suite (backend + frontend + E2E) with coverage reports. Validates all critical paths before deploy.
---

# Workflow: /test

Execute the full test suite across all layers.

## Steps

1. **Pre-check** // turbo
   ```bash
   pyrefly check . && echo "Types OK"
   cd frontend && npm run lint && echo "Lint OK"
   ```

2. **Backend unit tests**
   ```bash
   pytest -x --tb=short
   ```

3. **Backend coverage**
   ```bash
   pytest --cov=tools --cov=agents --cov=prospecting --cov-report=term-missing --cov-report=html
   ```
   - Target: ≥60% tools, ≥80% API endpoints

4. **Frontend unit tests**
   ```bash
   cd frontend && npm run test:run
   ```

5. **Frontend coverage**
   ```bash
   cd frontend && npx vitest run --coverage
   ```
   - Target: ≥50% components, ≥70% hooks

6. **E2E tests**
   ```bash
   cd frontend && npx playwright test
   ```
   - Critical paths: login, criar relatório, prospecção, exportar CSV

7. **Generate report**
   ```bash
   echo "=== BACKEND COVERAGE ==="
   cat htmlcov/index.html | grep -o '[0-9]\+%' | head -1
   echo "=== FRONTEND COVERAGE ==="
   cat frontend/coverage/index.html | grep -o '[0-9]\+%' | head -1
   ```

## Safety

- ⚠️ E2E tests need the backend running locally
- ⚠️ Playwright tests may modify DB state — use test database if possible
