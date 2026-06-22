# Arquitetura de Convergência — GymSite Intelligence

> Documento de arquitetura que descreve como **o produto (gymsite)**, a **landing (gym-insight-hub)** e o **Apollo (GTM/CRM)** convergem sobre um único banco **Supabase** (projeto <SUPABASE_PROJECT>).
>
> Estado: desenho de integração. Reflete o que já existe (DNS Cloudflare, Pages, schema Supabase) e o que falta conectar.

## 1. Componentes e onde cada um vive

| Componente | Repositório / Serviço | Hospedagem | Domínio |
|---|---|---|---|
| Landing (marketing + agente/lead) | github.com/Marcelo-Rosas/gym-insight-hub | Cloudflare Pages | getgymsite.com.br / www |
| Frontend do produto (dashboard) | github.com/Marcelo-Rosas/gymsite (frontend/) | Cloudflare Pages (projeto "gymsite") | app.getgymsite.com.br (a criar) |
| Backend / pipeline A0–A7 | github.com/Marcelo-Rosas/gymsite (backend/, agents/) | Google Cloud Run (issue #120) | api.getgymsite.com.br (a criar) |
| Banco de dados | Supabase epgedaiukjippepujuzc | Supabase (São Paulo) | — |
| GTM / engajamento de leads | Apollo.io | SaaS | — |
| E-mail transacional/caixa | Titan (HostGator) | HostGator | MX getgymsite.com.br |

## 2. Estado atual confirmado

### DNS (Cloudflare, zona getgymsite.com.br)
- `getgymsite.com.br` e `www` → CNAME `gym-insight-hub.pages.dev` (Proxied, SSL ativo) — **landing já no ar**.
- `MX` → `mx1/mx2.titan.email` — e-mail no Titan/HostGator.
- Registros cPanel (cpanel, whm, mail, ftp, autodiscover → 69.49.241.85) em **DNS only**.
- **Não existe** `app.` nem `api.` ainda.
- ⚠️ Aviso do próprio Cloudflare: *origin IP parcialmente exposto* pelos registros cPanel DNS-only.

### Cloudflare Pages / Workers
- Projeto `gym-insight-hub` (Git: gym-insight-hub) → custom domains getgymsite.com.br + www **ativos**.
- Projeto `gymsite` (Git: gymsite) → já faz build, mas **sem custom domain**.
- Projeto `gymsite-3p0` → sem Git, provável preview/duplicata (candidato a limpeza).

### Supabase (público, projeto compartilhado com o CFN)
Schema GymSite já presente no schema `public`. Tabelas-chave confirmadas:

| Tabela | Papel |
|---|---|
| `organizations` | Multi-tenant (id, nome, slug, plano, limite_relatorios_mes) |
| `organization_members` | Vínculo usuário × org (roles) |
| `relatorios` | Header da análise (status, custo_brl, tokens_total, markdown_completo, erro_mensagem) |
| `relatorio_inputs` | Formulário (publico_alvo, genero_alvo, tipo_negocio, bairros_indicados, a0_research_provider) |
| `relatorio_outputs` | Veredito, scores |
| `candidatos` / `competidores` / `cenarios_financeiros` / `sensibilidade_cenarios` / `bairros_alternativos` | Saídas do pipeline |
| `relatorio_custos_agentes` | Telemetria de custo por agente |
| `chat_interacoes` | **Persistência do agente conversacional** (user_id, session_id, endpoint, pergunta, intencao, resposta, kb_fontes jsonb) |
| `v_relatorios_resumo` / `v_bairros_aggregate` | Views agregadas |

Observação importante: a tabela `chat_interacoes` já existe e foi desenhada para registrar as conversas do agente — **mas a landing publicada hoje não escreve nela** (o formulário não chama endpoint algum). Esse é o gap central a fechar.

## 3. Diagrama de convergência

```
                         getgymsite.com.br (Cloudflare Pages)
                          ┌───────────────────────────────┐
                          │   LANDING  (gym-insight-hub)   │
                          │   Hero + Agente "Diagnóstico"  │
                          │   + Form de lead (LGPD)        │
                          └───────────────┬───────────────┘
                                          │  POST lead + intenção
                                          ▼
                         api.getgymsite.com.br (Cloud Run)
                          ┌───────────────────────────────┐
                          │  BACKEND FastAPI (gymsite)     │
                          │  /leads  /chat  /score  /run   │
                          │  ADK Runner → Pipeline A0–A7   │
                          └───────┬───────────────┬────────┘
                                  │               │
                 service_role    │               │  sync (API/webhook)
                                  ▼               ▼
                     ┌────────────────────┐   ┌──────────────────┐
                     │  SUPABASE (public) │   │   APOLLO (GTM)    │
                     │  organizations     │   │  Pessoas/Empresas │
                     │  relatorios+filhas │   │  Sequências       │
                     │  chat_interacoes   │   │  Visitantes/Forms │
                     │  (lead + tracking) │   │  Fluxos de trabalho│
                     └─────────▲──────────┘   └──────────────────┘
                               │ JWT (anon)
                          ┌────┴───────────────────────────┐
                          │  app.getgymsite.com.br (Pages)  │
                          │  FRONTEND produto (dashboard)   │
                          │  relatórios, mapa, custos       │
                          └─────────────────────────────────┘
```

## 4. Fluxo de dados de ponta a ponta

1. **Captação (landing).** Visitante usa o agente "Diagnóstico GymSite" em `getgymsite.com.br` e preenche o formulário (nome, e-mail, WhatsApp, intenção de negócio + consentimento LGPD).
2. **Persistência do lead.** A landing passa a fazer `POST api.getgymsite.com.br/leads` (e `/chat` para cada turno do agente). O backend grava em `chat_interacoes` e numa tabela/coluna de lead vinculada à `organization` GymSite.
3. **Sincronização com o Apollo.** O backend (ou um job/edge function) envia o lead ao **Apollo** via API/webhook: cria/atualiza *Pessoa* + *Empresa* e o inscreve numa **Sequência** de outbound/inbound. O `Apollo Sync Tracking` (já presente no histórico de queries do Supabase) registra o id externo e o status do sync para evitar duplicidade.
4. **Geração da análise (produto).** Quando o lead vira oportunidade, o usuário acessa `app.getgymsite.com.br`, submete o formulário detalhado (`relatorio_inputs`) e o backend dispara o **pipeline A0–A7**, persistindo `relatorios` + tabelas filhas no Supabase.
5. **Leitura.** O frontend do produto lê via **JWT do usuário (anon key + RLS)**; o backend escreve via **service_role**.
6. **Loop GTM.** Resultado/veredito do relatório pode realimentar o Apollo (nota na Pessoa, gatilho de Fluxo de Trabalho).

## 5. Contratos de integração (a implementar)

### Backend (Cloud Run) — endpoints novos para a landing
- `POST /chat` → grava turno em `chat_interacoes` (session_id, pergunta, intencao, resposta). Sem PII obrigatória.
- `POST /leads` → valida consentimento LGPD, grava lead, dispara sync Apollo (assíncrono). Retorna 202.
- CORS liberando `https://getgymsite.com.br` e `https://app.getgymsite.com.br`.

### Apollo
- Credencial de API do Apollo como **secret** (nunca no código).
- Mapeamento: lead → Person (email, phone, name) + Account (cidade/bairro/tipo_negocio) + add to Sequence.
- Idempotência via tabela de tracking de sync (external_id + status + tentativas).

### Supabase
- Lead/consentimento vinculados a `organization` GymSite (origem='gymsite').
- RLS: tabelas de lead seguem o padrão `user_org_ids()` já usado nas demais.
- Escritas da landing passam **só pelo backend** (service_role), nunca expondo service_role no browser.

## 6. DNS / deploy — passos para fechar a convergência

1. **Frontend produto:** adicionar custom domain `app.getgymsite.com.br` ao projeto Pages `gymsite` (CNAME proxied automático).
2. **Backend:** concluir issue **#120** (Dockerfile + deploy Cloud Run) e expor `api.getgymsite.com.br` — via CNAME **proxied** para o Cloud Run, ou via **Cloudflare Tunnel** (a conta já tem tunnels) para não expor IP de origem.
3. **Landing:** trocar o `onSubmit` mock do formulário por chamadas reais a `/chat` e `/leads`.
4. **Limpeza:** remover/renomear o Pages `gymsite-3p0` órfão.
5. **Higiene de DNS:** avaliar proxiar ou remover registros cPanel não usados (aviso de origem exposta).

## 7. Segurança e LGPD

- Produto é **proprietário © Vectra Cargo / Navi Vectra**.
- Segredos (Google SA, `GOOGLE_API_KEY`, Maps, Apollo, Supabase service_role) via **Secret Manager** do Cloud Run — nunca no container/repo.
- Frontend usa apenas `anon key` + RLS; `service_role` exclusivo do backend.
- O formulário coleta PII sob consentimento LGPD — o consentimento precisa ser **persistido** (timestamp + texto aceito) junto ao lead, e a promessa de "contato em 24h" só é válida quando o sync Apollo estiver ativo.

## 8. Pendências conhecidas

- Landing hoje **não envia** dados (formulário sem endpoint) — bloqueador #1.
- `chat_interacoes` existe mas está **sem ingestão** a partir da landing.
- `api.` e `app.` ainda não existem no DNS.
- Sync Apollo precisa de credencial + tabela de idempotência ativa.

---
© 2026 Vectra Cargo / Navi Vectra — uso interno.
