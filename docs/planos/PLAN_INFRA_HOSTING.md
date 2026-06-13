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

## Hospedagem (HostGator) - verificado

- Produto: Plano M (compartilhado)
- Dominio principal: gymsite.com.br
- Status: Ativo | Vencimento: 13/12/2026
- Servidor/cPanel: host br1080 (cPanel acessivel)
- Subdominios: nenhum cadastrado ainda

## cPanel - verificado

- Acesso ao cPanel disponivel (Jupiter theme).
- Zone Editor utilizado anteriormente para gerenciar registros DNS do dominio.
- (a confirmar) registros DNS especificos criados/editados (A, CNAME, MX, TXT/SPF/DKIM/DMARC).

## CDN / Edge (Cloudflare) - a confirmar

- Cloudflare foi utilizado no engajamento (Pages/CDN). (a confirmar) estado atual: zona ativa, proxy, e se o frontend e servido via Cloudflare Pages ou via HostGator.
- Observacao: o DNS autoritativo atual aponta para HostGator (ns1080/ns1081), entao se o Cloudflare estiver em uso, e preciso alinhar quem e o DNS autoritativo.

## Riscos / pontos de atencao

1. Dois caminhos de servir o site (HostGator vs Cloudflare Pages) podem conflitar — definir um unico fluxo.
2. E-mail outbound (Apollo, dominio vectracargo) e e-mail do dominio gymsite sao coisas distintas — alinhar SPF/DKIM/DMARC de cada um.
3. Renovacoes: dominio (2028) e hospedagem (12/2026) tem datas diferentes — monitorar.

## Pendencias / proximos passos

1. Confirmar e documentar os registros DNS atuais no Zone Editor (sem expor segredos).
2. Decidir arquitetura de entrega do frontend (HostGator vs Cloudflare Pages) e padronizar.
3. Configurar/validar SPF/DKIM/DMARC do dominio conforme o uso de e-mail.
4. Registrar credenciais/acessos em cofre proprio do usuario (nao neste repo).

## Constraints

- Nao inserir senhas nem alterar permissoes de acesso em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita.

