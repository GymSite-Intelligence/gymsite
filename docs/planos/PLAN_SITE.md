# PLAN_SITE.md — Landing Page GymSite Intelligence

> Documento de planejamento do site institucional/landing de captação.
> Tom: acessível e direto (foco: donos de academia / negócios fitness).
> Idioma: PT-BR. Fase 0: SEM preços fixos ("diagnóstico inicial gratuito; condições após teste").
> Sigilo: vender benefício, não método. Falar em "bases públicas + modelagem proprietária", nunca detalhar fontes.

---

## 0. Objetivo e princípios

- **Objetivo da página:** transformar visitante (dono de academia / gestor fitness) em lead qualificado, usando o **agente "isca"** como porta de entrada da conversão.
- **Promessa central:** mostrar onde estão os clientes certos antes de gastar com marketing no escuro.
- **Posicionamento:** inteligência de mercado **vertical para o setor fitness** — diferente dos concorrentes horizontais (geomarketing genérico).
- **Diretrizes:**
  - Linguagem simples, frases curtas, zero jargão técnico.
  - Cada bloco termina com clareza sobre o próximo passo.
  - Conformidade com a LGPD apresentada como diferencial de confiança, não como letra miúda.
  - Nenhum preço; CTA sempre para o diagnóstico gratuito **via agente**.

---

## 0.1 Integração com o agente "isca" (conversão central)

> O CTA da landing **não leva a um formulário estático** — ele abre o agente conversacional já existente no projeto.

**Fluxo de conversão:**
1. Visitante clica no CTA → **abre o agente "isca"** (widget de chat na própria landing).
2. O agente conversa, entende a região/negócio e **demonstra valor** com uma amostra (potencial da região / leitura de concorrência) — sempre respeitando sigilo de fontes, LGPD e Fase 0.
3. Quando há interesse, o agente faz o **gate**: conduz para o **formulário de produção** (campos canônicos do app: UF, município, bairro, tipo de negócio, porte, público-alvo, contato).
4. Lead capturado entra no fluxo do app → geração do relatório de viabilidade.

---

## 0.2 Embed do agente — DECISÃO

**Decisão:** **widget de chat nativo (React)** servido na landing, conversando com o **backend próprio** do projeto (motor conversacional em `services/`, exposto pela `api.py`). **Não** usar iframe direto do Agent Studio na página pública.

### Estado atual do chat (verificado no código)

- **Rota:** `POST /api/assistente/chat` (`api.py`); modelos `AssistenteChatInput` / `AssistenteChatOutput`.
- **Motor:** `services/tinker_bot.chat_async` + `services/tinker_context.build_contexto_chat`; guardrail de fora-de-escopo (`_RESPOSTA_FORA_DE_ESCOPO`).
- **Autenticação:** a API exige **JWT válido** (`_require_authenticated` → `(user_id, org_id)`), ou seja, é **multi-tenant e logada**. Hoje o chat é uma feature **interna do app autenticado**, não um endpoint público.
- **CORS:** `allow_origins = _cors_origins` (configurável — não é `*`).

### O problema: feature logada × landing pública

O visitante da landing é **anônimo** (não tem conta nem org). A rota atual do chat **exige login**, então **não dá para apontar o widget público direto para ela**. É preciso uma camada pública separada — senão, ou a gente expõe a rota autenticada (risco), ou o visitante esbarra num login antes de ver valor (mata a conversão).

### Como materializa no frontend do site (recomendado)

**Criar uma "porta pública" do chat, isolada da rota logada:**

1. **Endpoint público dedicado** (ex.: `POST /api/public/isca/chat`) — *separado* de `/api/assistente/chat`. Reaproveita o **mesmo motor** (`tinker_bot` + guardrails), mas:
   - **Sessão anônima/efêmera** (token de sessão emitido no 1º contato; sem login).
   - **Tenant "público"** dedicado (org_id reservado p/ leads), nunca um tenant de cliente real.
   - **Escopo reduzido:** só "modo isca" (amostra de valor) — não acessa dados de relatórios pagos nem ferramentas internas.
   - **Rate-limit + anti-abuso** (por IP/sessão) e **timeout de sessão** curto.
2. **Widget React na landing** (Cloudflare Pages): bolha de chat no canto inferior direito; os CTAs (Hero, passo 1, CTA final) abrem o widget. O widget só fala com o endpoint público.
3. **Gate de lead:** após demonstrar valor, o agente coleta os **campos canônicos** (UF/município/bairro, tipo de negócio, porte, público-alvo, contato) e **só então** cria o lead. Esse é o ponto em que pedimos consentimento LGPD.
4. **Hand-off para o app autenticado:** o lead capturado entra no fluxo de produção (área logada). Se o usuário virar cliente, aí sim usa o chat completo `/api/assistente/chat` (com JWT).

### Por que não reusar a rota logada direto

- Apontar o front público para `/api/assistente/chat` exigiria distribuir credenciais/JWT no bundle do site → **vazaria acesso ao app inteiro** (multi-tenant). **Inaceitável.**
- Pôr login antes do chat **mata a isca** (o objetivo é justamente capturar quem ainda não tem conta).
- Logo: **mesma engine, porta diferente** — endpoint público com sessão anônima e escopo "isca".

**Arquitetura (alvo):**
```
[Landing Vite/React — Cloudflare Pages]
        │  widget de chat (sessão anônima)
        ▼
[POST /api/public/isca/chat]  ──►  [services/ tinker_bot + guardrails | escopo "isca"]
        │  (rate-limit, tenant público, sem JWT de cliente)
        ▼
  gate → coleta contato → cria LEAD ──►  [app autenticado /api/assistente/chat (JWT) p/ clientes]
```

**Requisitos / guardrails:**
- **CORS:** `allow_origins` do endpoint público travado no domínio do site (ex.: `https://getgymsite.com.br`).
- **Sem segredos no front:** nenhum JWT/API key no bundle; o backend fala com o modelo.
- **Sigilo:** nunca expor fontes, ferramentas, modelo ou projeto; respostas passam pelos guardrails.
- **LGPD:** aviso curto no início do chat + consentimento antes do gate de contato.
- **Fallback:** backend fora do ar → CTA cai para o formulário curto (seção 9).


---

## 0.3 Fluxo de slot-filling do "modo isca" (conversa → gate)

> Objetivo: o agente preenche os **slots canônicos** (mesmos do app) conversando, mostra valor cedo e só pede contato quando o lead já está "aquecido".

**Slots canônicos (verificados no projeto):**
- `uf`, `cidade`, `bairro` (localização)
- `tipo_negocio` (academia / crossfit_box / studio_pilates / studio_funcional / outro)
- `tamanho_preset` (p / m / g) — opcional na isca
- `publico_alvo` (faixa etária, ex. "25-40") e `genero_alvo` (misto / predom_fem / predom_masc / ...) — opcionais na isca
- **contato** (nome, e-mail, WhatsApp) — coletado só no gate

**Ordem das perguntas (do mais leve ao mais comprometedor):**
1. **Abertura (0 slot):** "Me conta: você já tem academia ou está pensando em abrir? Em qual cidade/bairro?" → captura `cidade` + `bairro` + `uf`.
2. **Tipo de negócio:** "É academia tradicional, CrossFit, pilates, funcional…?" → `tipo_negocio`.
3. **PROVA DE VALOR (cedo!):** com cidade+bairro+tipo já dá pra devolver uma **amostra** (potencial da região / panorama de concorrência) — sem números atribuídos a fonte, em linguagem de negócio. É aqui que o visitante sente o "uau".
4. **Refino opcional:** público-alvo / porte, só se a conversa fluir.
5. **GATE (contato):** "Quer que eu monte o diagnóstico completo dessa região e te envie? Me passa nome, e-mail e WhatsApp." → consentimento LGPD + cria o **lead**.

**Regras do gate:**
- **Nunca** pedir contato antes de ter entregue valor (passo 3).
- Pedir **consentimento LGPD explícito** antes de gravar contato (checkbox/confirmação no chat).
- Se o visitante recusar o contato: oferecer um resumo do que viu e deixar o canal aberto (sem insistir).
- Cobertura fora da área primária → reconhecer e oferecer "sob demanda" (alinha com o fallback do `PLAN_AGENTE.md`); não usar a busca p/ nomear concorrentes.

**Estados da sessão (isca):**
`coletando_local` → `coletando_tipo` → `amostra_entregue` → `refino_opcional` → `gate_contato` → `lead_capturado` | `encerrado_sem_lead`.

---

## 0.4 Contrato do endpoint público (proposta)

> **Atenção (verificado):** a rota atual `POST /api/assistente/chat` é **stateless** — `AssistenteChatInput{ pergunta: str, relatorio_id: str|None }` → `AssistenteChatOutput{ resposta: str }`, e **exige JWT**. Para a isca pública precisamos de **sessão/estado** (conversa multi-turno anônima) e **sem JWT** — por isso um endpoint novo, não a reutilização direta.

**Endpoint:** `POST /api/public/isca/chat` (sem JWT; sessão anônima)

**Request (proposta):**
```json
{
  "session_id": "uuid-anon-ou-null-no-1o-contato",
  "mensagem": "texto do visitante",
  "consent_lgpd": false
}
```

**Response (proposta):**
```json
{
  "session_id": "uuid-anon",
  "resposta": "texto do agente",
  "estado": "amostra_entregue",
  "gate_aberto": false,
  "slots": { "uf": null, "cidade": "...", "bairro": "...", "tipo_negocio": "academia" },
  "lead_id": null
}
```

**Regras de sessão / segurança:**
- **Sessão anônima efêmera:** `session_id` emitido no 1º contato; TTL curto (ex. 30 min); estado guardado server-side (não no cliente).
- **Tenant público dedicado** (org_id reservado p/ leads) — nunca um tenant de cliente.
- **Escopo "isca":** só ferramentas de amostra (panorama/contagem), sem acesso a relatórios pagos.
- **Rate-limit por IP/sessão** + limite de turnos por sessão; anti-abuso.
- **Gate:** `lead_id` só é criado quando `consent_lgpd=true` e o slot de contato está completo.
- **CORS:** `allow_origins` travado no domínio do site.
- **Sem segredos no front:** nenhum JWT/API key no bundle.
- **Reuso:** internamente chama o **mesmo motor** (`services/tinker_bot`) com um `build_contexto_chat` em modo "isca" (contexto reduzido), aproveitando os guardrails de sigilo já existentes.

**Erros (proposta):** `429` rate-limit · `422` payload inválido · `409` sessão expirada (reabrir) · `503` motor indisponível → front cai para o formulário curto (seção 9).


---

## 1. Hero (primeira dobra)

**Headline (rascunho):**
> Descubra onde estão seus próximos alunos — antes de investir em marketing.

**Subheadline (rascunho):**
> Inteligência de mercado feita para academias. A gente mostra os bairros, perfis e oportunidades com maior potencial para o seu negócio fitness crescer com previsibilidade.

**CTA primário:** "Quero meu diagnóstico gratuito" → **abre o widget do agente "isca"**.
**CTA secundário (texto):** "Ver como funciona" (rola para a seção 3).

**Observação visual:** mapa/painel ilustrativo de uma região com áreas de oportunidade destacadas (mock, sem dados reais de cliente).

---

## 2. O problema (dor do dono de academia)

**Título (rascunho):** Abrir as portas e torcer para o aluno aparecer não é estratégia.

**Texto (rascunho):**
> A maioria das academias decide expansão, mídia e captação no feeling. Resultado: dinheiro de marketing jogado em quem nunca vai matricular, unidades abertas no lugar errado e concorrente chegando primeiro no bairro que era seu.

**Bullets de dor:**
- Você sabe quantos potenciais alunos existem num raio de 2 km da sua unidade?
- Sabe onde estão os concorrentes e quais regiões estão mal atendidas?
- Seu marketing fala com quem tem perfil de comprar — ou com qualquer um?

---

## 3. Como funciona (3 passos)

**Título (rascunho):** Simples assim — em 3 passos.

1. **Converse com o consultor** — clique e o nosso consultor de viabilidade (agente "isca") pergunta sua região e seu negócio. Em minutos, ele já mostra uma amostra do potencial.
2. **Receba o mapa de oportunidades** — onde estão os bairros e perfis com maior potencial para a sua academia, a partir de bases públicas e da nossa modelagem proprietária.
3. **Plano de ação** — recomendações práticas de onde captar, onde expandir e onde investir mídia com retorno.

*(Cada passo com um ícone simples e uma linha de apoio. O passo 1 abre o widget do agente.)*

---

## 4. O que você recebe (entregas traduzidas para academias)

**Título (rascunho):** O que você leva para casa.

- **Mapa de potencial por região:** quais bairros têm mais gente com perfil para matricular.
- **Leitura da concorrência:** onde os concorrentes estão fortes e onde há espaço aberto.
- **Perfil do aluno ideal:** características das pessoas com maior chance de virar cliente.
- **Recomendações de captação:** onde e como direcionar a verba de marketing.
- **(a confirmar)** Acompanhamento periódico do movimento do mercado na sua região.

---

## 5. Diferenciais

**Título (rascunho):** Por que a GymSite e não uma ferramenta genérica?

- **Feita para o fitness:** não é geomarketing genérico adaptado — é pensada para academias e estúdios.
- **Consultor que conversa:** em vez de formulário frio, um consultor inteligente entende seu caso e já mostra valor na hora.
- **Bases públicas + modelagem proprietária:** combinamos dados públicos com um modelo próprio que traduz tudo em decisão de negócio.
- **LGPD by design:** privacidade e conformidade desde a origem — você usa inteligência de mercado sem risco.
- **Linguagem de dono, não de cientista de dados:** entregamos respostas, não planilhas que ninguém entende.

---

## 6. Prova social (placeholders)

**Título (rascunho):** Quem já testou.

- [PLACEHOLDER] Depoimento de dono de academia (nome, unidade, cidade) — foco em "descobri um bairro que eu ignorava".
- [PLACEHOLDER] Métrica de resultado (ex.: "X% menos custo de aquisição") — *(a confirmar, usar só com dado real)*.
- [PLACEHOLDER] Logos de academias/parceiros — *(a confirmar)*.

> Nota: não publicar números ou nomes sem autorização e dado verificado.

---

## 7. FAQ (trata objeções sem revelar método)

**De onde vêm os dados?**
> Trabalhamos com bases públicas combinadas a uma modelagem proprietária. Você recebe a conclusão pronta para decidir — sem precisar lidar com a parte técnica.

**Isso está de acordo com a LGPD?**
> Sim. A conformidade com a LGPD faz parte do projeto desde a concepção. Não trabalhamos com dados pessoais sensíveis de terceiros para te entregar resultado.

**Falar com o consultor me obriga a alguma coisa?**
> Não. A conversa é gratuita e sem compromisso. Você só avança para o diagnóstico completo se quiser.

**Preciso ter conhecimento técnico?**
> Não. A entrega é em linguagem de negócio, com recomendações práticas.

**Quanto custa?**
> O diagnóstico inicial é gratuito. As condições de continuidade são apresentadas depois que você vê o valor na prática.

**Serve para academia pequena?**
> Sim. A análise se ajusta ao seu porte e à sua região — de estúdio de bairro a rede.

---

## 8. Confiança e LGPD

**Título (rascunho):** Seus dados e os do mercado, tratados com responsabilidade.

**Texto (rascunho):**
> Levamos privacidade a sério. Operamos em conformidade com a LGPD e usamos apenas informações de forma legítima e responsável. Transparência e segurança são parte do produto, não um detalhe.

*(Bloco com selo/ícone de privacidade — visual de confiança.)*

---

## 9. CTA final + gate (formulário curto)

**Título (rascunho):** Pronto para enxergar seu mercado com clareza?

**Subtítulo (rascunho):** Comece falando com o consultor. Sem compromisso.

**CTA:** "Quero meu diagnóstico gratuito" → **abre o widget do agente "isca"**.

**Gate (formulário de produção, exibido ao final da conversa):** campos canônicos do app —
- UF / Município / Bairro
- Tipo de negócio / Porte
- Público-alvo (faixa etária, gênero)
- Contato (nome, e-mail, WhatsApp)

**Microcopy abaixo do CTA:** "Resposta em minutos no chat. Seus dados ficam protegidos conforme a LGPD."

---

## 10. Notas de implementação (técnico / interno)

- Stack: Vite + React; deploy em Cloudflare Pages (alinhar com `PLAN_APP_FRONTEND.md`).
- **Conversão = agente "isca" via widget React nativo** (ver seção 0.2).
- **Chat hoje é logado e stateless** (`POST /api/assistente/chat`, JWT; input `pergunta`+`relatorio_id`). Para a landing: **criar endpoint público** `/api/public/isca/chat` com sessão anônima, estado multi-turno, tenant público, escopo "isca", rate-limit — **reusando o mesmo motor** (`services/tinker_bot`). Ver seções 0.3 e 0.4.
- Backend alcançado pelo **túnel/CORS Cloudflare já existente** (`CLOUDFLARED_CORS_SETUP.md`); `allow_origins` travado no domínio do site.
- Sem segredos no bundle do front; o backend é quem fala com o modelo. Nunca distribuir JWT/API key no site.
- Agent Studio permanece como ambiente de prompt/eval (hoje em DRAFT, ver `PLAN_AGENTE.md`); nada vai a público sem Deploy autorizado.
- SEO: foco em termos do setor fitness + intenção local (a confirmar palavras-chave).
- Sem expor nomes de fontes, ferramentas, modelo ou projeto em qualquer copy pública nem nas respostas do agente.
- Revisar todos os [PLACEHOLDER] e marcações "(a confirmar)" antes de publicar.

---

_Status: rascunho v5 — embed + slot-filling (0.3) + contrato do endpoint público (0.4). Próximo: confirmar criação do endpoint público, host do backend e onde guardar o estado da sessão anônima._
