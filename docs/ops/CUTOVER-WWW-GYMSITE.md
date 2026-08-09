# Cutover www.gymsite.com.br → Pages `gymsite`

Manual. Não automatizar DNS sem humano.

## Pré

- [ ] `frontend/` com landing `/`, `/blog`, `/degustacao`, `/explorar` unificado deployado no projeto CF **gymsite** (ainda em `getgymsite.com.br` se www ainda for hub).
- [ ] Build Pages: `VITE_DEGUSTACAO_PROVIDER=cloudflare`, `VITE_TURNSTILE_SITEKEY`, Supabase publishable, `VITE_API_BASE=https://api.getgymsite.com.br` (A0–A9). Chat isca: `resolveSiteAgentBases` ignora `VITE_API_BASE` se provider=cloudflare → same-origin Worker.
- [ ] Worker `gymsite-degustacao` já roteia `www.gymsite.com.br/api/site-agent/*`.
- [ ] `_routes.json` no dist: `exclude: ["/api/site-agent/*"]`.
- [ ] Supabase Auth → Redirect URLs: `https://www.gymsite.com.br/**` e `https://www.gymsite.com.br/auth/callback`.

## Ordem (evitar dois Pages no mesmo host)

1. Deploy produção do monorepo `frontend/` no projeto **gymsite**.
2. Anexar custom domain **www.gymsite.com.br** ao projeto **gymsite**.
3. **Remover** www do projeto **gym-insight-hub** (senão conflito).
4. Redirect Rule zona `getgymsite.com.br`:
   - If hostname equals `getgymsite.com.br` (não `api.` / `api-hetzner.`)
   - Then 301 `https://www.gymsite.com.br/${path}` (preservar query).
5. Apex `gymsite.com.br` já 301 → www (HostGator) — não mexer.

## Smoke

- [ ] `https://www.gymsite.com.br/` landing
- [ ] `/blog` + um slug cidade
- [ ] `/degustacao` chat (Worker + Turnstile)
- [ ] `/explorar` anônimo (1 recorte)
- [ ] `/login` → `/dashboard` logado → `/consultor` → `/explorar` com sidebar
- [ ] `https://getgymsite.com.br/explorar` → 301 `/explorar` no www
- [ ] `/degustacao/explorar` → `/explorar`

## Rollback

Reanexar www ao hub; remover redirect getgymsite; redeploy hub.
