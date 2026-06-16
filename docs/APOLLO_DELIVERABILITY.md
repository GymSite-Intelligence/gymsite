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
