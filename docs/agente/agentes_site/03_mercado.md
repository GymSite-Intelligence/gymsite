# <span style="color:#38bdf8">Agente 3 — GymSite · Mercado</span>

> <span style="color:#ef4444">⏸️ **Parcial.** RAG (qualitativo) configura agora. A **função viva** (concorrentes/demografia) entra via `FunctionTool` (ADK) apontando para `POST /api/tools/concorrentes` — entrego junto com o system prompt final quando ligar a tool, pra não configurar pela metade.</span>

## <span style="color:#38bdf8">Identidade</span>
- **Nome:** `GymSite · Mercado`
- **Descrição de roteamento (root → sub-agente):** Especialista em viabilidade de mercado e captação. Acione para concorrência no entorno, saturação do bairro, perfil de renda/população, e perguntas de "vale a pena abrir aqui" ou "como vocês calculam viabilidade".

## <span style="color:#38bdf8">Ferramentas</span>
- **RAG (Repositório de Dados Vertex AI):** `gymsite-market-docs_1782013477930` (display: "gymsite-market-docs") — ID completo com sufixo
  - Projeto `gen-lang-client-0106729343` · Local `global` · Coleção `default_collection`
- **Função viva (PENDENTE):** `buscar_concorrentes` → `POST https://<host>/api/tools/concorrentes` (header `X-API-Key`); entrada `cidade/bairro/uf/tipo_negocio/raio_metros`; saída `total_concorrentes / nivel_saturacao / concorrentes[]`.
- **Pesquisa Google:** ON
- **Contexto do URL:** OFF
- <span style="color:#f97316">**IAM:** ao linkar o data store → clicar **"Conceder permissões"** (passo do usuário)</span>

## <span style="color:#22c55e">Instruções (System Prompt)</span>
> <span style="color:#ef4444">Entregue junto com a `FunctionTool` (persona de captação/degustação + antifatiamento). Placeholder até ligar a função — não colar ainda.</span>

## <span style="color:#a855f7">5 perguntas de teste (Preview)</span>
1. Quantos concorrentes existem num raio de 1,5 km do bairro Cocó, em Fortaleza?
2. O bairro Pinheiros, em São Paulo, está saturado de academias?
3. Qual o perfil de renda e população do bairro Batel, em Curitiba?
4. Vale a pena abrir uma academia de musculação no Meireles, Fortaleza?
5. Como vocês calculam a viabilidade de uma academia? (puxa RAG qualitativo)

> <span style="color:#eab308">**Validação esperada:** perg. 1-4 = chama a função viva e devolve número real + saturação (sem inventar contagem); perg. 5 = RAG metodológico citando a base; nunca fabrica número.</span>
