---
name: gymsite-resend
description: >-
  Envio de e-mail GymSite via Resend (drip degustação/Explorar, transacional).
  Use when the user mentions Resend, e-mail, drip, sequence, degustação e-mail,
  plugin Resend, MCP Resend, contato@gymsite.com.br, or nurture after Explorar.
---

# GymSite × Resend

Produção manda e-mail pela **API na VPS** (`RESEND_API_KEY` + `RESEND_FROM`).
MCP Resend no Cursor é só para o agente **desenvolver e testar** (seu e-mail).

## Quando usar

- Ligar drip após degustação / Explorar.
- Template “pesquisa grátis”, “relatório pronto”, follow-up dia 3/8.
- Testar envio pelo MCP Resend.
- **Não** usar Apollo para sequence. **Não** achar dono de academia via Resend.

## Regras

1. Remetente: `GymSite <contato@gymsite.com.br>` (domínio já verificado).
2. Reply-to: mesma caixa Titan (`contato@gymsite.com.br`).
3. Cliente real: só código no backend (`tools/` / `backend/`), nunca disparo em massa pelo chat.
4. Teste MCP: só e-mail do Marcelo / `teste@gymsite.com.br`.
5. Webhook Resend: opcional (bounce/open). Não bloqueia o drip v1.
6. Segredo: `.env` local + `.env.production` na VPS. Nunca commit. Nunca colar a chave no chat.
7. Login OTP do app continua no **Supabase Auth**, não no Resend.

## MCP no Cursor

Servidor global `resend` → `https://mcp.resend.com/mcp` (OAuth no browser).
Se o MCP estiver `needsAuth`, autenticar e só então enviar teste.

Skills oficiais Resend (templates React Email): `npx skills add resend/resend-skills`.

## Implementação backend (quando pedir código)

- Env: `RESEND_API_KEY`, `RESEND_FROM` (já na VPS).
- HTTP `POST https://api.resend.com/emails` com `Authorization: Bearer`.
- Lead Explorar/landing: gravar em `gymsite.leads`, depois enfileirar drip (dia 0 / 3 / 8).
- Dia 0 = `send_explorar_welcome` (HTML do recorte). Dia 3 e 8 = automação Resend `Explorar — cadência dia 3 e 8` no evento `explorar.lead_captured`.
- Linguagem do e-mail: dono de academia, PT simples. Sem jargão técnico.

## Anti-padrões

- ❌ Pagar Apollo só para sequence
- ❌ Mandar e-mail de lead pelo Cursor MCP em produção
- ❌ HubSpot no funil GymSite
- ❌ Waterfall/People Search no Resend (não existe)
