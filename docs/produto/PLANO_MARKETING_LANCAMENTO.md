# Plano de Marketing — Lançamento MVP (Fase 0)

> Criado 2026-07-03. Par do `MODELO_NEGOCIO.md` (Fase 0: 60 dias sem cobrança, validação).
> Canal principal: Instagram (o segmento fitness mora lá). Público = quem ABRE/GERE academia,
> não aluno de academia.
> Regra: valores financeiros são ranges herdados do `MODELO_NEGOCIO.md` §4.1 — não são fatos.

---

## 1. Objetivo do lançamento

O MVP **não vende** — valida. Sucesso da Fase 0 é funil medido + entrevistas feitas, não receita.

| Meta Fase 0 (60 dias) | Alvo sugerido (a calibrar) |
|---|---|
| Análises gratuitas concluídas no site | 100–300 |
| Taxa chat iniciado → análise concluída | ≥ 40% |
| Análise → cadastro na ferramenta | ≥ 15% |
| Entrevistas willingness-to-pay | 5–10 por ICP (PD-001) |
| Seguidores Instagram | secundário — não é KPI de decisão |

---

## 2. Público e mensagem

### ICPs (do `MODELO_NEGOCIO.md` §5) por canal

| ICP | Canal primário | Papel na Fase 0 |
|---|---|---|
| Empreendedor 1ª unidade | **Instagram** | Alvo central do conteúdo e da análise gratuita |
| Dono de rede local (2–10) | Instagram + WhatsApp | Alvo das entrevistas WTP (tier Rede, PD-005) |
| Consultor fitness | Instagram + direct | Canal futuro (white-label) — cultivar relação |
| Franqueadora | LinkedIn / outbound direto | FORA do Instagram; não perseguir na Fase 0 |

### Mensagem única (posicionamento)

**"Não abra academia no bairro errado."**
Erro de ponto custa R$ 300K+; a análise com dados reais (CNPJ, Maps, IBGE, reviews) custa zero
no MVP. Ancoragem contra: "achismo", "planilha do amigo", consultoria de R$ 15–50K que demora
30–60 dias.

Prova concreta que já existe no produto: caso Cocó/Fortaleza — parecia MÉDIO com margem 24%,
motor V3 mostrou INVIÁVEL (ocupação 40%, prejuízo R$ 16K/mês). **Esse tipo de virada é o
conteúdo mais forte que temos.**

---

## 3. Instagram — plano operacional

### Setup (semana 0)
- Handle sugerido: `@getgymsite` (casa com o domínio getgymsite.com.br). Bio: promessa + CTA
  único → link da análise gratuita (www.gymsite.com.br).
- Identidade visual: reaproveitar tokens da landing (petroleum deep + lime, Space Grotesk).
  ✅ R6 DECIDIDO (2026-07-04): **cor de marca = `#84cc16`** (lime-500, o mesmo dos ícones em
  `src/components/site/gymsite-icons.tsx`). O token `--lime` (`oklch(0.88 0.22 135)`) deve ser
  alinhado a esse hex. Ver §10.6.
- Conta comercial + WhatsApp Business vinculado (follow-up de lead; `LeadAccessPage` já existe).

### 4 pilares de conteúdo

| Pilar | % | O que é | Fonte interna (custo ~zero) |
|---|---|---|---|
| **P1 Dados do mercado** | 35% | "Bairro da semana": saturação, academias/10K hab, renda, veredito | O próprio pipeline: charts A9 (gauge, radar, receita×resultado) viram card |
| **P2 Educação de abertura** | 30% | CAPEX real por modelo, teto de ocupação do aluguel, Fator R, ticket piso | Motor V3 / `parametros_metodologia.py` — cada regra do motor é um post |
| **P3 Casos e provas** | 20% | Análise real anonimizada: APROVADO vs INVIÁVEL e por quê | Relatórios gerados (anonimizar bairro/CNPJ) |
| **P4 Produto/bastidores** | 15% | Como a IA analisa; 8 fontes de dados; demo do chat | Landing já tem a narrativa (grid de 8 fontes da New Page) |

### Calendário editorial (mínimo viável, sustentável solo)

| Dia | Formato | Pilar |
|---|---|---|
| Seg | Carrossel (5–7 cards) | P1 dados do bairro |
| Qua | Reel 30–45s | P2 educativo ("o erro nº1 ao alugar galpão pra academia") |
| Sex | Carrossel ou estático | P3 caso / P4 produto (alternar) |
| Diário | 2–3 stories | Enquete ("abriria academia nesse bairro?"), bastidor, repost |

3 posts/semana é o piso do plano original — manter 8 semanas antes de julgar alcance.

### 6 exemplos prontos de post

1. **Carrossel P1:** "X academias para cada 10 mil habitantes no [bairro]. Saturado ou
   oportunidade? Analisamos com dados públicos →" (gauge do A9 como card final + CTA análise grátis)
2. **Reel P2:** "Seu aluguel pode reprovar sua academia antes de você abrir. A conta que ninguém
   faz: ocupação máxima de 12–15% do faturamento." (regra do guardrail V3, quadro branco/talking head)
3. **Carrossel P3:** "Essa academia ia dar prejuízo de R$ 16 mil/mês — e o plano de negócio dizia
   lucro. O que a análise pegou:" (caso Cocó anonimizado, 5 cards)
4. **Reel P4:** screen-record do chat da análise gratuita respondendo em tempo real. "3 minutos,
   sem cadastro, sem consultor de R$ 15 mil."
5. **Carrossel P2:** "Quanto custa DE VERDADE abrir uma academia em 2026: obra, equipamento,
   contingência" (chart capex_stacked por modelo low/mid/premium)
6. **Estático P1:** mapa de calor do Brasil (asset `brazil-heatmap` da landing) + "onde o fitness
   cresce mais rápido" (dado CNPJ de entrantes)

### Hashtags (mix, 8–12 por post)
Nicho: `#abriracademia #gestaodeacademia #mercadofitness #negociofitness #franquiafitness`
Médio: `#empreendedorismofitness #academia #donodeacademia`
Amplo (1–2): `#empreendedorismo #smartfit`

---

## 4. Ads — Fase 0 = teste pequeno, não escala

Orgânico primeiro. Se testar pago (opcional, a partir da semana 4):

| Campanha | Plataforma | Objetivo | Budget teste | Segmentação |
|---|---|---|---|---|
| Análise gratuita | Meta Ads | Tráfego → landing/chat | R$ 300–600/mês | 25–50, interesses: gestão de academias, franquias, empreendedorismo fitness; capitais |
| Intenção alta | Google Search | "como abrir uma academia", "quanto custa abrir academia" | R$ 300–500/mês | BR, exact/phrase; CAC esperado R$ 80–200 (`MODELO_NEGOCIO` §4.1) |
| Remarketing | Meta | Quem abriu o chat e não concluiu | R$ 100–200/mês | Pixel na landing (verificar instalação) |

Criativo do ad = post que melhor performou organicamente (não inventar criativo do zero).
**Não escalar ads antes do funil análise→cadastro estar medido** — senão compra tráfego sem saber
o que converte.

---

## 5. Prova social e avaliações

Fase 0 (produto sem base de clientes — foco em depoimento, não em Maps):
1. Toda entrevista WTP termina pedindo 1 frase de depoimento autorizada (nome + cidade).
2. Primeiros 20 usuários da análise gratuita: follow-up por WhatsApp pedindo feedback → os bons
   viram story/destaque "Quem usou".
3. Google Business Profile: criar, mas é secundário (SaaS descoberto por busca/social, não por Maps).
4. Avaliação negativa/cética (vai acontecer): responder com dado, nunca defensiva — "a análise usa
   fontes públicas X/Y/Z, refaça com outro bairro e compare".

---

## 6. CTA e funil

**CTA único primário em TUDO: "Faça a análise gratuita do seu ponto"** → chat da landing.
Um funil só, medível de ponta a ponta:

```
Instagram → landing (www.gymsite.com.br) → ChatAgent (análise 3-tier N3)
  → resultado + convite → cadastro (getgymsite.com.br) → relatório completo → [Fase 2: pagar]
```

- CTAs secundários (só stories/bio): "Receba o guia de abertura" (futuro lead magnet), WhatsApp.
- Teste A/B (semana 3+): "Analise seu ponto grátis" vs "Descubra se seu bairro comporta uma
  academia" — medir clique→chat iniciado.
- ⚠️ Dependência técnica: manter o `<ChatAgent>` como mecanismo de conversão na migração da New
  Page (regressão R1 do plano de refatoração — CRÍTICA).

---

## 7. KPIs (revisão semanal, 30 min)

| Funil | Métrica |
|---|---|
| Topo | Alcance/perfil visitado; clique no link da bio |
| Meio | Chats iniciados; % concluídos; análises geradas |
| Fundo | Cadastros; relatórios completos gerados; entrevistas WTP agendadas |
| Saúde | Custo por análise concluída (se ads ativo) |

Instrumentação: telemetria por módulo é pré-requisito da Fase 0 (`MODELO_NEGOCIO.md` §6) —
`chat_interacoes` já coleta desde 2026-06-12; falta consumo por relatório/módulo.

---

## 8. O que NÃO fazer na Fase 0

- Não cobrar (nem "founder price") — contamina os dados de WTP.
- Não sistema de créditos (decidido: Fase 2, PD-003 jurídico aberto).
- Não outbound pra franqueadora (Enterprise é Fase 3).
- Não escalar ads sem funil medido.
- Não abrir segundo canal (TikTok/YouTube) antes do Instagram ter 8 semanas de dado.

## 9. Sequência de execução

1. **Semana 0:** decidir cor de marca (R6) → criar conta + bio + 9 posts de estoque → pixel/UTMs
   na landing → telemetria por módulo.
2. **Semanas 1–4:** cadência 3 posts/sem + stories; agendar entrevistas WTP com quem concluir análise.
3. **Semanas 4–8:** teste de ads pequeno; A/B de CTA; primeira revisão de KPIs → decidir dobrar
   orgânico vs ligar pago.
4. **Fim da Fase 0:** fechar PD-001/PD-002/PD-005 com os dados; decidir price points; aí sim Fase 1.

---

## 10. Claude Design — produção do conteúdo visual do Instagram

> Adicionado 2026-07-04. **Ponto de partida: zero** — não existe conta @getgymsite, materiais,
> nem executor. Único ativo pronto: app na Meta com permissão Graph (a reaproveitar). Execução da
> Fase 0 = Marcelo solo + Claude gerando conteúdo; coworking/terceiro fica como opção futura.

### 10.0 Ordem de construção (do zero)

Nada existe — a sequência importa. Fazer nesta ordem; cada passo destrava o próximo:

1. **Decidir a cor de marca (R6).** Bloqueia todo o resto — sem cor travada, todo template vira
   retrabalho. Uma cor, decidida, registrada em §3.
2. **Criar o kit de identidade mínimo.** Claude gera (via Artifact) um "starter kit": paleta final,
   par tipográfico (Space Grotesk/Sora), 1 template de carrossel, 1 de story, 1 de card de dado.
   É o molde de que tudo sai depois.
3. **Criar a conta Instagram Business.** Handle `@getgymsite`, bio (promessa + CTA único → link),
   converter para conta comercial e vincular a uma Página do Facebook (necessário para o app Meta).
4. **Vincular ao app Meta existente.** Confirmar escopos (§10.4) e gerar token de longa duração.
5. **Gerar os 9 posts de estoque** com o prompt-brief (§10.2) — a partir do caso Cocó e dos charts
   do pipeline. Só depois disso começa a cadência.
6. **Ligar pixel + UTMs na landing** (§9) antes do 1º post, senão o conteúdo sai cego.

### 10.1 Como o design (Claude) nos ajuda

Começando do zero e solo, sem designer, o Claude é o que torna a Fase 0 viável — não é luxo, é o
substituto de estúdio:

O gargalo real da Fase 0 não é ideia de post — os 4 pilares e 6 exemplos (§3) já resolvem o
*quê*. O gargalo é **produzir volume visual consistente sozinho, de graça, sem virar designer**.
É aí que o Claude entra, em quatro frentes:

1. **Templates a partir dos dados que já temos.** Os charts do pipeline (gauge/radar/receita×resultado
   do A9, `capex_stacked`, `brazil-heatmap`) são a matéria-prima do P1/P2/P3. O Claude transforma cada
   um em card de carrossel Instagram-ready (1080×1350) via **Artifact HTML/SVG** — export direto como
   imagem, sem Canva, sem Figma. A skill `dataviz` garante que o gráfico segue um sistema de cor único.
2. **Sistema de design travado = identidade coerente.** Uma vez decidida a cor de marca (R6, ainda
   pendente) e fixados os tokens (petroleum deep + lime, Space Grotesk/Sora), todo post sai do mesmo
   molde. Isso mata o risco nº1 de conta solo: cada post parecer de uma marca diferente.
3. **Estoque da semana 0 em horas, não semanas.** A sequência de execução (§9) pede 9 posts de
   estoque antes do lançamento. O Claude gera os 9 num lote a partir do prompt-brief (§10.2).
4. **Adaptação de formato barata.** Mesmo dado vira carrossel, story (enquete "abriria academia
   nesse bairro?") e legenda de reel — sem retrabalho manual.

**Limite honesto:** o Claude produz o *estoque base* e os *templates de dados*. Não substitui edição
de vídeo (reels P2/P4 exigem talking-head/screen-record reais) nem direção de arte fina. O objetivo é
tirar 80% do trabalho repetitivo da frente, não fingir estúdio.

### 10.2 Prompt-brief editorial (fonte de verdade para gerar qualquer post)

Este bloco é reutilizável: cola no início de cada pedido de geração de post para o Claude entender o
editorial sem reexplicar. Manter versionado neste arquivo — se o editorial mudar, muda aqui.

```
Você é o designer de conteúdo do @getgymsite (GymSite Intelligence).

MARCA
- Produto: análise de viabilidade de ponto para quem ABRE/GERE academia (não aluno).
- Posicionamento único: "Não abra academia no bairro errado." Erro de ponto custa R$ 300K+;
  nossa análise com dados reais (CNPJ, Google Maps, IBGE, reviews) custa zero no MVP.
- Ancoragem: contra achismo, "planilha do amigo" e consultoria de R$ 15–50K que demora 30–60 dias.
- Tom: técnico mas direto, sem jargão vazio; número é o herói; nunca hype fitness genérico.

IDENTIDADE VISUAL
- Cores: fundo petroleum deep (#0e1a1f aprox / oklch 0.18 0.03 215); destaque lime #84cc16;
  texto quase-branco. Petroleum+lime manda em TODO card. As 5 cores de setor (azul/esmeralda/
  âmbar/rosa/violeta) SÓ em conteúdo P4 que mostra o swarm — nunca fora disso.
- Tipografia: Space Grotesk. Números grandes, muito respiro, UM dado por card.
- Mascote: ícone-robô line-art (stroke lime) no canto como etiqueta de pilar; capa de carrossel
  sempre tem o robô do pilar.
- Formato carrossel: 1080×1350, 5–7 cards, último card = CTA "Faça a análise gratuita do seu ponto".

PILARES (peso)
- P1 Dados do mercado (35%): "bairro da semana", saturação, academias/10K hab, veredito.
- P2 Educação de abertura (30%): CAPEX real, teto de ocupação do aluguel (12–15% do faturamento),
  Fator R, ticket piso. Cada regra do motor V3 é um post.
- P3 Casos e provas (20%): análise real ANONIMIZADA, APROVADO vs INVIÁVEL e por quê.
  Caso âncora: Cocó/Fortaleza — parecia margem 24%, motor mostrou prejuízo R$ 16K/mês.
- P4 Produto/bastidores (15%): como a IA analisa, 8 fontes de dados, demo do chat.

REGRAS DURAS
- Todo número factual vem do motor V3 / relatório real — NUNCA inventar dado.
- P3: anonimizar bairro e CNPJ antes de publicar (LGPD).
- CTA único primário em tudo: "Faça a análise gratuita do seu ponto" → link da bio.
- Entrega: HTML/SVG em Artifact, 1 card por seção, pronto para export PNG.

TAREFA
[descrever o post: pilar, dado de origem, formato]
```

### 10.3 Execução na Fase 0: Marcelo solo (coworking = opção futura)

**Decisão:** na Fase 0 a operação é solo — Marcelo executa, Claude gera o conteúdo. Terceirizar
(coworking, estagiário, VA) só quando o volume ou o alcance justificar, não antes de haver dado.

| Frente | Fase 0 (solo) | Como o Claude reduz a carga |
|---|---|---|
| Criação de card + legenda + hashtags | Marcelo pede, Claude entrega | Gera do prompt-brief (§10.2); Marcelo só revisa |
| Publicação e agendamento | Marcelo | Posts saem prontos p/ upload (manual ou Graph §10.4) |
| Stories diários | Marcelo | Claude sugere roteiro/enquete; publicação manual |
| DM / comentário / avaliação cética | Marcelo | Claude prepara FAQ e respostas-modelo com dado |

**Quando avaliar delegar (gatilhos, não datas):** cadência de 3/semana + stories virou insustentável
por 2 semanas seguidas; OU volume de DM passou do que dá pra responder no mesmo dia. Aí sim entra a
opção de executor externo.

**Se um dia delegar (coworking/terceiro) — regras que já ficam registradas:**
- Executor assume só **publicação, agendamento, stories e 1º nível de DM**.
- **Nunca** delegar criação de P1/P2/P3 com números (erro factual mancha a marca) nem resposta a
  crítica cética — isso é voz da marca, fica com Marcelo+Claude.
- Controle de acesso: executor publica via ferramenta de agendamento ou perfil com papel limitado,
  **nunca** com token/senha da conta Meta principal.
- Pré-requisito de delegação: brief escrito + FAQ de DM + checklist "não postar P2/P3 sem aprovação".

### 10.4 Publicação via Meta Graph API (app já existe, resto é do zero)

Único ativo pronto: o **app na Meta com permissão Graph**. Falta o que fica *em cima* dele — conta IG
Business, Página FB, vínculo e token. Passos para ativar (parte do §10.0, item 3–4):

1. Criar/converter a conta `@getgymsite` para **Instagram Business** e vincular a uma **Página do
   Facebook** (o Graph publica via Página, não direto no perfil).
2. No app existente, confirmar/solicitar escopos: `instagram_content_publish`, `instagram_basic`,
   `pages_read_engagement`, `pages_show_list`.
3. Gerar **token de longa duração** (renova a cada ~60 dias); guardar como secret (padrão do projeto:
   Secret Manager, **nunca** em código).

Fluxo de publicação depois de ativo:

```
Claude gera card (Artifact) → render PNG → upload via Instagram Content Publishing API
  → cria container de mídia → publica ou agenda
```

Limites e pegadinhas:
- **25 posts/24h** por conta via API — folgado para 3/semana.
- Carrossel e Reels têm endpoints próprios; **Stories não são publicáveis por API** de forma estável
  → stories ficam manuais (Marcelo).
- **Decisão de fase: na Fase 0 NÃO automatizar.** Começando do zero e solo, o valor está em criar a
  conta e postar à mão (Claude gera → Marcelo publica pelo app). Ligar o pipeline Graph só quando o
  volume justificar — automatizar cedo é manter integração sem saber se o conteúdo converte (mesmo
  erro do "não escalar ads sem funil medido", §4).

### 10.5 Considerações adicionais ao plano (Claude)

1. **A cor de marca (R6) é bloqueador de tudo aqui.** Sem cor travada, todo template gerado vira
   retrabalho. É a primeira ação da semana 0 (§9) — reforçado: nada de design em escala antes disso.
2. **O caso Cocó é ouro subutilizado.** É a prova mais forte (§2) e serve P1, P2 e P3. Sugiro fazer
   dele o **primeiro carrossel de estoque** e o criativo candidato nº1 para o teste de ads (§4).
3. **Risco factual > risco estético.** Um post bonito com número errado do motor é pior que um post
   simples correto. Por isso a separação do §10.3 põe o dado sempre sob Claude+Marcelo.
4. **Reels são o buraco do plano — e solo pesa mais.** P2/P4 dependem de vídeo (talking-head,
   screen-record do chat) que o Claude não produz e que Marcelo teria de gravar sozinho. Risco real
   de furar a cadência. Mitigação para começar: substituir reel por **carrossel animado + voz-off**
   (Claude gera os cards; edição leve), e só migrar para talking-head quando a rotina firmar.
5. **Fechar o loop de telemetria.** UTMs por post (§9) + `chat_interacoes` já ativo permitem saber
   *qual card* trouxe chat iniciado. Sem isso, gerar 9 posts com Claude vira volume cego.

### 10.6 Ativos de marca que já existem no repo (ícones/mascote)

Auditoria do `gym-insight-hub` (2026-07-04) achou dois ativos prontos que encurtam o starter kit
(§10.0) — não começamos do zero visual, começamos do zero de *conta*.

**a) Design tokens reais** (`src/styles.css`) — a marca já é código, não achismo:
- Fundo: petroleum deep `oklch(0.18 0.03 215)`; card `oklch(0.22 0.035 215)`.
- Destaque: `--lime` / `--primary` `oklch(0.88 0.22 135)` + `--lime-glow` `oklch(0.92 0.2 130)`.
- Petroleum médio `oklch(0.42 0.08 210)`. Fonte: **Space Grotesk**.
- Uso no Instagram: fundo petroleum + número/CTA em lime + texto quase-branco. É o molde de todo card.

**b) Mascote — modelo primário (raster) é o oficial do Instagram.** ⚠️ Correção 2026-07-04: existem
DUAS famílias e elas não são intercambiáveis:
- **Flat SVG** (`docs/agente/gymsite_agents/icons/*.svg` + `gymsite-icons.tsx`) = versão simples,
  **só UI do app**. NÃO usar no Instagram (fogem do modelo primário).
- **Modelo primário (raster)** = robô fitness MUSCULOSO (corpo de atleta, circuito verde, dentro do
  pino lime+slate), estilo ilustração premium. É a arte de marketing. Vive em
  `docs/produto/brand/mascotes/` (PNG transparente 1080). Recriação/regeneração via
  `docs/produto/brand/PROMPT_BASE_MASCOTE.md` (modelo de imagem, não SVG à mão).

Regra: todo mascote de setor é o MESMO personagem — muda só o objeto na mão. Logo oficial em
`pdf/assets/logo-gymsite.png`. Kit completo em `docs/produto/brand/README.md`.

Anatomia do crachá: **pino de localização** (metade lime `#84cc16` + metade slate `#1e293b` — casa
com o tema "bairro"), objeto temático por setor.

| SVG | Objeto | Vira post de… |
|---|---|---|
| `dados.svg` | robô + gráfico de barras | P1 dados do bairro |
| `financeiro.svg` | baú de moedas + seta ↑ | P2 CAPEX / ROI |
| `contabilidade.svg` | prancheta + ábaco | P2 Fator R, CNPJ |
| `marketing.svg` | alvo + megafone | P1 saturação / posicionamento |
| `conhecimento.svg` | livro + engrenagem (RAG) | P4 como a IA analisa |
| `tecnico.svg` | haltere + prédio | P2 obra / equipamento |
| `mercado.svg`, `arquiteto.svg`, `engenheiro.svg`, `regulatorio.svg` | site degustação | P4 / bastidores |

**Dois modos de uso no feed:**
- **Sticker** (feed dark): remover o fundo blueprint → pino + robô flutuam sobre petroleum. Modo
  padrão de card e avatar. Mantém o grid coeso.
- **Blueprint completo** (perfil, capa de P4, "conheça o swarm"): SVG inteiro com a grade azul.

**c) Template base oficial já existe** (`docs/produto/brand/instagram/desingn-base-instagram.png`).
Define paleta mestra, tipografia, post feed 1:1, story 9:16 e carrossel 4 painéis. ⚠️ Usa **fundo
split** (metade dark slate, metade lime), não petroleum cheio — alinhar o starter kit a isso ao gerar
os posts. Duas famílias de mascote: **setor** (`brand/icons/`) e **atividade/exercício**
(`brand/mascotes/`). R6: apareceu 3º verde `#8dc63f` (assinatura de e-mail) — decisão mantida em
`#84cc16`, alinhar a assinatura. Kit completo catalogado em `docs/produto/brand/`.

**Como os ícones ajudam as postagens:**
1. **Mascote recorrente = reconhecimento de feed.** O robô-linha vira a assinatura visual da conta;
   aparece no card de capa de cada carrossel e no destaque de stories. Feed coeso sem designer.
2. **Ícone = etiqueta de pilar.** Cada pilar (§3) ganha seu robô no canto do card — o seguidor
   aprende a ler "isto é post de dados / de dinheiro" antes de ler o texto.
3. **Combustível direto de P4.** A narrativa "8 fontes / swarm de 23 agentes" (bastidores) já tem
   rosto: os 6 robôs + as 5 cores de setor viram um carrossel "conheça a equipe de IA que analisa
   seu ponto".
4. **Custo zero e escalável.** São SVG — o Claude reusa o mesmo path em qualquer resolução de card,
   story ou avatar.

**✅ Decisões de marca (2026-07-04):**
1. **Cor de marca = `#84cc16`** (lime-500). R6 fechado. Token `--lime` no `styles.css` a alinhar.
2. **Regra de cor do feed:** petroleum + lime manda em TODO o feed (grid coeso). As 5 cores de setor
   do `INDEX_HANDOFFS.md` (Dados `#3b82f6`, Financeiro `#10b981`, Contabilidade `#f59e0b`,
   Conhecimento `#f43f5e`, Marketing `#8b5cf6`) entram **só** dentro de conteúdo P4 que mostra o
   swarm — onde a variedade de cor *significa* algo. Fora de P4, robô sempre em lime sobre petroleum.

Ambas as regras estão embutidas no prompt-brief (§10.2) e no starter kit visual.
