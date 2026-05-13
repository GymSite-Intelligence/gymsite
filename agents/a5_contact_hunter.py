# agents/a5_contact_hunter.py
"""
A5 — ContactHunter (decisor + script de abordagem).

REFATOR Task #57:
Substituídas 4 tools (identificar_tipo_ponto + buscar_cnpj + gerar_script_abordagem
+ formatar_contato_whatsapp) por 1 macro: `gerar_contato_decisor_completo`.
A5 antigo iterava em 3 calls do LLM (~112k tok = 27% custo total).
Mesmo padrão A1/A3a/A3b/A4 — eliminação consistente de round-trips.

FIX 2026-05-12:
Em alguns runs (Blumenau, Florianópolis) o LLM emitia 0 tokens output após
chamar a tool — `output_key` salvava string vazia e sobrescrevia o que a
macro-tool gerou. Sintoma: `contato_decisor: {}` na DB → viewer renderizava
section órfã. Fix: after_agent_callback que detecta state vazio e
re-executa a macro-tool em Python (idempotente, determinística). Garante
que SEMPRE há dados úteis pro A6 consolidar e pro frontend mostrar.
"""
import json

from google.adk.agents import Agent
from tools.contact_tools import gerar_contato_decisor_completo


def _a5_fallback_after_agent(callback_context):
    """Se o LLM emitiu vazio, popula state['contato_decisor'] com o output da macro.

    No final, encaminha pro state_dump telemetry (que `_attach_telemetry` pula
    porque já existe callback definido aqui).
    """
    try:
        state = callback_context.state
        current = state.get("contato_decisor")
        is_empty = (
            not current
            or (isinstance(current, str) and not current.strip())
            or (isinstance(current, dict) and not current)
        )
        if is_empty:
            result = gerar_contato_decisor_completo(callback_context)
            if isinstance(result, dict) and result:
                state["contato_decisor"] = result
                try:
                    preview = json.dumps(result, ensure_ascii=False)[:200]
                    print(f"[A5 fallback] LLM vazio - repopulado via macro-tool: {preview}...")
                except Exception:
                    pass
    except Exception as e:
        print(f"[A5 fallback] erro: {type(e).__name__}: {e}")

    # Encaminha pra telemetria (chain manual)
    try:
        from tools.state_diagnostics import after_agent_state_dump
        after_agent_state_dump(callback_context)
    except Exception:
        pass


contact_hunter_agent = Agent(
    name="ContactHunter",
    model="gemini-2.5-flash",
    description=(
        "Identifica decisor do imóvel candidato #1 e gera script de abordagem "
        "WhatsApp/ligação personalizado, via macro-tool determinística."
    ),
    instruction="""
agente: A5 ContactHunter
papel: identificar decisor + script de abordagem do candidato #1
regra_execucao: autonoma  # nunca pede confirmação ao usuário

input:
  candidato_top_1: lido do session.candidatos_geoscout (output do A1)
  cidade: lido do session.market_context (output do A0)

fluxo_obrigatorio (2 passos APENAS):
  - passo: 1
    acao: gerar_contato_decisor_completo()
    nota_critica: |
      Esta macro-tool faz TUDO em 1 chamada determinística:
        1. Lê top 1 candidato do session state
        2. Classifica tipo do ponto (supermercado, loja, etc)
        3. Decide canal recomendado (WHATSAPP/LIGACAO/EMAIL/LINKEDIN)
        4. Gera script de abordagem personalizado (template fixo + variáveis)
        5. Formata link WhatsApp se telefone disponível (raro)
        6. Calcula nível de confiança e próximos passos

      VOCÊ é apenas redator. NÃO chame as 4 tools antigas separadamente.
      Padrão idêntico ao A1/A3a/A3b/A4.

  - passo: 2
    acao: emitir JSON de saída final
    instrucao: |
      Pegue o output da macro-tool e devolva-o LITERAL como o JSON
      esperado pelo A6. Você pode adicionar 1-2 frases de contexto
      executivo se desejar, mas NÃO altere os campos da macro.

saida_obrigatoria_json:
  tipo_ponto: string
  decisor_identificado: string
  empresa: string
  telefone: string
  email: string
  whatsapp_link: string
  canal_recomendado: WHATSAPP|LIGACAO|EMAIL|LINKEDIN
  observacao_canal: string
  melhor_horario: string
  script_abordagem: string  # script completo já formatado
  nivel_confianca_contato: ALTO|MEDIO|BAIXO
  proximos_passos: [string]
  top_candidato_referencia: {nome, endereco, tipo_ponto, score_geoscout}

regras_payload:
  - NÃO chame tools além de `gerar_contato_decisor_completo`.
  - NÃO regenere o script — copie literal do output da macro.
  - NÃO peça dados ao usuário; A5 SEMPRE executa com fallbacks padrão.
""",
    tools=[
        gerar_contato_decisor_completo,
    ],
    output_key="contato_decisor",
    after_agent_callback=_a5_fallback_after_agent,
)
