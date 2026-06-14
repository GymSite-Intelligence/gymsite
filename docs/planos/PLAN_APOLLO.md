# PLAN — Prospeccao / Outbound (Apollo)

Categoria: geracao de leads e e-mail outbound via Apollo.io. Atualizado em 2026-06-14. Nota de privacidade: dados pessoais (CPF/endereco/telefone) NAO sao registrados aqui.

## Objetivo

Estruturar a operacao de prospeccao outbound (academias / donos de negocio fitness) para alimentar o funil do GymSite, a partir de um dominio de envio dedicado de marca, com autenticacao (SPF/DKIM/DMARC) e aquecimento (warmup) antes de disparos em escala.

## Decisao de dominio de envio (2026-06-14)

Avaliamos 3 opcoes para o dominio remetente das sequencias. O remetente que o lead ve e SEMPRE a caixa conectada ao Apollo (o Apollo nao mascara o From).

| Opcao | Marca GymSite no From? | Reputacao | DNS | Veredito |
|---|---|---|---|---|
| gymsite.com.br (raiz do produto) | Sim | Arriscado (cold outbound no dominio principal; DMARC ainda p=none) | cPanel HostGator | Evitar |
| vectracargo.com.br | Nao | DMARC p=reject; SPF so cobre Cloudflare | Cloudflare (NS) | Inviavel sem ajuste arriscado |
| vectracargo.com | Nao | SPF ja cobre GoDaddy; DMARC p=quarantine | GoDaddy (NS) | Pronto, mas sem marca |
| getgymsite.com.br (marca dedicada) | Sim (marca, sem ser a raiz) | Dominio novo (precisa warmup), isola o produto | cPanel HostGator | ESCOLHIDO |

Decisao: usar getgymsite.com.br — dominio de marca dedicado para outbound, que carrega a marca GymSite sem arriscar a reputacao do dominio raiz gymsite.com.br.

## Estado dos dominios (verificado via DNS publico em 2026-06-14)

- gymsite.com.br: e-mail Titan (mx1/mx2.titan.email), SPF include spf.titan.email, DMARC p=none. E o dominio do produto — nao usar para cold outbound.
- vectracargo.com.br: MX misto GoDaddy (secureserver.net) + Cloudflare routing; SPF so include _spf.mx.cloudflare.net ~all; DMARC p=reject; NS na Cloudflare.
- vectracargo.com: MX GoDaddy (secureserver.net); SPF v=spf1 include:secureserver.net -all (ja cobre o sender GoDaddy); DMARC p=quarantine; NS na GoDaddy (domaincontrol.com). Subutilizado.
- getgymsite.com.br: pedido de registro EM FILA de processamento (HostGator, pedido 31598622). Status no portal: "Falha no registro" / pagamento pos-conclusao. DNS ainda NXDOMAIN (nao resolve). AGUARDANDO ATIVACAO.

## Estado atual do Apollo (verificado)

- Caixa conectada hoje: manager@vectracargo.com.br (IMAP, marcada como Padrao) — provedor de envio GoDaddy. Setup ~80%.
- Diagnostico de autenticacao da caixa atual: DKIM Bom, DMARC Bom, SPF "Revisar" (o SPF do .br nao cobre o sender GoDaddy). Por isso vamos migrar para o dominio dedicado em vez de remendar o .br.
- Warmup: ainda nao iniciado. Limites: 50/dia, 6/hora, 600s de atraso.
- Itens de setup ja OK: Assinatura, Limites de envio, Link de descadastro, Subdomain tracking.

## Runbook de configuracao pos-ativacao do getgymsite.com.br

Executar quando o dominio sair de "Falha no registro" para Ativo e o DNS comecar a resolver:

1. Apontar/associar o dominio a hospedagem (cPanel HostGator) ou garantir que a zona DNS do getgymsite.com.br esteja gerenciavel no cPanel (mesma conta br1080).
2. Criar a caixa de e-mail de envio: contato@getgymsite.com.br (criacao da caixa e do acesso e feita pelo usuario — o assistente nao cria conta nem insere senha).
3. Conectar a caixa contato@getgymsite.com.br ao Apollo (login/conexao feita pelo usuario) e definir como caixa de envio das sequencias.
4. Autenticacao no DNS (cPanel Zone Editor), com proposta-primeiro antes de publicar cada registro:
   - SPF (TXT no apex): autorizar o sender real da caixa. Valor de referencia a confirmar conforme o provedor de envio (ex.: v=spf1 include:<sender> ~all). Definir apos sabermos por onde a caixa envia (HostGator/Titan/etc.).
   - DKIM (TXT): publicar o seletor DKIM que o provedor de envio / Apollo gerar. Valor exato vem do painel (nao reproduzir a chave neste repo).
   - DMARC (TXT em _dmarc): iniciar em p=none (monitoramento) com rua=mailto:dmarc@getgymsite.com.br; endurecer para quarantine -> reject apos validar relatorios.
5. Rodar o diagnostico do Apollo (Domain authentication) ate SPF/DKIM/DMARC ficarem "Bom".
6. Iniciar o WARMUP (aquecimento) e manter por algumas semanas com volume baixo. So escalar o limite diario apos warmup saudavel.
7. So entao ligar as sequencias para leads reais.

## Pendencias / proximos passos

- [ ] (USUARIO) Concluir o registro do getgymsite.com.br (pagamento/dados no Registro.br) — pedido 31598622 em fila.
- [ ] Apos ativo: executar o runbook acima (DNS + caixa + Apollo + warmup).
- [ ] Confirmar o provedor de envio da caixa contato@ para fechar o include do SPF.
- [ ] Definir ICP (perfil de cliente ideal) e as sequencias de outbound (copy alinhada ao sigilo de fontes e LGPD).
- [ ] Garantir opt-out/descadastro em todas as sequencias.

## Constraints

- LGPD: sem coletar/usar dados pessoais sensiveis de terceiros fora de base legal; respeitar opt-out.
- Sigilo de fontes: a copy de outbound NAO menciona as fontes de dados nem categorias de metodo — vende beneficio (bases publicas + modelagem proprietaria).
- Fase 0: sem precos fixos na abordagem (diagnostico inicial gratuito; condicoes apos teste).
- Nao criar contas, registrar dominios, nem inserir senhas em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita; proposta-primeiro para cada registro.
- Nao reproduzir segredos (chaves DKIM, tokens) nem dados pessoais (CPF) neste repo.
