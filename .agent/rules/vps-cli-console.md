# VPS CLI (Hetzner) — canónico

> Cursor: [`.cursor/rules/vps-cli-console.mdc`](../../.cursor/rules/vps-cli-console.mdc)

API = `/opt/gymsite` no Linux da VPS (`gymsite-api`). Não existe no Windows.

**PowerShell / CMD:** não colar `grep` / `sed` / `cd /opt/gymsite` / `docker compose -f docker-compose.prod.yml`. Só `ssh` ou Console no painel.

**Consola web Hetzner (noVNC):** teclado inverte maiúsculas/minúsculas. Entregar bloco `swapcase` (letras) + bloco original. Se o ecrã mostrar `GREP`, Caps Lock está off → original.

**SSH** com teclado normal: só original.

Evitar na consola: `|` (`\`), `(` / `)` (`9` / `0`), `^` (`6`). Paths sem swapcase. `GET /actions` da Cloud API não muda env nem contentores.
