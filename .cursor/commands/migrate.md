---
name: migrate
description: "Aplicar UMA migration SQL (schema gymsite / views public)"
---

# /migrate

Seguir **à letra** o workflow:

`.agent/workflows/migrate.md`

Proibido reaplicar `db/migrations/*.sql` em lote. Confirmar `relkind` antes de ALTER.
