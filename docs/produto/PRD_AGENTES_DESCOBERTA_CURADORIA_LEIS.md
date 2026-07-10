# PRD — Agentes de Descoberta: curadoria de leis por especialidade

## Em uma frase

Criar **um agente de descoberta por especialidade** (Obras, Arquitetura, Regulatório), rodando sozinho em horário agendado, que **encontra as leis que faltam, confere na fonte oficial e prepara o material** para alimentar os assistentes — sem um humano ter que pesquisar cada lei à mão.

## Por que — o que aprendemos

Tentamos, ao vivo no chat, achar a regra de uma cidade e o link da lei. Falhou três vezes: uma citação de lei que não existia (veio de uma pesquisa automática que errou), um documento oficial ilegível e um link que dava erro 404. **Verificar direito exige tempo, várias tentativas e olho humano** — coisa que não cabe numa conversa de segundos.

A conclusão: a parte difícil (achar a lei certa, confirmar que o link abre a norma, extrair o número correto) tem que acontecer **antes**, offline, com calma e revisão — e não na hora que o dono de academia pergunta. O assistente do chat só **mostra** o que já foi conferido.

## Objetivo

Manter a base de conhecimento de cada especialidade **completa, correta e com fonte**, crescendo sozinha por trás — de forma que o assistente responda rápido e sempre com material verificado.

## Como funciona

### Duas frentes de trabalho (não é uma ou outra — são as duas)

**1. Proativo — cura o núcleo conhecido.** Coisas que já sabemos que precisamos, lista finita, curadas antes de alguém perguntar:
- Regulatório: os 27 CREFs regionais, Lei 9.696, anuidades.
- Obras / Arquitetura: as normas nacionais (NBR) — conjunto fechado.
- Municipal: os Códigos de Obras das **cidades-alvo** (capitais + as mais procuradas), não as 5.570.

Isso dá valor no primeiro dia: cobre o que mais aparece.

**2. Reativo — preenche a cauda pela demanda.** Cidade obscura que ninguém previu entra quando **alguém pergunta e o assistente não sabe**. O agente lê o **registro das perguntas que falharam** e vai atrás dessas.

> **Pré-requisito do reativo:** registrar as falhas — um "diário de buracos": toda vez que um assistente responde "não tenho essa regra", isso fica anotado. Sem esse diário, o reativo é cego. É uma peça pequena, mas tem que existir antes.

### A ordem
1. Começa **proativo** (semeia o núcleo — 27 CREFs é o melhor primeiro passo: fechado e de alto valor).
2. **Reativo** entra depois, quando houver perguntas falhando o bastante para valer a caça à cauda.

### Um agente por especialidade, em horário agendado
Cada agente roda sozinho (ex.: uma vez por semana), pela plataforma de **agentes agendados** da Anthropic (Managed Agents — Scheduled Deployments, hoje em **beta**). A Anthropic hospeda a execução (sandbox gerenciado — não hospedamos infra). A cada rodada: acha a lacuna → pesquisa e **confere offline** → escreve o material → **abre um pedido de revisão (PR)** → um humano aprova → entra na base. **Nunca entra sem revisão humana.**

> **Como se cria (confirmado na doc):** via **API** (`deployments.create`, com o beta header `managed-agents-2026-04-01`) — **não há criação por dashboard/UI**. O prompt canônico abaixo é o conteúdo que vai nessa chamada. Agendamento em cron POSIX + timezone (`America/Sao_Paulo`); teto de 1.000 deployments por organização.

Os três agentes de lei:
- **Descoberta — Obras** (normas de obra + Código de Obras municipal)
- **Descoberta — Arquitetura** (acessibilidade/projeto + Código de Obras municipal)
- **Descoberta — Regulatório** (CREF/CONFEF + licenças)

*Técnico e Mercado ficam de fora deste PRD: não curam lei, curam catálogo e dados de mercado — outra cadência, outro tipo de agente.*

## O prompt canônico (o coração)

Este é o **texto-base do agente**, reusável nas três especialidades — troca só os campos em `[COLCHETES]` e cola no painel da Anthropic (platform.claude.com/dashboard) para criar cada agente agendado. É o mesmo cérebro; muda só o domínio.

```
# Agente de Descoberta — Curadoria de Leis · [ESPECIALIDADE]

## Quem você é
Você é o curador de conhecimento legal da especialidade [ESPECIALIDADE] do GymSite.
Seu trabalho é manter a base que alimenta o assistente de [ESPECIALIDADE] completa,
correta e com fonte — sem um humano pesquisar cada lei à mão. Você NÃO conversa com
clientes; você produz material verificado para a base.

## O que você faz a cada execução
1. IDENTIFIQUE lacunas de cobertura:
   - PROATIVO: percorra a lista-alvo do seu domínio — [LISTA-ALVO: ex. os 27 CREFs / as
     NBRs X, Y, Z / os Códigos de Obras das cidades: São Paulo, Fortaleza, João Pessoa...]
     — e teste, uma por uma, se a base já responde.
   - REATIVO: leia o registro de perguntas que o assistente não conseguiu responder
     [DIÁRIO DE BURACOS] e priorize as que mais se repetiram.
2. Para cada lacuna confirmada (a base realmente não tem a resposta):
   a. PESQUISE a fonte primária oficial — site de governo/conselho/prefeitura, domínio
      oficial (.gov.br, .leg.br, conselho). NUNCA blog, fórum ou agregador.
   b. VERIFIQUE antes de escrever: confirme que a lei/norma existe de verdade, leia o
      texto real, e confirme que a URL ABRE a norma específica. Se a primeira fonte
      parecer errada (artigo com número estranho, lei revogada, PDF ilegível, link que
      não abre), busque de novo. Você ERRA na primeira tentativa — trate toda fonte como
      suspeita até confirmar na origem.
   c. ESCREVA o documento de ingest no formato abaixo.
3. ABRA um Pull Request com três coisas: (1) o documento novo, (2) qual documento antigo
   ele substitui (para purgar), (3) um teste de cobertura proposto. NUNCA ingira direto.

## Regras de ouro (inegociáveis)
- CARIMBO: todo número, norma ou exigência carrega valor · base · fonte · janela.
  Ex.: "R$ 1.569,68 · anuidade PJ · Resolução CONFEF nº 596/2025 · vigência 2026".
- FONTE PRECISA: nomeie a norma — lei nº + ano + artigo. Nunca "art. X" nem nome vago.
- LINK SÓ SE VERIFICADO: inclua uma URL apenas se você CONFIRMOU que ela abre a norma
  específica. NUNCA invente ou adivinhe URL (ex.: chutar /norma/<nº da lei> não resolve).
  Nunca linke o portal genérico. Sem URL verificada → a fonte fica em texto, sem link.
- NUNCA INVENTE: escreva só o que encontrou e conferiu na fonte. Não achou? Escreva que
  não achou — jamais complete o buraco com conhecimento geral do modelo.
- ENTIDADE REPETIDA: se o documento lista entidades parecidas (estados, municípios),
  repita a entidade em CADA frase relevante, para a busca não confundir depois.
- PT-BR sempre. Se a fonte for de Portugal, traduza os termos ("faturação"→"faturamento").

## Formato do documento de ingest
- Título com a entidade explícita (ex.: "Código de Obras — João Pessoa/PB").
- Cada regra em pergunta→resposta, na linguagem de quem pergunta
  ("quantos banheiros para 200 alunos em João Pessoa?").
- Cada resposta com o carimbo completo (valor · base · fonte · janela).
- Cabeçalho declarando FONTE · BASE · JANELA e qual documento antigo isto substitui.

## Limites
- No máximo [N] lacunas por execução (controla custo).
- Só a sua especialidade — não toque nas outras.
- Você NÃO ingere e NÃO purga nada sozinho: só propõe, via PR, para revisão humana.
```

### Como preencher por especialidade

| Campo | Regulatório | Obras | Arquitetura |
|---|---|---|---|
| `[ESPECIALIDADE]` | Regulatório | Obras | Arquitetura |
| `[LISTA-ALVO]` | 27 CREFs, Lei 9.696, anuidades | NBRs de obra (6120, 16280...) + COE das cidades-alvo | NBR 9050/13532 + COE das cidades-alvo |
| Fontes oficiais | confef/cref regionais, prefeituras | ABNT (requisito público), prefeituras/leg | ABNT, prefeituras/leg |

## O que o agente entrega (a cada lacuna)

1. **Documento curado** — a regra em pergunta→resposta, carimbada, com link só se verificado.
2. **Marcação do que purgar** — qual documento velho o novo substitui (curar sem purgar não resolve: o velho vence na busca).
3. **Teste de cobertura proposto** — para a base passar a vigiar aquela lacuna dali em diante.

Tudo num pedido de revisão que um humano aprova antes de entrar.

## O que fica de fora

- Ingerir ou apagar qualquer coisa sem revisão humana.
- Técnico e Mercado (não são lei).
- A tool de busca "ao vivo" no chat: **descartada** — a verificação mora aqui, offline. O chat só mostra o que já foi conferido.
- Cobrir as 5.570 cidades de uma vez: o núcleo é proativo (cidades-alvo), o resto é por demanda.

## O que a plataforma entrega (confirmado na doc oficial)

Apoiamos o desenho no que existe de verdade — verificado contra platform.claude.com:

| Peça | Situação | Uso nosso |
|---|---|---|
| Agente agendado (cron) | ✅ beta, criado via API | o coração — cada agente de especialidade |
| Busca na web + abrir/ler página e PDF | ✅ nativo | achar e conferir a lei (sem página com JavaScript dinâmico) |
| Sandbox gerenciado | ✅ Anthropic hospeda | não cuidamos de servidor |
| Saída estruturada (JSON com schema) | ✅ nativo | trava o formato do doc (carimbo nunca sai incompleto) |
| Lote (batch, ~50% custo) | ✅ | semear os 27 CREFs de uma vez, barato |
| Cache de prompt (~90% em releitura) | ✅ | reusar a base entre rodadas da semana |
| Custo/uso e histórico de execuções | ✅ | controle de gasto e auditoria |
| Avaliações | ⚠️ parcial | Console (lado-a-lado) + autoavaliação do agente; não há eval em lote pronta |

### As duas ressalvas que mudam o desenho

1. **Criação só por API, não por dashboard.** O prompt canônico é o conteúdo da chamada `deployments.create` — não se cola numa tela. (Corrige a ideia de "criar no dashboard".)
2. **Abrir PR no GitHub não é nativo, e MCP local não roda no agente agendado** (só MCP via HTTPS público). Então o passo "abre o pedido de revisão" precisa de **uma ferramenta própria que chama a API do GitHub** (com token), ou um conector MCP hospedado em HTTPS. Não é bicho de sete cabeças — é uma peça a construir, não um botão pronto.

## Riscos e cuidados

- **Agente cita fonte errada** → por isso toda entrega passa por revisão humana antes de entrar; nada é automático.
- **Custo escapando** → agendado (não contínuo) + teto de lacunas por rodada.
- **Fonte oficial fora do ar / ilegível** → o agente registra "não consegui confirmar" e não força; a lacuna fica para a próxima rodada.
- **Falso "buraco"** (a base até tinha, mas a busca não achou) → o teste de cobertura proposto ajuda a distinguir cobertura real de falha de busca.

## Como vamos saber que funcionou

- A base de cada especialidade **cresce toda semana**, começando pelas entidades de maior valor/demanda.
- Perguntas que antes davam "confirme na prefeitura" passam a ter **resposta carimbada**.
- Nenhuma entrada na base sem carimbo completo; nenhum link sem verificação.
- O tempo entre "buraco detectado" e "material pronto para revisão" cai rodada a rodada.

## Primeiro passo sugerido

**Proativo do Regulatório — os 27 CREFs.** Domínio fechado (27), alto valor, fontes oficiais claras (conselhos). É o melhor teste do agente antes de abrir para a cauda municipal.
