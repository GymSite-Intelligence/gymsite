---
name: test
description: "Gate pytest .venv + tsc --noEmit"
---

# /test

Seguir **à letra** o workflow:

`.agent/workflows/test.md`

Backend: `.venv\Scripts\python.exe -m pytest`. Front: `npx tsc --noEmit`. Sem Vitest/Playwright fantasmas.
