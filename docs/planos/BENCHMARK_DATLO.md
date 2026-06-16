# BENCHMARK: Datlo + Decisao de Construcao do Site

> Documento de referencia (benchmark competitivo + decisao de stack) para o landing do GymSite Intelligence.
> Restricoes vinculantes: sigilo de fontes (vender beneficio, nunca metodo/origem de dados); Fase 0 (sem precos fixos); LGPD (consentimento no gate). Nada aqui deve nomear fontes de dados, APIs ou modelos de IA na copy publica.

## 1. Resumo

A Datlo (datlo.com) e uma plataforma de inteligencia de mercado B2B (Maringa-PR; Y Combinator 2021). Servimos como referencia de estrutura de landing e de mecanica de "degustacao". Este doc consolida (a) melhores praticas a adotar, (b) o que evitar por sigilo, (c) a stack de frontend deles, e (d) a recomendacao de como construir o nosso site.

## 2. Molde de pagina (estrutura que se repete e que vamos adotar)

Quase todas as paginas da Datlo seguem o mesmo esqueleto, validado e eficaz:

1. Hero com rotulo de categoria + titulo curto + 1 paragrafo + CTA unico.
2. Faixa de logos / prova social imediata.
3. Bloco "SEM nos x COM nos" (dor em 3 colunas vs solucao em 3 colunas).
4. Faixa de metricas animadas (contadores).
5. Secoes de funcionalidade com apoio visual.
6. Depoimentos nominais (carrossel).
7. FAQ.
8. Formulario de captura + passo a passo (01 contato, 02 demo, 03 onboarding).

CTA unico e repetido ao longo da pagina ("Falar com especialista"). Para nos, o CTA primario sera o agente isca ("Quero meu diagnostico gratuito").

## 3. Tecnicas de copy a espelhar

- **Dor x Solucao em colunas**: enquadrar o "antes" (decisao no achismo) vs "depois" (decisao com dados). Encaixa no dono de academia.
- **Comparativo Humano x IA com numeros**: a Datlo usa tabelas (tempo/custo/precisao, ex. "economia de 360x"). Formato poderoso. Na Fase 0 usar numeros reais ou claramente ilustrativos; nunca inventar.
- **Persona narrativa**: a Datlo cria personagens ("Fred", "Marcus") para tornar o abstrato concreto. Podemos ter uma persona dona de academia cujo bairro/mercado e "lido" pela amostra.
- **Vilao definido**: paginas posicionam contra "consultorias caras/lentas" ou "listas genericas". Nosso vilao: abrir/operar academia no achismo.
- **Selo de confianca de dados**: a Datlo repete "consentido, anonimizado, conforme LGPD". Adotamos o enquadramento LGPD, com consentimento no gate.

## 4. Mecanica da "degustacao" (insight central)

A demo de mapa da Datlo NAO e um app ao vivo: sao elementos <video> com um campo de texto que digita sozinho uma pergunta-exemplo ("Agora me mostre as areas de Fortaleza classificadas por renda") e o "mapa" anima a resposta. E uma demonstracao pre-renderizada, barata, sem custo de backend por visita.

**Decisao para o GymSite**: superamos esse padrao entregando uma amostra REAL e limitada via o agente isca (slot-filling), em vez de um video roteirizado. A degustacao e o proprio mecanismo de captura de lead (a amostra de valor vem ANTES de pedir contato; o formulario e o gate ao fim). Ver PLAN_SITE secoes 0.1-0.4.

## 5. Stack de frontend da Datlo (verificado)

- CMS: WordPress.
- Construcao: Elementor + Elementor Pro, tema Hello Elementor; add-ons ElementsKit e Essential Addons.
- i18n: TranslatePress. SEO: Yoast.
- JS: jQuery 3.7.1; NAO usa React nem Vue (site de marketing renderizado server-side).
- Terceiros via tag: HubSpot (analytics + chat "conversations-visitor" + formularios), Google Tag Manager / gtag, Google Site Kit.
- Sem biblioteca de mapas no front (a demo e video, nao Mapbox/Leaflet).

**Leitura**: a Datlo separa SITE DE MARKETING (WordPress, editavel por marketing) do PRODUTO (plataforma logada, a parte). O chat publico deles e um widget de terceiro (HubSpot), nao o motor real.

## 6. O que NAO copiar (sigilo de fontes)

A Datlo vende nomeando suas origens e metodos de dado e expoe ate exemplo de API. Para nos isso e proibido. Nossa copy permanece em beneficio ("bases publicas + modelagem proprietaria"), sem citar fontes, metodos de coleta, APIs ou nomes de modelos de IA. O argumento de seguranca deles ("nao passa por IAs de terceiros") e o oposto da nossa restricao: nos nao nomeamos nossa stack de IA em copy alguma.

## 7. Decisao de construcao do nosso site

### 7.1 Ambiente HostGator (plano atual, verificado no cPanel)

Hospedagem compartilhada cPanel/Jupiter. Disponivel: WordPress + Softaculous (Weebly, phpBB, pH7Builder), MultiPHP, phpMyAdmin, Git Version Control, Application Manager, dominios/subdominios. NAO observado: Node.js Selector, Ruby/Python app, terminal/SSH.

Conclusao tecnica: o HostGator e otimo para PHP/WordPress e para servir ARQUIVOS ESTATICOS, mas NAO roda um backend Node nativamente neste plano. O nosso agente isca exige um backend proprio (engine conversacional em services/), que nao roda em hospedagem shared PHP.

### 7.2 Opcoes avaliadas

**(A) WordPress/Elementor direto no HostGator** — como a Datlo.
- Pros: rapido de montar; marketing edita sozinho; SEO/plugins prontos; baixo custo inicial.
- Contras: nao hospeda nosso backend; a degustacao real (agente) teria de ser um widget externo apontando para outro host; descasa da stack que ja temos no repo (Vite/React). Acaba exigindo dois ambientes mesmo assim.

**(B) Construcao do zero em Vite + React (stack atual do repo) + Cloudflare Pages** — direcao ja registrada no PLAN_SITE.
- Pros: a degustacao E o produto (agente isca nativo); mesma stack do app; deploy estatico na Cloudflare Pages (rapido, CDN, gratis no inicio); backend publico via api.getgymsite.com.br (a confirmar) atras do Cloudflare; controle total de UX e do widget.
- Contras: exige desenvolvimento (nao no-code); marketing nao edita sozinho sem CMS.

**(C) Ferramentas de IA de scaffolding (Lovable / v0 / Bolt)** — gerar o frontend do zero com IA.
- Pros: acelera MUITO o boilerplate de UI; Lovable/Bolt geram React+Tailwind exportavel; v0 (Vercel) gera componentes shadcn/ui. Bom para prototipar o landing e os componentes da degustacao rapidamente, depois exportar para o repo.
- Contras: codigo gerado precisa revisao/integracao; tendem a acoplar a hospedagem propria (Lovable/Vercel) — usar como GERADOR e trazer o codigo para a nossa stack/Cloudflare, nao como host final; cuidado para nao vazar termos sigilosos em prompts/telemetria.

### 7.3 Recomendacao

Construir do zero na stack atual (opcao B), usando ferramentas de IA (opcao C) como ACELERADOR de UI — gerar layout/componentes com Lovable/v0/Bolt e trazer o codigo para o repo Vite/React, hospedando o estatico na Cloudflare Pages e o backend do agente em api.getgymsite.com.br (a confirmar). Descartar WordPress/HostGator como base do site porque ele nao hospeda o agente isca, que e o nucleo da nossa conversao. O HostGator permanece util para e-mail (Titan ja configurado) e como fallback estatico.

Observacao de arquitetura DNS (a confirmar): se o site for servido pela Cloudflare, o dominio deveria apontar NS para Cloudflare; hoje o NS de getgymsite.com.br foi alterado para os nameservers do HostGator. Revisar Cloudflare x HostGator antes do go-live.

## 8. Pendencias (a confirmar)

- Host publico do backend do agente (provavelmente api.getgymsite.com.br via Cloudflare).
- Definir CMS leve para textos (ou manter copy no codigo na v1).
- Confirmar Cloudflare x HostGator para o dominio do site.
- Depoimentos reais e numeros reais para os blocos de prova (Fase 0: sem inventar).
- Avaliar Lovable/v0/Bolt como gerador, garantindo que nenhum termo sigiloso entre nos prompts.

## 9. Referencias

- PLAN_SITE.md (estrutura, copy, agente isca, embed, contrato do endpoint publico).
- PLAN_AGENTE.md / PLAN_APP_FRONTEND.md (fluxo do agente e integracao de lead).
