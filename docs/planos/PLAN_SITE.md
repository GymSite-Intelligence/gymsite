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

> O CTA da landing **não leva a um formulário estático** — ele abre o agente conversacional já criado (ver `PLAN_AGENTE.md` e `PLAN_APP_FRONTEND.md`).

**Agente:** "GymSite — Consultor de Viabilidade" (Google Agent Platform / Studio).

**Fluxo de conversão:**
1. Visitante clica no CTA → **abre o agente "isca"** (widget de chat na própria landing).
2. O agente conversa, entende a região/negócio e **demonstra valor** com uma amostra (potencial da região / leitura de concorrência) — sempre respeitando sigilo de fontes, LGPD e Fase 0.
3. Quando há interesse, o agente faz o **gate**: conduz para o **formulário de produção** (campos canônicos do app: UF, município, bairro, tipo de negócio, porte, público-alvo, contato).
4. Lead capturado entra no fluxo do app → geração do relatório de viabilidade.

**Notas técnicas:**
- O formulário curto da seção 9 é o **gate** ao final da conversa, não a porta de entrada.
- (a confirmar) forma de embed do agente na landing (widget/iframe/SDK) — alinhar com `PLAN_APP_FRONTEND.md`.
- Sem expor nomes de fontes, ferramentas ou modelos em qualquer copy ou resposta do agente.

---

## 1. Hero (primeira dobra)

**Headline (rascunho):**
> Descubra onde estão seus próximos alunos — antes de investir em marketing.

**Subheadline (rascunho):**
> Inteligência de mercado feita para academias. A gente mostra os bairros, perfis e oportunidades com maior potencial para o seu negócio fitness crescer com previsibilidade.

**CTA primário:** "Quero meu diagnóstico gratuito" → **abre o agente "isca"** (chat de viabilidade).
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

*(Cada passo com um ícone simples e uma linha de apoio. O passo 1 abre o agente.)*

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

**CTA:** "Quero meu diagnóstico gratuito" → **abre o agente "isca"**.

**Gate (formulário de produção, exibido ao final da conversa):** campos canônicos do app —
- UF / Município / Bairro
- Tipo de negócio / Porte
- Público-alvo (faixa etária, gênero)
- Contato (nome, e-mail, WhatsApp)

**Microcopy abaixo do CTA:** "Resposta em minutos no chat. Seus dados ficam protegidos conforme a LGPD."

---

## 10. Notas de implementação (técnico / interno)

- Stack prevista: Vite + React; deploy em Cloudflare Pages (alinhar com `PLAN_APP_FRONTEND.md`).
- **Conversão = agente "isca"** (Google Agent Platform). A landing embeda o agente; o formulário de produção é o gate ao final.
- (a confirmar) método de embed do agente (widget/iframe/SDK) e destino do lead capturado.
- ATENÇÃO: agente só vai ao ar após Deploy autorizado (hoje em DRAFT, ver `PLAN_AGENTE.md`).
- SEO: foco em termos do setor fitness + intenção local (a confirmar palavras-chave).
- Sem expor nomes de fontes, ferramentas ou modelos em qualquer copy pública nem nas respostas do agente.
- Revisar todos os [PLACEHOLDER] e marcações "(a confirmar)" antes de publicar.

---

_Status: rascunho v2 — estrutura + copy com integração do agente "isca". Próximo: validar headline, definir embed do agente, depoimentos reais e destino do formulário._
