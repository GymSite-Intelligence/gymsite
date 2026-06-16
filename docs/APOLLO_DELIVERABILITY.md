# Apollo — Diagnóstico de Entregabilidade da Sequência Outbound

Registro da verificação feita na conta Apollo sobre o impacto da
configuração de domínio na sequência ativa. Documento descritivo; nenhuma
configuração de DNS, conta ou warmup foi alterada — todos os ajustes abaixo
são ações manuais do responsável.

## Sequência ativa

- Nome: "GymSite Intelligence — Expansão Fitness (Redes/Franquias)".
- É a única sequência ativa na conta.
- Cadência: 4 e-mails (dias 0, 3, 8 e 14). Conjunto de regras "Default".
- Contatos: 4, todos no estágio Ativo / Etapa 1 / Cold
  (Bianca Amorim, Fabio Rodrigues, Sergio Camargo, Marcel Gandra).
- Nenhum e-mail entregue até o momento (estatísticas zeradas / N/A).

## Remetente usado

A sequência envia pela caixa de e-mail padrão da conta, que é
`manager@vectracargo.com.br` (marcada como "Padrão" na Suíte de
Entregabilidade). Não há remetente alternativo definido na sequência.
Confirmado pelo rascunho da sequência, que sai desse endereço.

## Problema identificado

No Diagnóstico de domínio do Apollo:

| Domínio | SPF | DKIM | DMARC |
|---------|-----|------|-------|
| gymsite.com.br (contato@) | Bom | Bom | Bom |
| vectracargo.com.br (manager@) | Revisar | Bom | Bom |

O domínio `vectracargo.com.br` — justamente o remetente da sequência ativa —
está com SPF em estado "Revisar". Como a sequência envia por essa caixa, o
problema de SPF impacta a entregabilidade dos disparos (maior risco de spam
e bounce).

Gargalo adicional (impacta tanto quanto o SPF): a caixa
`manager@vectracargo.com.br` está com warmup não iniciado e limite diário
em 0/50 ("Iniciar aquecimento"). Com limite zerado, a sequência praticamente
não dispara, o que é coerente com nenhum dos 4 contatos ter recebido e-mail.

Atenuantes: o status é "Revisar" (não "Ruim"); DKIM e DMARC dessa caixa estão
"Bom"; e o score de deliverability dela aparece como "88% - Ótima". Não é
bloqueio total, e sim risco/degradação.

Observação importante: `vectracargo.com.br` é o domínio corporativo, não o do
produto. O domínio do GymSite (`gymsite.com.br`) está 100% verde em
SPF/DKIM/DMARC.

## SendGrid / Mailgun

Status "Não configurado". A sequência usa envio direto pela caixa conectada
(mailbox sending), não um provedor de envio em massa. Por isso a saúde do SPF
da própria caixa é o que importa.

## Ações recomendadas (manuais)

1. Opção A (recomendada): trocar a caixa de envio padrão da sequência para
   `contato@gymsite.com.br`, que já está totalmente autenticado e é o domínio
   do produto.
2. Opção B: manter `vectracargo.com.br` e corrigir o registro SPF no DNS —
   incluir o `include:` do provedor de envio, garantir um único registro
   `v=spf1` e terminar com `~all` (ou `-all`).
3. Em qualquer opção: iniciar o warmup e liberar o limite diário da caixa que
   for usada; sem isso o envio continua travado em zero.


---

## Integração Cloudflare × Apollo — funções e ROI

> Seção adicionada para orientar a conexão da API do Cloudflare à operação de entregabilidade no Apollo. Relaciona-se ao SPF "Revisar" de vectracargo.com.br já registrado acima.

### Autenticação (recomendação)

A integração nativa do Apollo pede **API Key + Email** (Global API Key legada — acesso total à conta). Recomenda-se NÃO usar esse método e sim um **API Token com escopo restrito** (Bearer).
- Base da API: `https://api.cloudflare.com/client/v4`
- Header: `Authorization: Bearer <token>`
- Escopo mínimo: **Zone · DNS · Read** (e Write apenas se for aplicar correções).
- A geração e a inserção do token são ação manual do usuário (credencial sensível).

### Funções recomendadas (wrappers sobre a API do Cloudflare)

| Função | Endpoint Cloudflare | O que faz |
|---|---|---|
| `cf_list_zones()` | `GET /zones` | Lista domínios da conta (gymsite, vectracargo) |
| `cf_verify_email_auth(zone)` | `GET /zones/{id}/dns_records` | Valida existência/correção de SPF, DKIM, DMARC |
| `cf_upsert_dns_record(zone,type,name,content)` | `POST`/`PATCH /zones/{id}/dns_records` | Cria/atualiza registro (aplicação requer aprovação humana) |
| `cf_check_dmarc_reports(zone)` | relatórios rua | Agrega alinhamento/spoofing do DMARC |
| `cf_zone_health(zone)` | orquestra as anteriores | Devolve "health score de entregabilidade" por domínio |

Fluxo de **pré-voo**: rodar `cf_verify_email_auth` antes de cada campanha e cruzar com o status do Apollo (warmup, daily limit, deliverability %).

### ROI

O retorno vem de **entregabilidade e proteção de reputação**, não de receita nova mágica:

| Vetor | Impacto |
|---|---|
| Inbox placement | Corrigir SPF/DKIM/DMARC reduz queda em spam → mais aberturas/respostas pelo mesmo volume |
| Redução de trabalho manual | Pré-voo automatizado substitui checagem manual de DNS + diagnóstico Apollo |
| Proteção de domínio | Previne "queima" de domínio (caro e lento de recuperar) |
| Escalabilidade multi-domínio | Mesma função valida novos domínios de envio sem retrabalho |

**Maior impacto isolado no cenário atual:** `cf_verify_email_auth` + correção do SPF de vectracargo.com.br (hoje "Revisar", warmup não iniciado, limite 0/50) — destrava a sequência ativa sem risco de spam.

*Nota: DDL/endpoints a confirmar; nenhuma credencial é incluída. Alterações de DNS são ação manual do usuário.*
