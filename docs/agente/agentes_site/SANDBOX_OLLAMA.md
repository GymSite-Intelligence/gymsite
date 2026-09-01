# Sandbox `/teste` + Ollama local

`/teste?dev_token=…` (prod) usa o **mesmo** chat da degustação: ADK + Eros RAG
(`knowledge-ask`, modelo **Gemini 3.6 Flash**). Bypass sem Turnstile/caps.

Chat do agente (prosa) no servidor: `LLM_PROVIDER` (NVIDIA/Ollama/Gemini).
Quando Gemini: `GYMSITE_SITE_MODEL=gemini-3.6-flash`.

## Blueprint: chat genérico → GymSite

```text
# processAIResponse (blueprint)              # GymSite (sandbox / consultor)
1. supabase messages by contactPhone   →  carregar_historico(projeto_id)
2. openai gpt-4 "assistente GymSite"   →  ADK agents_site.agent (especialistas)
                                          modelo = resolve_site_model()  # Ollama|NVIDIA|Gemini
3. Evolution sendText(WA)              →  salvar_mensagem(assistant) + poll HTTP
                                          (NÃO Evolution — WA é Eros)
```

| Job Redis / BackgroundTasks | Função |
|-----------------------------|--------|
| `site_conversar` | `run_site_agent_adk` — degustação / `/teste` |
| `consultor_conversar` | `run_consultor_adk` — app logado `/consultor` |

Enqueue: `POST /api/site-agent/conversar` ou `POST /api/consultor/conversar`.

## Pré-requisitos
1. Preferido: `LLM_PROVIDER=nvidia` + `NVIDIA_API_KEY` + `NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b`
2. Alternativa local: Ollama em `http://127.0.0.1:11434` + `LLM_PROVIDER=ollama`
3. Troca sem editar `.env`: UI `/admin/llm` → Redis override (`gymsite:llm_provider`)

```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=…
NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b
# ou:
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=llama3.2:3b
# OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Cloud Run **ignora** `LLM_PROVIDER=ollama` (detecta `K_SERVICE`) — use NVIDIA ou Gemini em prod.

Com Ollama local, o chat **não usa Redis compartilhado** (senão o `gymsite-worker` na nuvem
roubaria o job). Processa in-process via BackgroundTasks. NVIDIA/Gemini enfileiram normal.

## Subir API local

```powershell
cd c:\Users\marce\gymsite
# use o .venv que tem ADK + litellm
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
# ou: C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
```

Confirme no boot o log: `site_chat model=NVIDIA nvidia_nim/...` ou `site_chat model=Ollama ollama/...`.

## Front apontando pro local

`gymsite.com.br/teste` fala com **prod**. Pra sandbox local:

```powershell
cd frontend
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev
```

Admin: `/admin/llm` (JWT + ADMIN_EMAILS / role admin).

## Trocar de volta pra Gemini (3.6 Flash)

```env
LLM_PROVIDER=gemini
GYMSITE_SITE_MODEL=gemini-3.6-flash
```

Ou na UI: Provedor de IA → Gemini / Voltar ao .env.
