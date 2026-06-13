# PLAN - Infra / Hosting / DNS

> Categoria: dominio, hospedagem, DNS e CDN do GymSite.
> Atualizado em 2026-06-13.
> Nota de privacidade: dados pessoais do titular (CPF/endereco/telefone) NAO sao registrados aqui.

## Objetivo

Manter o dominio do produto registrado, apontado corretamente e servido com hospedagem + CDN, base para o site/app e e-mail.

## Dominio (Registro.br) - verificado

- Dominio: gymsite.com.br
- Status: Publicado
- Criacao: 13/06/2026 | Expiracao: 13/06/2028
- Titular: pessoa fisica (dados pessoais omitidos por privacidade)
- Servidores DNS apontados: ns1080.hostgator.com.br e ns1081.hostgator.com.br
- Conclusao: o DNS autoritativo e a HostGator (nao a Cloudflare).

## Hospedagem (HostGator) - verificado

- Produto: Plano M (compartilhado)
- Dominio principal: gymsite.com.br
- Status: Ativo | Vencimento: 13/12/2026
- Servidor/cPanel: host br1080 | IP do servidor: 69.49.241.85
- Subdominios: nenhum cadastrado manualmente (apenas os de servico do cPanel)

## DNS (cPanel Zone Editor) - verificado em 2026-06-13

Registros relevantes da zona gymsite.com.br (27 registros no total; segredos como chaves DKIM completas nao reproduzidos aqui):

| Nome | Tipo | Valor | TTL |
|------|------|-------|-----|
| gymsite.com.br. | A | 69.49.241.85 (HostGator) | 14400 |
| www.gymsite.com.br. | CNAME | gymsite-3p0.pages.dev (Cloudflare Pages) | 14400 |
| mail.gymsite.com.br. | A | 69.49.241.85 | 14400 |
| gymsite.com.br. | MX | mx1.titan.email (prio 10) | 3600 |
| gymsite.com.br. | MX | mx2.titan.email (prio 20) | 3600 |
| gymsite.com.br. | TXT (SPF) | v=spf1 include:spf.titan.email ~all | 3600 |
| default._domainkey | TXT (DKIM) | presente (chave RSA, valor omitido) | 14400 |
| titan1._domainkey | TXT (DKIM) | presente (chave RSA, valor omitido) | 3600 |

Tambem existem os subdominios padrao do cPanel (cpanel, webmail, webdisk, ftp, autodiscover, cpcontacts, cpcalendars, whm) apontando para 69.49.241.85, e registros SRV/TXT de caldav/carddav/autodiscover.

## CDN / Edge (Cloudflare Pages) - verificado (via DNS)

- O frontend e servido via Cloudflare Pages: www.gymsite.com.br -> CNAME gymsite-3p0.pages.dev.
- O apex (gymsite.com.br) aponta para a HostGator (A 69.49.241.85).
- Arquitetura de entrega: apex na HostGator, www no Cloudflare Pages. Convem padronizar para evitar divergencia entre apex e www.
- (a confirmar no painel Cloudflare) estado da conta/projeto Pages, dominio customizado verificado e configuracao de redirect apex->www (ou vice-versa).

## E-mail - verificado (via DNS)

- E-mail do dominio gymsite.com.br: provedor Titan (mx1/mx2.titan.email, SPF include spf.titan.email, DKIM titan1).
- E-mail outbound de prospeccao (Apollo) usa OUTRO dominio (vectracargo.com.br) - ver PLAN_APOLLO.md. Sao fluxos distintos.

## Riscos / pontos de atencao

1. Apex (HostGator) e www (Cloudflare Pages) servem por caminhos diferentes — definir redirect canonico e garantir TLS em ambos.
2. E-mail do dominio (Titan) e e-mail de prospeccao (Apollo/vectracargo) sao distintos — manter SPF/DKIM/DMARC de cada dominio separados.
3. DMARC: nao foi observado registro _dmarc na zona — recomendado adicionar politica DMARC para gymsite.com.br.
4. Renovacoes: dominio (13/06/2028) e hospedagem (13/12/2026) tem datas diferentes — monitorar.

## Pendencias / proximos passos

1. Confirmar no painel Cloudflare o estado do projeto Pages (gymsite-3p0) e o dominio customizado.
2. Padronizar entrega do frontend (redirect apex<->www) e validar certificado em ambos.
3. Avaliar adicao de registro DMARC para gymsite.com.br.
4. Registrar credenciais/acessos em cofre proprio do usuario (nao neste repo).

## Constraints

- Nao inserir senhas nem alterar permissoes de acesso em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita.
- Nao reproduzir segredos (chaves DKIM completas, tokens) neste repo.
