# Vídeo 04 — Conectar agentes aos dados da empresa via servidor MCP remoto

> Canal: Google Cloud Tech · ~6:02
> Tema: novo servidor MCP (Model Context Protocol) remoto para conectar agentes diretamente às fontes de dados corporativas.
> Feature GymSite: expor fontes (concorrentes, demografia, listings) como ferramentas MCP.

## Conceito aplicado
Abstrair as fontes de dados do pipeline atrás de um servidor MCP padronizado, reduzindo acoplamento e fragilidade dos scrapers (relacionado ao BUG-003).

## Testes de validação

### T04.1 — Descoberta de ferramentas MCP
- Dado o servidor MCP ativo
- Então o agente lista as ferramentas/fontes disponíveis sem hardcode no app.

### T04.2 — Consulta via MCP
- Dado uma pergunta sobre concorrência em um bairro
- Então o agente busca os dados pela ferramenta MCP correspondente e cita a fonte.

### T04.3 — Resiliência a fonte indisponível
- Dado que uma fonte MCP está fora do ar
- Então o agente degrada graciosamente (informa indisponibilidade), sem travar — substitui o erro cru do BUG-003.

### T04.4 — Segurança/escopo de acesso
- Dado uma ferramenta MCP com dados sensíveis
- Então o acesso respeita autorização; o agente não expõe dados fora do escopo do usuário.

### T04.5 — Substituível sem mudar o agente
- Dado que uma fonte é trocada (ex.: novo provedor de listings)
- Então basta atualizar o MCP; o código do agente não muda.
