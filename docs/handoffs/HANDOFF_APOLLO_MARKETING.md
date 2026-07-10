# HANDOFF — Frente Apollo (sequências) + Marketing

> Criado em 2026-07-09 pra transferir esta frente pra um chat/agente paralelo.
> **Primeira instrução ao novo agente:** ler `CLAUDE.md` (raiz) e este arquivo;
> carregar a skill `gymsite-prospecting` sob demanda. NÃO mexer na frente de
> auditoria de relatório (quadros/motor financeiro) — ela corre em outro chat.

## 1. Objetivo da frente

Retomar duas coisas que ficaram paradas:
1. **Sequência Apollo** — cadência de e-mails pra leads/oportunidades da
   prospecção (engine CNPJ×CNO gera oportunidades; Apollo faz enrichment,
   sync de CRM e sequências de outreach).
2. **Marketing** — material/plano que estava em `docs/marketing/` (pasta criada,
   conteúdo a inventariar) e a ponte prospecção → campanha.

## 2. O que JÁ EXISTE no repo (ler antes de criar qualquer coisa)

| Artefato | O que faz |
|---|---|
| `tools/apollo_client.py` | Cliente da API Apollo (auth, chamadas base) |
| `tools/apollo_enrichment.py` + `tools/test_apollo_enrichment.py` | Enrichment de contatos/empresas das oportunidades |
| `services/apollo_crm_sync.py` | Sync de oportunidades da prospecção → Apollo CRM |
| `db/migrations/20250610_apollo_crm_sync_oportunidades.sql` | Colunas/estado do sync no banco |
| `docs/MODULO_PROSPECCAO.md` | Doc do módulo de prospecção (fluxo, status de oportunidade) |
| `prospecting/` | Engine CNPJ×CNO + webhooks |
| `.agent/skills/gymsite-prospecting/SKILL.md` | Skill com convenções da frente |
| MCP Apollo conectado no Cowork | tools `apollo_*` (sequences, emailer_campaigns, contacts, tasks…) |

Estado da SEQUÊNCIA: foi começada em chat anterior — **inventariar primeiro**:
`apollo_emailer_campaigns_search` (MCP) lista sequências existentes na conta;
conferir o que já foi criado lá antes de criar de novo.

## 3. Regras da casa que valem aqui (resumo do CLAUDE.md)

- Chaves/tokens NUNCA em chat ou commit; `.env` local só.
- Backend testa com `.venv\Scripts\python.exe -m pytest` (pytest solto quebra).
- Toda mudança fecha com teste ANTES do commit.
- Banco: projeto Supabase `epgedaiukjippepujuzc`, schema `gymsite`
  (compartilhado com Vectra Cargo — cuidado). Dinheiro em centavos, UTC.
- ⚠️ Coluna nova em tabela do gymsite → atualizar a VIEW espelho em `public`
  (lista explícita de colunas; senão PGRST204 e a gravação falha em silêncio).
- Git: branch a partir de `origin/main` (`git checkout -b feat/x origin/main` —
  a árvore local tem frente paralela suja, não usar `checkout main`).
  PR pra main; checks do GitHub Actions estão QUEBRADOS por billing — ignorar;
  o deploy real é Cloud Build (projeto `gen-lang-client-0106729343`, us-central1).
- E-mails/sequências: NUNCA ativar envio sem aprovação explícita do Marcelo —
  criar em rascunho/pausado e pedir revisão.

## 4. Próximos passos sugeridos (validar com o Marcelo no novo chat)

1. Inventário: sequências/campanhas existentes na conta Apollo (MCP) + estado
   do `apollo_crm_sync` (rodou? oportunidades sincadas? conferir tabela).
2. Retomar a sequência: definir público (status de oportunidade), copy dos
   passos, cadência — em RASCUNHO pra aprovação.
3. Inventariar `docs/marketing/` e listar o que estava planejado vs parado.
4. Plano de marketing: amarrar com o produto atual (relatório auditado é o
   argumento de venda — margem/imposto/BE agora fecham na conferência).

## 5. O que NÃO é desta frente

Auditoria de quadros do relatório, motor financeiro (A4), ERRC/A9, fila de
tasks #26–#39 — tudo isso segue no chat original. Se esbarrar em bug dessas
áreas, ANOTAR aqui embaixo e avisar, não corrigir.

## 6. Log de passagem (o novo chat escreve aqui)

- (vazio)
