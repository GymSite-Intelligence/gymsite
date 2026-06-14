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

Registros relevantes da zona gymsite.com.br (segredos como chaves DKIM completas nao reproduzidos aqui):

| Nome | Tipo | Valor | TTL |
|------|------|-------|-----|
| gymsite.com.br. | A | 69.49.241.85 (HostGator) | 14400 |
| www.gymsite.com.br. | CNAME | gymsite-3p0.pages.dev (Cloudflare Pages) | 14400 |
| mail.gymsite.com.br. | A | 69.49.241.85 | 14400 |
| gymsite.com.br. | MX | mx1.titan.email (prio 10) | 3600 |
| gymsite.com.br. | MX | mx2.titan.email (prio 20) | 3600 |
| gymsite.com.br. | TXT (SPF) | v=spf1 include:spf.titan.email ~all | 3600 |
| _dmarc.gymsite.com.br. | TXT (DMARC) | v=DMARC1; p=none; rua=mailto:dmarc@gymsite.com.br; fo=1 | 14400 |
| default._domainkey | TXT (DKIM) | presente (chave RSA, valor omitido) | 14400 |
| titan1._domainkey | TXT (DKIM) | presente (chave RSA, valor omitido) | 3600 |

Tambem existem os subdominios padrao do cPanel (cpanel, webmail, webdisk, ftp, autodiscover, cpcontacts, cpcalendars, whm) apontando para 69.49.241.85, e registros SRV/TXT de caldav/carddav/autodiscover.

## Alteracoes aplicadas em 2026-06-13 (com autorizacao)

1. DMARC: criado o registro TXT _dmarc.gymsite.com.br com politica de MONITORAMENTO (p=none) e relatorios agregados para dmarc@gymsite.com.br. Proximo passo (apos analisar relatorios): endurecer para p=quarantine e depois p=reject.
2. Redirect canonico: criado redirect 301 PERMANENTE do apex gymsite.com.br -> https://www.gymsite.com.br (opcao 'nao redirecionar www', para NAO afetar www que e servido pelo Cloudflare Pages). Confirmado pelo cPanel: "'/' on 'gymsite.com.br' redirects to 'https://www.gymsite.com.br'".

## CDN / Edge (Cloudflare Pages) - VERIFICADO no painel Cloudflare em 2026-06-13

- Conta Cloudflare: marcelo.rosas@vectracargo.com.br.
- Projeto Pages que serve o site: nome 'gymsite' (subdominio padrao gymsite-3p0.pages.dev).
- Dominio customizado anexado ao projeto: www.gymsite.com.br.
- Branch de producao: main. Ultimo deploy de producao: 2026-06-13, status SUCCESS.
- Observacao: existe um segundo projeto Pages 'gymsite-3p0' (gymsite-3p0-2jr.pages.dev) sem dominio customizado — NAO e o que serve o site.

## Arquitetura de entrega (resolvido)

- apex gymsite.com.br -> A 69.49.241.85 (HostGator) -> redirect 301 -> https://www.gymsite.com.br.
- www.gymsite.com.br -> CNAME gymsite-3p0.pages.dev (projeto Pages 'gymsite') -> app em producao.
- Host canonico: www.

## E-mail - verificado (via DNS)

- E-mail do dominio gymsite.com.br: provedor Titan (mx1/mx2.titan.email, SPF include spf.titan.email, DKIM titan1, DMARC p=none).
- E-mail outbound de prospeccao (Apollo) usa OUTRO dominio (vectracargo.com.br) - ver PLAN_APOLLO.md. Sao fluxos distintos.

## Riscos / pontos de atencao

1. DMARC esta em p=none (monitoramento). Nao protege contra spoofing ainda — endurecer apos validar relatorios.
2. O redirect do apex roda no HostGator; depende do apex continuar apontando para 69.49.241.85. Se o apex for movido, revisar.
3. E-mail do dominio (Titan) e e-mail de prospeccao (Apollo/vectracargo) sao distintos — manter SPF/DKIM/DMARC de cada dominio separados.
4. Renovacoes: dominio (13/06/2028) e hospedagem (13/12/2026) tem datas diferentes — monitorar.

## Pendencias / proximos passos

1. Validar o redirect apex->www em producao (testar http e https no apex).
2. Acompanhar relatorios DMARC e endurecer a politica (quarantine -> reject).
3. Garantir certificado TLS valido no apex (para o 301 funcionar via https).
4. Registrar credenciais/acessos em cofre proprio do usuario (nao neste repo).

## Constraints

- Nao inserir senhas nem alterar permissoes de acesso em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita.
- Nao reproduzir segredos (chaves DKIM completas, tokens) neste repo.
