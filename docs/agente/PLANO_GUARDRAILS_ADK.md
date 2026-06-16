# Plano — Guardrails e Otimização de Custo no Agente de IA Especialista em Fitness

> Inspirado em "Combata a IA desonesta: imponha políticas e reduza custos no ADK"
> (Serverless Expeditions — Martin Omander & Miguel Gutierrez).
> Repositório de referência: https://goo.gle/adk-financial-advisor
> Aplicado ao Agente de IA Especialista em Fitness (GymSite) — ver AS_BUILT.md.

---

## 1. Objetivo

Adicionar uma camada de **proteção e governança** ao agente conversacional, garantindo que ele:
1. Permaneça dentro do escopo (consultoria de viabilidade de academias), recusando temas fora do domínio.
2. Não emita conselhos proibidos (financeiros/investimento, jurídicos, crédito, criptomoedas), reduzindo risco legal.
3. Exiba um aviso legal **uma única vez** por conversa, sem repetição.
4. Imponha **limites rígidos** sobre quando o pipeline pesado A0–A9 pode ser disparado.
5. Reduza latência e custo de tokens via **cache** de respostas e classificações repetidas.

Princípio condutor: as proteções vivem em **callbacks do ADK**, não espalhadas no `conversational_engine.py`. Assim, política é desacoplada da lógica de conversa.

---

## 2. Conceitos do vídeo → mapeamento no GymSite

| Conceito do vídeo | Onde se encaixa no GymSite |
|-------------------|----------------------------|
| `before_agent_callback` / `after_agent_callback` | Interceptar entrada/saída do agente conversacional antes de chegar à extração de slots ou ao usuário |
| `before_tool_callback` | Bloquear/condicionar o disparo do pipeline A0–A9 (a "ferramenta pesada") |
| Disclaimer único via estado | Flag em `sessions.slots` (ex.: `_disclaimer_exibido: true`) |
| "Juiz" LLM leve de intenção | Reusar o classificador Gemini Flash já existente, estendido com rótulos de risco |
| Limites rígidos em ferramentas | Regras determinísticas no `before_tool_callback` (não delegadas ao LLM) |
| Cache de tokens | Estender o Redis (`competitor_cache`) com cache de classificação/resposta |

---

## 3. Guardrails de escopo e política (o "juiz" LLM)

**3.1 Estender a classificação de intenção.** Hoje `classificar_intencao` (Gemini Flash) retorna intenções como `novo_relatorio`, `pergunta_simples`, `status_relatorio`, `encerrar`. Adicionar uma dimensão de **risco/escopo** na mesma chamada (sem custo extra de uma segunda chamada):
- `dentro_escopo` — viabilidade, localização, concorrência, público, modelo de academia.
- `fora_escopo` — assuntos não relacionados a abrir/operar academia.
- `conselho_proibido` — investimento/finanças pessoais, crédito/empréstimo, jurídico, cripto.

**3.2 Resposta determinística por rótulo.** O LLM apenas *classifica*; a *ação* é código:
- `conselho_proibido` → resposta-padrão de recusa educada + redirecionamento ao escopo. **Nunca** chega ao pipeline.
- `fora_escopo` → reconduzir gentilmente à consultoria de academias.
- `dentro_escopo` → fluxo normal.

**3.3 Onde implementar.** Em um `before_agent_callback` que roda antes da extração de slots. Mantém `conversational_engine.py` focado em slot-filling.

> Regra: classificação é probabilística (LLM); bloqueio é determinístico (código). Nunca confie só no LLM para impor a política.

---

## 4. Aviso legal "único" via estado da conversa

- Na **primeira** mensagem de cada sessão, anexar um disclaimer curto: a análise é uma estimativa de viabilidade, não garantia de sucesso nem aconselhamento financeiro/jurídico.
- Persistir flag `_disclaimer_exibido: true` em `sessions.slots` (JSONB) — **sem migration**, igual ao padrão já usado para `_incertos` (ver BUG-001).
- `after_agent_callback` verifica a flag; se ausente, prepende o aviso e seta a flag.
- Respeitar P-001 (linguagem do domínio): redigir o aviso em tom de consultoria, não juridiquês.

---

## 5. Limites rígidos no disparo do pipeline (ferramenta pesada)

O pipeline A0–A9 é caro (scraping, Redis, múltiplos LLMs). Tratar como ferramenta com `before_tool_callback`:
1. **Só dispara após confirmação explícita** — já garantido pelo estado `aguardando_confirmacao` (BUG-001). Reforçar no callback.
2. **Slots obrigatórios presentes** (`cidade`, `bairro`) — bloqueio determinístico, não "achismo" do LLM.
3. **Rate limit por usuário** — máximo de N análises por janela de tempo (chave Redis `pipeline_quota:{user_id}`), evitando abuso e estouro de custo.
4. **Dedupe** — se já existe análise recente para o mesmo `cidade+bairro+tipo_negocio`, oferecer o relatório em cache antes de re-executar (conecta com §6 e com o "Cache inteligente por bairro" listado nos próximos passos do as-built).

---

## 6. Cache para reduzir latência e custo

| Camada | Chave | TTL sugerido | Ganho |
|--------|-------|--------------|-------|
| Classificação de intenção | hash da mensagem normalizada | curto (horas) | evita reclassificar mensagens repetidas |
| Respostas de Q&A simples | hash da pergunta | médio | evita re-chamar Gemini para FAQs |
| Relatório por bairro | `cidade+bairro+tipo+tamanho` | longo (dias) | evita reexecutar o pipeline A0–A9 |

- Reaproveitar o Redis já em uso (`competitor_cache`).
- Implementar como `before_agent_callback` (cache hit → retorna sem chamar o LLM) + escrita no `after_agent_callback`.
- Respeitar o glossário: a UI nunca diz "cache"/"token" (termos proibidos); usar "consulta recente" / "resultado já calculado".

---

## 7. Ordem de implementação (incremental)

1. **Guardrail de conselho proibido** — maior redução de risco legal; estende classificador existente. *(prioridade 1)*
2. **Disclaimer único** — baixo esforço, alto valor de conformidade (flag em `slots`).
3. **Limites rígidos no pipeline** — rate limit + revalidação de confirmação no `before_tool_callback`.
4. **Cache de classificação e Q&A** — ganho imediato de custo/latência.
5. **Cache/dedupe de relatório por bairro** — fecha o item "Cache inteligente por bairro" do roadmap.

---

## 8. Riscos e cuidados

- **Falsos positivos do juiz:** uma classificação `conselho_proibido` errada pode recusar pergunta legítima. Mitigar com prompt bem calibrado + log de auditoria das recusas.
- **Não usar `/`, atalhos ou termos proibidos na UI** (P-001) — guardrails devem soar como consultoria, não como sistema.
- **Cache e dados sensíveis:** não cachear conteúdo específico de usuário em chave compartilhada; segmentar por `user_id` quando aplicável.
- **Determinismo > LLM:** toda decisão de *bloqueio* deve ter fallback determinístico caso o LLM falhe ou retorne formato inesperado.
- **Testes de integração:** seguir o padrão do BUG-001 (LLM mockado) — cenários: conselho proibido, fora de escopo, disclaimer único, rate limit, cache hit/miss.

---

## 9. Critérios de aceite

- [ ] Pedido de conselho financeiro/cripto é recusado e nunca dispara o pipeline.
- [ ] Disclaimer aparece exatamente uma vez por conversa.
- [ ] Pipeline só dispara com confirmação + slots obrigatórios + dentro da cota.
- [ ] Mensagens repetidas retornam de cache (verificável por log/latência), sem nova chamada ao LLM.
- [ ] Nenhum termo proibido vaza para a UI.