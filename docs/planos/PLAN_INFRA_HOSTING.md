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
- Conclusao: o DNS autoritativo e a HostGator (NAO a Cloudflare). Confirmado tambem pelo lado Cloudflare: gymsite.com.br nao e uma zona na conta Cloudflare.

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

## CDN / Edge (Cloudflare Pages) - VERIFICADO no painel Cloudflare em 2026-06-13

- Conta Cloudflare: marcelo.rosas@vectracargo.com.br.
- Projeto Pages que serve o site: nome **gymsite** (subdominio padrao gymsite-3p0.pages.dev).
- Dominio customizado anexado ao projeto: **www.gymsite.com.br** (confirmado na lista de domains do projeto).
- Branch de producao: main.
- Ultimo deploy de producao: 2026-06-13, estagio 'deploy' com status SUCCESS (build OK).
- Observacao: existe um segundo projeto Pages chamado 'gymsite-3p0' (gymsite-3p0-2jr.pages.dev) sem dominio customizado — NAO e o que serve o site; o site e servido pelo projeto 'gymsite'.

## Arquitetura de entrega (resolvido)

- apex gymsite.com.br -> A 69.49.241.85 (HostGator).
- www.gymsite.com.br -> CNAME gymsite-3p0.pages.dev (projeto Pages 'gymsite').
- NAO ha zona/redirect no Cloudflare (gymsite.com.br nao e zona Cloudflare). Logo, qualquer redirect apex<->www teria de ser feito no HostGator (ou trocando o apex para o Pages). Hoje apex e www sao servidos por sistemas diferentes.

## E-mail - verificado (via DNS)

- E-mail do dominio gymsite.com.br: provedor Titan (mx1/mx2.titan.email, SPF include spf.titan.email, DKIM titan1).
- E-mail outbound de prospeccao (Apollo) usa OUTRO dominio (vectracargo.com.br) - ver PLAN_APOLLO.md. Sao fluxos distintos.

## Riscos / pontos de atencao

1. Apex (HostGator) e www (Cloudflare Pages) servem por caminhos diferentes — definir redirect canonico no HostGator e garantir TLS em ambos.
2. E-mail do dominio (Titan) e e-mail de prospeccao (Apollo/vectracargo) sao distintos — manter SPF/DKIM/DMARC de cada dominio separados.
3. DMARC: nao foi observado registro _dmarc na zona — recomendado adicionar politica DMARC para gymsite.com.br.
4. Renovacoes: dominio (13/06/2028) e hospedagem (13/12/2026) tem datas diferentes — monitorar.

## Pendencias / proximos passos

1. Configurar redirect canonico apex<->www no HostGator (decidir qual e o host canonico).
2. Validar certificado TLS no apex e no www.
3. Avaliar adicao de registro DMARC para gymsite.com.br.
4. Registrar credenciais/acessos em cofre proprio do usuario (nao neste repo).

## Constraints

- Nao inserir senhas nem alterar permissoes de acesso em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita.
- Nao reproduzir segredos (chaves DKIM completas, tokens) neste repo.
