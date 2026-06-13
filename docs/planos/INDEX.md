# INDEX - Planos por categoria (GymSite Intelligence)

Registro consolidado do que foi feito no engajamento de setup/consultoria. Atualizado em 2026-06-13. Cada categoria tem seu proprio PLAN nesta pasta. Itens nao verificaveis nesta sessao estao marcados como (a confirmar).

## Planos

| Categoria | Arquivo | Status resumido |
|-----------|---------|-----------------|
| Prospeccao / Outbound (Apollo) | PLAN_APOLLO.md | Mailbox configurada, warmup pendente |
| Infra / Hosting / DNS | PLAN_INFRA_HOSTING.md | Dominio ativo; DNS na HostGator; DNS e Cloudflare Pages verificados (apex->HostGator, www->projeto Pages 'gymsite', e-mail Titan) |
| App / Frontend | PLAN_APP_FRONTEND.md | Frontend em Cloudflare Pages (projeto 'gymsite', deploy de producao OK 2026-06-13); telas em dev (localhost) a confirmar |
| Agente do site (Agent Studio) | PLAN_AGENTE.md | Prompt corrigido e IMPLANTADO (deploy 2026-06-13, us-west1) |
| Avaliacao do agente (eval) | ../agente/PLAN_AGENT_EVAL.md | 14/15 PASS; cobertura_fallback depende de fix de backend |
| Fix arquitetural (cobertura) | ../agente/FIX_COBERTURA_FALLBACK.md | Documentado: allowlist de cobertura no backend |

## Convencoes

- (a confirmar): detalhe nao verificado diretamente nesta sessao; nao inventar.
- Nenhum dado pessoal sensivel (CPF, endereco, telefone) e registrado nestes documentos.
- Cloudflare verificado em 2026-06-13: projeto Pages 'gymsite' com dominio www.gymsite.com.br e deploy de producao com sucesso. gymsite.com.br NAO e zona Cloudflare (DNS autoritativo na HostGator); por isso nao ha redirect apex<->www no Cloudflare — pendencia movida para o HostGator.

## Constraints permanentes do projeto

- Sigilo de fontes; LGPD; Fase 0 sem precos fixos; nao publicar/deploy sem autorizacao.
