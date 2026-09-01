# Modelo de Negócio — GymSite Execução

> Análise de custos, opções de monetização e decisão recomendada para o módulo Consultor Conversacional + Playbook de Abertura.
>
> **Revisão 2026-06-10:** arquitetura de monetização atualizada com base em benchmark verificado — ver `docs/produto/PESQUISA_PRICING_BENCHMARK.md`. Price points são PROVISÓRIOS até o fim da Fase 0 (entrevistas de willingness-to-pay + métricas de uso).

---

## 1. Análise de Custo de Infraestrutura por Projeto

### 1.1. Pesquisa de Mercado (Consultor Conversacional)

| Componente | Custo Unitário | Uso por Projeto | Custo Total |
|-----------|---------------|-----------------|-------------|
| Gemini 3.6 Flash (router/respostas) | $0.30 / 1M tokens | ~50K tokens | $0.015 |
| Gemini 3.6 Flash (extrair slots) | $0.30 / 1M tokens | ~20K tokens | $0.006 |
| Gemini 3.6 Flash (A3b — reviews) | $0.30 / 1M tokens | ~100K tokens | $0.030 |
| Gemini 3.6 Flash (análise profunda) | $3.50 / 1M tokens | ~50K tokens (opcional) | $0.175 |
| Google Places API (A1, A3a) | $7 / 1.000 req | ~15 requests | $0.105 |
| Google Geocoding | $5 / 1.000 req | ~3 requests | $0.015 |
| CNPJ/RFB consultas | Gratuito | ~5 requests | $0.000 |
| CNO consultas | Gratuito | ~1 request | $0.000 |
| Deep Research (A0) | $0.30 / 1M tokens | ~200K tokens | $0.060 |
| **Subtotal Pesquisa Completa** | | | **~$0.23 - $0.40** |

> Nota: se usar cache de bairro (DP-003), projetos subsequentes no mesmo bairro custam ~$0.05 (só consultor + resposta).

### 1.2. Geração de Playbook

| Componente | Custo Unitário | Uso | Custo Total |
|-----------|---------------|-----|-------------|
| Gemini 3.6 Flash (gerar tarefas) | $0.30 / 1M tokens | ~30K tokens | $0.009 |
| Gemini 3.6 Flash (sugestões IA) | $0.30 / 1M tokens | ~10K tokens/sugestão | $0.003 |
| **Subtotal Playbook** | | | **~$0.01 - $0.05** |

### 1.3. Infraestrutura Fixa (mensal)

| Serviço | Plano | Custo Mensal |
|---------|-------|--------------|
| Supabase (DB + Auth + Storage) | Pro | $25 |
| Supabase Storage (anexos) | 100GB incluso | $0 (dentro do limite) |
| Redis (Upstash ou Railway) | Starter | $0 - $10 |
| Cloudflare Workers/Pages | Free tier | $0 |
| FastAPI (GCP Cloud Run) | ~1 vCPU | $10 - $30 |
| Envio de email (Resend) | 3.000 emails/mês | $0 (free tier) |
| **Subtotal Infra Fixa** | | **~$35 - $65/mês** |

### 1.4. Custo Total por Tipo de Usuário (mensal)

| Perfil | Projetos/mês | Pesquisas/mês | Custo Variável | Custo Fixo Rateado | Custo Total |
|--------|-------------|---------------|----------------|-------------------|-------------|
| Free (1 projeto) | 1 | 1 completa + 3 leves | $0.40 + $0.15 = $0.55 | $0.50 | **~$1.05** |
| Pro (5 projetos) | 5 | 5 completas + 10 leves | $2.00 + $0.50 = $2.50 | $2.00 | **~$4.50** |
| Enterprise (20 projetos) | 20 | 20 completas + 40 leves | $8.00 + $2.00 = $10.00 | $5.00 | **~$15.00** |

> Taxa de câmbio referência: US$ 1 = R$ 5,00

---

## 2. Concorrência e Benchmark de Preços

| Concorrente | Modelo | Preço | O que oferece |
|-------------|--------|-------|---------------|
| **Sebrae** | Gratuito (subsidiado) | R$ 0 | Curso + consultoria genérica. Não tem dados de mercado específicos por bairro. |
| **Franq.io** | SaaS | R$ 199-499/mês | Gestão de franquias. Foco operacional, não em viabilidade de ponto. |
| **Lark/Feishu (template)** | Freemium | $0-12/user/mês | Gestão de tarefas genérica. Não tem IA especializada em fitness. |
| **PwC/Consultoria** | Projeto | R$ 15.000-50.000 | Estudo de viabilidade tradicional. Demora 30-60 dias. |
| **Planilha do amigo** | Gratuito | R$ 0 | Não tem dados reais de mercado. Alto risco de erro. |

**Lacuna de mercado:** Ninguém oferece **pesquisa de mercado com dados reais (CNPJ, Google Maps, reviews) + consultoria de IA + playbook de execução** em um só lugar, acessível ao pequeno empreendedor.

---

## 3. Opções de Modelo de Negócio

### Opção A — Gratuito (Monetização Indireta)

**Como funciona:**
- Tudo gratuito para o empreendedor.
- Limitado a 1 projeto ativo por vez.
- Monetização via parcerias: fornecedores de equipamento, financiadoras, franqueadoras pagam para aparecer como "recomendações" no playbook.

**Prós:**
- Adoção máxima. Barreira zero.
- Dados valiosos para parceiros ("qual bairro está em alta?").

**Contras:**
- Dependência de parceiros comerciais (difícil de conseguir no início).
- Custo de infra cresce com usuários, mas receita não é proporcional.
- Risco de virar "planilha glorificada" sem recurso para investir em melhorias.

**Viabilidade:** ⚠️ Média. Só funciona com muitos usuários + parceiros consolidados.

---

### Opção B — Freemium (Recomendada)

**Como funciona:**
- **Free:** Consultor conversacional gratuito (1 projeto ativo). Playbook limitado a 10 tarefas. Sem sugestões IA. Sem dashboards.
- **Pro (R$ 99/mês):** Projetos ilimitados. Playbook completo. Sugestões IA. Dashboards de progresso e custo. Notificações por email. Exportação de relatório PDF.
- **Enterprise (R$ 499/mês):** Tudo do Pro + múltiplos usuários por projeto, permissões avançadas, API para integração com ERP/franquia, white-label (logo da rede), suporte prioritário, onboarding dedicado.

**Prós:**
- Free serve como funil de aquisição. Usuário experimenta valor antes de pagar.
- Pro é acessível para empreendedor que já decidiu abrir (tem budget).
- Enterprise captura franqueadoras e gestores de rede (alto LTV).

**Contras:**
- Precisa de gateway de pagamento (Stripe, Asaas, Mercado Pago).
- Complexidade de implementar limites por tier.

**Viabilidade:** ✅ Alta. Alinhada com o mercado B2B SaaS no Brasil.

---

### Opção C — SaaS Puro (Sem Free)

**Como funciona:**
- Trial de 7 dias (acesso completo).
- Starter: R$ 49/mês (1 projeto).
- Pro: R$ 149/mês (projetos ilimitados).
- Enterprise: R$ 699/mês.

**Prós:**
- Receita previsível desde o primeiro usuário.
- Suporte mais enxuto (só usuários pagantes).

**Contras:**
- Barreira de entrada alta. Empreendedor não paga antes de validar ideia.
- Concorre com "planilha do amigo" e Sebrae gratuito.

**Viabilidade:** ⚠️ Média-baixa. Funciona melhor quando a marca já é conhecida.

---

## 4. Análise de Unit Economics (Opção B — Freemium)

### 4.1. Custo de Aquisição de Cliente (CAC)

| Canal | Custo Estimado |
|-------|---------------|
| Orgânico (SEO, conteúdo) | R$ 0 - 20 |
| Instagram/YouTube (influenciadores fitness) | R$ 50 - 150 |
| Google Ads ("como abrir academia") | R$ 80 - 200 |
| Parcerias (fornecedores indicam) | R$ 30 - 80 (comissão) |
| **CAC Médio Estimado** | **R$ 60 - 120** |

### 4.2. Lifetime Value (LTV)

| Tier | Preço Mensal | Churn Mensal Estimado | Tempo Médio de Permanência | LTV |
|------|-------------|----------------------|---------------------------|-----|
| Free | R$ 0 | 30% (abandona rápido) | 2 meses | R$ 0 |
| Pro | R$ 99 | 8% | 12 meses | **R$ 1.188** |
| Enterprise | R$ 499 | 3% | 18 meses | **R$ 8.982** |

### 4.3. Margem

| Tier | Receita Mensal | Custo Infra + LLM | Margem Bruta |
|------|---------------|-------------------|--------------|
| Free | R$ 0 | R$ 5 | Negativo |
| Pro | R$ 99 | R$ 23 | **~77%** |
| Enterprise | R$ 499 | R$ 75 | **~85%** |

### 4.4. Payback e Saúde

- **LTV/CAC ratio:** Pro = 9.9x, Enterprise = 74.8x. ✅ Excelente (saudável > 3x).
- **Payback do CAC:** Pro = 1.2 meses, Enterprise = 0.3 meses. ✅ Muito rápido.
- **Margem bruta:** ~80%. ✅ SaaS saudável.

---

## 5. Decisão Recomendada (revisada 2026-06-10)

**Adotar Freemium HÍBRIDO: assinatura com franquia de uso inclusa + relatório avulso pay-per-use. Pacote de créditos só na Fase 2, após validar assinatura.**

Base da revisão: benchmark verificado em `PESQUISA_PRICING_BENCHMARK.md`. Best practice convergente (Metronome/Stripe, m3ter, Lago): lançar "subscription + included usage" antes de qualquer sistema de créditos.

### Estrutura de Ofertas

| Oferta | Preço (provisório) | O que inclui | Ancoragem |
|--------|-------------------|--------------|-----------|
| **Free** | R$ 0 | 1 projeto ativo, consultor limitado, playbook 10 tarefas, 1 relatório total | Funil de aquisição ("ahá moment") |
| **Relatório avulso** | R$ 49–99 | 1 Relatório de Viabilidade completo, sem assinatura | 50–300x mais barato que consultoria tradicional (Sebrae R$ 4.680–15.600); margem 91–95% sobre custo R$ 4,45 |
| **Pro** | R$ 99/mês | 2–3 relatórios/mês inclusos + playbook completo + sugestões IA + dashboards + email + PDF | Abaixo do piso do SaaS de gestão que o ICP já paga (Tecnofit R$ 269+) — vende como add-on do stack |
| **Rede** (novo, a validar) | ~R$ 199–299/mês | Pro + multi-projetos simultâneos + comparativo entre bairros + 3+ convidados | Gap entre Pro e Enterprise; redes 2–10 unidades; espelha eixo unidades+alunos do setor (W12/Tecnofit) |
| **Enterprise** | R$ 499+/mês com eixo de escala (unidades analisadas ou seats) | Tudo + múltiplos usuários, RBAC, API, white-label, WhatsApp, onboarding | Coerente com teto internacional de SaaS fitness (US$ 100–500/mês) |

### Justificativa

1. **Free é funil, não produto.** O empreendedor precisa sentir valor antes de pagar. O consultor conversacional gratuito (1 projeto) é o "ahá moment".
2. **Relatório avulso captura demanda pontual.** Dono de academia avaliando 1–2 pontos não assina mensalidade — paga R$ 99 para evitar erro de R$ 300K. Margem ~90% banca o funil.
3. **Pro é o core.** R$ 99/mês é acessível para quem está decidindo investir R$ 500K-1,5M em uma academia. É menos de 0.02% do investimento total.
4. **Enterprise é o multiplicador.** Uma franqueadora com 50 franqueados = R$ 24.950/mês de receita recorrente.
5. **Margem sustentável.** 77-85% de margem bruta dá folga para investir em melhorias e suporte.
6. **Créditos adiados deliberadamente.** Modelo de créditos tem armadilhas documentadas (burn rate confuso, disputas de pool, breakage estilo Apollo.io). Entra na Fase 2 com regra simples: 1 crédito = 1 relatório, validade 12 meses + lembretes, condicionado a parecer jurídico (CDC × expiração de pré-pago).

### ICPs e modelo natural de cada um

| ICP | Modelo natural |
|-----|----------------|
| Consultor fitness (revende análise) | Pacote de créditos (Fase 2) + white-label do relatório — é canal, não só cliente |
| Empreendedor 1ª unidade | Free → relatório avulso → pacote "Abertura" (relatório + playbook) |
| Dono de rede local (2–10) | Tier Rede |
| Franqueadora / rede nacional | Enterprise + API |
| Fornecedor de equipamentos | Lead gen (não paga assinatura — paga lead; ver `PARCERIAS_FORNECEDORES.md`) |

### Regras de Conversão Free → Pro

| Gatilho | Ação do Sistema |
|---------|----------------|
| Usuário atinge 10 tarefas no playbook | Exibe modal: "Seu playbook está cheio. Libere tarefas ilimitadas com Pro." |
| Usuário pede "Gerar Relatório Formal" pela 2ª vez | "Você já usou seu projeto gratuito. Crie projetos ilimitados com Pro." |
| Usuário clica em "Sugestão da IA" | "Sugestões inteligentes disponíveis no plano Pro." |
| Usuário tenta convidar sócio | "Colaboração em equipe é um recurso Pro." |

---

## 6. Roadmap de Monetização

| Fase | Quando | O que implementa |
|------|--------|----------------|
| **Fase 0** | Agora (60 dias) | Acesso completo sem cobrar. **Instrumentar telemetria por módulo** (cada pesquisa/relatório/tarefa loga consumo equivalente em créditos). **Entrevistas de willingness-to-pay**: 5–10 por ICP (consultores fitness, donos de rede, franqueadoras). **Parecer jurídico** sobre expiração de créditos pré-pagos (CDC). Conversar com 2–3 fornecedores (Movement, Life Fitness BR) sobre valor de lead. |
| **Fase 1** | Mês 2 após lançamento | Limites técnicos por tier (Free sente limitação: 10 tarefas, 1 projeto). **Decidir price points finais** com dados da Fase 0. |
| **Fase 2** | Mês 3 | Abrir pagamento: relatório avulso + Pro + Rede. Enterprise sob consulta. **Avaliar lançamento de pacote de créditos** (1 crédito = 1 relatório, validade 12 meses + lembretes — condicionado ao parecer jurídico). |
| **Fase 3** | Mês 6 | Enterprise self-service com onboarding automatizado. Parcerias comerciais (fornecedores). White-label para consultores. |

> **Recomendação:** Não cobrar nos primeiros 60 dias. Use o período para validar que usuários realmente completam playbooks e geram relatórios. Métricas de conversão são mais importantes que receita no início.

---

## 6.1. Pendências da Decisão de Preço (fechar até fim da Fase 0)

| Pendência | Como fechar | Status |
|-----------|-------------|--------|
| **PD-001** Price points finais (Pro R$ 99? Rede R$ 199 ou 249?) | Entrevistas WTP + telemetria Fase 0 | Aberta |
| **PD-002** Franquia do Pro: 2 ou 3 relatórios/mês? | Telemetria de consumo real | Aberta |
| **PD-003** Expiração de créditos é legal no BR? | Parecer jurídico (analogia: créditos de celular limitados por Anatel/Justiça) | Aberta |
| **PD-004** Valor do lead para fornecedor (R$ 50–150 é chute) | Conversas diretas com fornecedores | Aberta |
| **PD-005** Tier Rede entra no lançamento ou depois? | Volume de ICP rede nas entrevistas | Aberta |

> Regra do processo de mudança: pendência aberta → perguntar antes de assumir default na implementação.

---

## 7. Checklist de Implementação (EIXO 4)

- [x] Análise de custo de infra por projeto
- [x] Benchmark de concorrência
- [x] Comparação de 3 opções de modelo de negócio
- [x] Unit economics (LTV, CAC, margem)
- [x] Decisão recomendada: Freemium híbrido (assinatura + franquia + avulso; créditos Fase 2)
- [x] Regras de conversão Free → Pro
- [x] Roadmap de monetização
- [x] Benchmark de pricing verificado (`PESQUISA_PRICING_BENCHMARK.md`)
- [ ] Entrevistas de willingness-to-pay por ICP (Fase 0)
- [ ] Parecer jurídico sobre expiração de créditos (Fase 0)
- [ ] Price points finais (Fase 1)

**Próximo passo:** Documentar limites técnicos por tier (`LIMITES_TIER.md`) — atualizar com tier Rede e franquia de relatórios quando PD-001/PD-002/PD-005 fecharem.
