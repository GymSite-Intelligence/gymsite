PLAN — Prospeccao / Outbound (Apollo)

Categoria: geracao de leads e e-mail outbound via Apollo.io. Atualizado em 2026-06-14. Nota de privacidade: dados pessoais (CPF/endereco/telefone) NAO sao registrados aqui.

## Objetivo

Estruturar a operacao de prospeccao outbound (academias / donos de negocio fitness) para alimentar o funil do GymSite, a partir de um dominio de envio dedicado de marca, com autenticacao (SPF/DKIM/DMARC) e aquecimento (warmup) antes de disparos em escala.

## Decisao de dominio de envio (2026-06-14)

Avaliamos 3 opcoes para o dominio remetente das sequencias. O remetente que o lead ve e SEMPRE a caixa conectada ao Apollo (o Apollo nao mascara o From).

| Opcao | Marca GymSite no From? | Reputacao | DNS | Veredito |
|---|---|---|---|---|
| gymsite.com.br (raiz do produto) | Sim | Arriscado (cold outbound no dominio principal) | cPanel HostGator | Evitar |
| vectracargo.com.br | Nao | DMARC p=reject; SPF so cobre Cloudflare | Cloudflare (NS) | Inviavel sem ajuste arriscado |
| vectracargo.com | Nao | SPF ja cobre GoDaddy; DMARC p=quarantine | GoDaddy (NS) | Pronto, mas sem marca |
| getgymsite.com.br (marca dedicada) | Sim (marca, sem ser a raiz) | Dominio novo (precisa warmup), isola o produto | cPanel HostGator | ESCOLHIDO |

Decisao: usar getgymsite.com.br — dominio de marca dedicado para outbound, que carrega a marca GymSite sem arriscar a reputacao do dominio raiz gymsite.com.br.

## Provedor de e-mail: Titan (decidido 2026-06-14)

Ao adicionar getgymsite.com.br na hospedagem, o HostGator ja provisionou a zona DNS com e-mail via Titan Email (padrao). Decidimos usar o Titan (Caminho A) — menor atrito, autenticacao de fabrica, boa entregabilidade. A caixa de envio sera contato@getgymsite.com.br, criada no painel Titan pelo usuario.

## Estado dos dominios (verificado via DNS publico em 2026-06-14)

- gymsite.com.br: e-mail Titan (mx1/mx2.titan.email), SPF include spf.titan.email, DMARC p=none. E o dominio do produto — nao usar para cold outbound.
- vectracargo.com.br: MX misto GoDaddy + Cloudflare routing; SPF so include Cloudflare; DMARC p=reject; NS na Cloudflare.
- vectracargo.com: MX GoDaddy; SPF cobre GoDaddy (-all); DMARC p=quarantine; NS na GoDaddy. Subutilizado.
- getgymsite.com.br: REGISTRADO e PUBLICADO no Registro.br (criado 14/06/2026, expira 14/06/2028). Adicionado a hospedagem HostGator (cPanel br1080, document root proprio). Zona DNS criada com e-mail Titan. NS apontados para HostGator (ns1080/ns1081.hostgator.com.br) — delegacao SALVA no Registro.br, em janela de transicao (~2h) para dominio novo. Aguardando propagacao.

## Estado da zona DNS de getgymsite.com.br (cPanel, 2026-06-14)

Autenticacao de e-mail COMPLETA na zona:

- MX: mx1.titan.email (prio 10), mx2.titan.email (prio 20) — Titan.
- SPF (TXT apex): v=spf1 include:spf.titan.email ~all — Titan.
- DKIM: seletor titan1._domainkey publicado pelo HostGator/Titan (chave nao reproduzida aqui).
- DMARC (TXT em _dmarc): ADICIONADO por nos. Politica p=none (monitoramento), rua=mailto:contato@getgymsite.com.br, fo=1, alinhamento relaxed (adkim=r/aspf=r), TTL 3600. Endurecer para quarantine -> reject apos validar relatorios.

## Estado atual do Apollo (verificado)

- Caixa conectada hoje: manager@vectracargo.com.br (IMAP, Padrao) — envio GoDaddy. Setup ~80%.
- Diagnostico da caixa atual: DKIM Bom, DMARC Bom, SPF "Revisar". Por isso migramos para o dominio dedicado em vez de remendar.
- Warmup: ainda nao iniciado. Limites: 50/dia, 6/hora, 600s de atraso.
- Itens de setup ja OK: Assinatura, Limites de envio, Link de descadastro, Subdomain tracking.

## Runbook (apos propagacao dos NS)

1. (FEITO) Adicionar getgymsite.com.br na hospedagem (cPanel HostGator) — zona DNS criada.
2. (FEITO) DMARC publicado em p=none. MX/SPF/DKIM via Titan ja presentes.
3. Verificar propagacao dos NS (esperado: ns1080/ns1081.hostgator.com.br resolvendo).
4. (USUARIO) Criar a caixa contato@getgymsite.com.br no painel Titan (o assistente nao cria conta nem insere senha).
5. (USUARIO) Conectar a caixa ao Apollo (login feito pelo usuario) e definir como caixa de envio das sequencias.
6. Rodar o diagnostico do Apollo (Domain authentication) ate SPF/DKIM/DMARC ficarem "Bom".
7. Iniciar o WARMUP e manter por algumas semanas com volume baixo. So escalar apos warmup saudavel.
8. So entao ligar as sequencias para leads reais.

## Pendencias / proximos passos

- (REGISTRO.BR) Aguardar fim da janela de transicao da delegacao NS (~2h).
- (USUARIO) Criar caixa contato@ no Titan; conectar ao Apollo.
- Apos caixa criada: rodar diagnostico Apollo + warmup.
- Definir ICP e as sequencias de outbound (copy alinhada ao sigilo de fontes e LGPD).
- Garantir opt-out/descadastro em todas as sequencias.
- Plano de endurecimento do DMARC: p=none -> quarantine (pct gradual) -> reject.

## Constraints

- LGPD: sem coletar/usar dados pessoais sensiveis de terceiros fora de base legal; respeitar opt-out.
- Sigilo de fontes: a copy de outbound NAO menciona as fontes de dados nem categorias de metodo — vende beneficio (bases publicas + modelagem proprietaria).
- Fase 0: sem precos fixos na abordagem (diagnostico inicial gratuito; condicoes apos teste).
- Nao criar contas, registrar dominios, nem inserir senhas em nome do usuario.
- Nao publicar/alterar DNS sem autorizacao explicita; proposta-primeiro para cada registro.
- Nao reproduzir segredos (chaves DKIM, tokens) nem dados pessoais (CPF) neste repo.
