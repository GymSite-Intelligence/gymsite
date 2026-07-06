# Operação do Instagram — modelo coworking / executor externo

> Criado 2026-07-04. Expande o `PLANO_MARKETING_LANCAMENTO.md` §10.3. Define como um executor
> externo (coworking, estagiário ou VA) opera o @getgymsite sem descaracterizar a marca nem
> assumir risco factual/de segurança. Claude gera conteúdo; Marcelo aprova o dado sensível.

## 1. Divisão de responsabilidade

| Frente | Claude | Marcelo | Executor (coworking) |
|---|---|---|---|
| Criação de card + legenda + hashtags | **Faz** | revisa | — |
| Dado factual (número do motor, caso) | fonte | **aprova** | não toca |
| Publicação e agendamento | — | supervisiona | **executa** |
| Stories diários (enquete, bastidor) | sugere roteiro | — | **executa** |
| 1º nível de DM / comentário | prepara FAQ | escala técnico | **responde** |
| Resposta a crítica cética | redige com dado | **aprova/publica** | encaminha |
| Métricas semanais | — | decide | **coleta e reporta** |

Regra dura: **P1/P2/P3 com número nunca é criado pelo executor** (erro factual mancha a marca).
Voz da marca em crítica = Marcelo + Claude.

**SLAs do Marcelo** (a meta do executor só vale se estes forem cumpridos):

- Pacote da semana aprovado até **quinta EOD** (chega ao executor na sexta).
- DM técnica/crítica escalada: resposta em **24h úteis**.
- Atualização de FAQ (§5) quando pricing ou escopo mudar — no mesmo dia da mudança.

## 2. Onboarding do executor (antes do 1º post)

1. Ler `docs/produto/brand/README.md` + `instagram/COMO_USAR.md` (template, paleta, CTA único).
2. Receber o pacote-padrão de cada post: imagem/vídeo final + legenda + hashtags + horário.
3. FAQ de DM (abaixo) + regra de escalonamento.
4. Assinar checklist de "não postar sem aprovação" para conteúdo com dado.
5. Assinar **termo de confidencialidade** antes de qualquer acesso: DMs contêm dados pessoais
   de leads (cidade, ponto, CNPJ) — tratamento sob LGPD, proibido copiar/exportar conversas.

## 3. Controle de acesso (segurança — não negociar)

- Executor **nunca** recebe senha nem token da conta Meta principal.
- Acesso padrão: **ferramenta de agendamento externa (Later ou Buffer) com seat próprio** — o
  Meta Business Suite não tem papel realmente limitado para terceiros. Fallback: convite como
  **Editor** na Página/conta comercial — nunca Admin.
- 2FA obrigatório na conta principal, controlado por Marcelo.
- Revogar acesso imediatamente se o executor sair.
- Publicação via Graph API (quando ligar) usa token de Marcelo em secret — executor não vê.

## 4. Cadência operacional semanal

| Dia | Executor faz |
|---|---|
| Sexta anterior | Recebe o pacote da semana (3 posts + roteiro de stories) e **agenda os 3 posts na hora** |
| Seg / Qua / Sex | Confere que o post agendado saiu no horário definido |
| Diário | 2–3 stories; responde DM/comentário em até 4h úteis |
| Sexta | Fecha o report de métricas (§6) e manda pro Marcelo |

Agendar tudo na sexta é a contingência: se o executor faltar, os posts saem sozinhos — só
stories e DM ficam descobertos (Marcelo assume ou aceita o gap do dia).

Horário útil = **seg–sex, 9h–18h BRT**. As metas de resposta contam dentro dessa janela.

Estimativa de carga: **5–7h/semana** (agendamento + stories + DM + report). Dimensiona a
contratação — estagiário ou VA por hora; pacote de coworking só se vier com outras entregas.

## 5. FAQ de DM (1º nível — executor responde)

- "É pago?" → "A análise do seu ponto é gratuita no momento. É só fazer pelo link da bio."
- "Como funciona?" → "Você responde poucas perguntas e a IA cruza dados públicos (CNPJ, Maps, IBGE) do bairro. Link na bio."
- "Atende minha cidade?" → "Sim, cobre o Brasil todo. Faz o teste no link da bio."
- Pergunta técnica de metodologia/número → **escalar para Marcelo**, não improvisar.
- Crítica/ceticismo → encaminhar para Marcelo responder com dado.

Dono do FAQ: **Marcelo**. Fato perecível (ex.: "gratuita no momento") — quando pricing/escopo
mudar, Marcelo atualiza no mesmo dia e o executor confirma leitura antes de responder de novo.

**Moderação** — o que o executor pode fazer sozinho vs. não pode:

- Pode: ocultar spam evidente, bloquear bot, ocultar ofensa gratuita (palavrão, ataque pessoal).
- **Não pode**: apagar/ocultar crítica legítima (mesmo dura) — vira pauta pro Marcelo; nem
  responder concorrente provocando — sempre escalar.

## 6. KPIs do executor (report semanal, 30 min)

- Posts publicados no prazo (meta: 3/3).
- Stories/dia (meta: 2–3).
- Tempo médio de 1ª resposta a DM (meta: < 4h úteis).
- DMs recebidas × encaminhadas ao Marcelo.
- Alcance/perfil visitado e cliques no link da bio (do Insights).

Controle de qualidade (não só velocidade): Marcelo lê **5 DMs respondidas por semana**
(spot-check de tom e precisão). Report sempre no mesmo template/planilha, pra comparar
semana a semana.

## 7. Quando ativar (gatilhos, não datas)

Fase 0 começa **solo** (Marcelo + Claude). Ativar executor quando:
- cadência 3/semana + stories ficou insustentável por 2 semanas seguidas; **ou**
- volume de DM passou do que dá pra responder no mesmo dia.

Antes disso, delegar é custo sem necessidade.

**Entrada e saída:**

- Período de teste: **2 semanas** com revisão total (Marcelo confere todo post, story e DM).
- Gatilho de desligamento: 2 semanas seguidas abaixo da meta de prazo (§6), ou 1 violação da
  regra dura (§1) / do controle de acesso (§3) — nesse caso, imediato.
- Offboarding: revogar seat da ferramenta de agendamento + remover Editor da Página + trocar
  senha se houve qualquer compartilhamento indevido.
