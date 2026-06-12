"""Conversational Engine — núcleo do Agente de IA Especialista em Fitness.

Responsabilidades:
  1. Classificar intenção da mensagem do usuário
  2. Extrair slots (parâmetros) do texto livre, detectando incerteza declarada
  3. Slot-filling: perguntar o que falta de forma natural
  4. Propor configuração final e aguardar confirmação explícita do usuário
  5. Disparar o pipeline de relatório somente após o usuário confirmar

Máquina de estados da sessão:
  coletando_slots → aguardando_confirmacao → pronto_para_pipeline → pipeline_rodando

Defaults NUNCA são aplicados silenciosamente (BUG-001): quando o usuário declara
não saber um parâmetro ("ainda não sei o tamanho"), o slot entra em `_incertos`,
deixa de ser perguntado e a proposta final apresenta a sugestão de forma explícita
para o usuário aceitar ou ajustar.

Tom conversacional: estruturado, profissional e especialista no setor fitness,
como um consultor sênior de expansão de franquias de academia.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from services.chat_state import (
    ChatSession,
    criar_sessao,
    buscar_ultima_sessao_ativa,
    atualizar_sessao,
    adicionar_mensagem,
)
from tools._genai_client import build_genai_client, generate_content_resilient
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# Slots obrigatórios e opcionais para criação de relatório
SLOTS_OBRIGATORIOS = {"cidade", "bairro"}
SLOTS_OPCIONAIS = {
    "uf",
    "area_m2_min",
    "area_m2_max",
    "tamanho_preset",
    "publico_alvo",
    "genero_alvo",
    "tipo_negocio",
    "estacionamento_obrigatorio",
}
SLOTS_TODOS = SLOTS_OBRIGATORIOS | SLOTS_OPCIONAIS

# Defaults quando o usuário não especifica
DEFAULTS = {
    "tamanho_preset": "m",
    "publico_alvo": "25-40",
    "genero_alvo": "misto",
    "tipo_negocio": "academia",
    "estacionamento_obrigatorio": True,
}

# Mapeamento tamanho_preset → área
TAMANHO_PRESET_AREAS = {
    "pp": (200, 500),
    "p": (500, 800),
    "m": (800, 1500),
    "g": (1500, 2500),
    "gg": (2500, 5000),
}

# Chave reservada dentro do JSONB `slots` da sessão para slots que o usuário
# declarou explicitamente não saber. Prefixo "_" a exclui dos slots reais.
INCERTOS_KEY = "_incertos"

ROTULOS_SLOTS = {
    "tipo_negocio": "Tipo de negócio",
    "tamanho_preset": "Tamanho",
    "publico_alvo": "Público-alvo",
    "genero_alvo": "Perfil de público",
    "estacionamento_obrigatorio": "Estacionamento",
}


def _llm_call(system_prompt: str, user_prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    """Chamada unificada ao Gemini para classificação e extração.

    thinking_budget=0: tarefas mecânicas (classificar/extrair JSON). No 2.5 os
    thought tokens CONSOMEM max_output_tokens — com thinking dinâmico o JSON
    saía truncado ("```json" cortado) e extrair_slots devolvia {} em loop
    (regressão pega no E2E de 2026-06-12)."""
    client = build_genai_client()
    model = os.getenv("TINKER_FALLBACK_MODEL", "gemini-2.5-flash")
    response = generate_content_resilient(
        client,
        model=model,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max(max_tokens, 1024),
            temperature=temperature,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),  # pyright: ignore[reportCallIssue]
        ),
    )
    return response.text or ""


# ── 1. Classificador de Intenção ───────────────────────────────────────────

_PROMPT_CLASSIFICACAO = """Você é um classificador de intenção para um Agente de IA Especialista em Fitness e Expansão de Franquias de Academia.

Classifique a mensagem do usuário em UMA das categorias abaixo. Responda APENAS com o JSON:
{"intencao": "...", "confianca": 0.0-1.0}

Categorias:
- "novo_relatorio": usuário quer criar uma análise de viabilidade para abrir academia (ex: "quero abrir", "analise para", "viabilidade de")
- "pergunta_simples": pergunta sobre um relatório já existente (ex: "qual o veredito", "e a concorrência", "quanto custa")
- "status_relatorio": pergunta sobre andamento de relatório (ex: "como está", "já ficou pronto", "demora quanto")
- "ajuda": pedido de ajuda ou listagem de capacidades (ex: "o que você faz", "me ajuda", "como funciona")
- "clarificacao": resposta a uma pergunta direta do agente (ex: usuário responde "Fortaleza" quando perguntamos a cidade)
- "encerrar": usuário quer encerrar conversa (ex: "tchau", "obrigado", "é só isso")
- "fora_de_escopo": pedido de conselho de investimento financeiro, criptomoedas, ações,
  consultoria jurídica/tributária/médica, ou qualquer tema sem relação com abertura,
  expansão ou operação de academias (ex: "qual cripto compro", "como declaro imposto",
  "me indica uma ação", "dieta para emagrecer")
- "indefinido": não encaixa em nenhuma categoria

Na dúvida entre "fora_de_escopo" e outra categoria, escolha "fora_de_escopo" apenas
quando o pedido claramente NÃO é sobre o negócio de academias.
"""

# Recusa determinística — nunca passa por LLM (guardrail vídeo 01 / T01.1).
_RESPOSTA_FORA_DE_ESCOPO = (
    "Esse assunto está fora do meu campo — meu trabalho é viabilidade e expansão "
    "de academias: análise de bairro, concorrência, preços e plano de abertura.\n\n"
    "Quer que eu analise a viabilidade de uma academia em algum bairro?"
)

# Aviso legal — exibido UMA vez por sessão (T01.3).
_DISCLAIMER = (
    "\n\n---\n*Análise informativa baseada em dados públicos — não constitui "
    "recomendação de investimento.*"
)


def classificar_intencao(mensagem: str) -> tuple[str, float]:
    user_prompt = f'Mensagem do usuário: "{mensagem}"'
    texto = _llm_call(_PROMPT_CLASSIFICACAO, user_prompt, max_tokens=128, temperature=0.1)
    try:
        data = json.loads(texto.strip().replace("```json", "").replace("```", "").strip())
        return data.get("intencao", "indefinido"), float(data.get("confianca", 0.5))
    except Exception:
        logger.warning("Falha ao classificar intenção. Fallback para clarificacao. Texto: %s", texto)
        return "clarificacao", 0.5


# ── 2. Extrator de Slots ──────────────────────────────────────────────────

_PROMPT_EXTRACAO = """Você é um extrator de parâmetros para análise de viabilidade de franquias de academia no Brasil.

Extraia do texto do usuário os seguintes campos. Responda APENAS com JSON válido:
{
  "cidade": string | null,
  "bairro": string | null,
  "uf": string | null,
  "tamanho_preset": "pp" | "p" | "m" | "g" | "gg" | null,
  "publico_alvo": "18-25" | "25-40" | "30-50" | "40+" | null,
  "genero_alvo": "misto" | "predom_fem" | "predom_masc" | "excl_fem" | "excl_masc" | null,
  "tipo_negocio": "academia" | "crossfit_box" | "studio_pilates" | "studio_funcional" | "outro" | null,
  "estacionamento_obrigatorio": boolean | null,
  "area_m2_min": number | null,
  "area_m2_max": number | null,
  "incerto": string[]
}

Regras:
- Inferir UF a partir da cidade quando possível.
- "pequena" → "p", "média" → "m", "grande" → "g", "mini" → "pp", "mega" → "gg".
- "jovem" → "18-25", "adulto" → "25-40", "maturidade" → "30-50", "terceira idade" → "40+".
- "só mulher" → "excl_fem", "só homem" → "excl_masc", "mais mulher" → "predom_fem", "mais homem" → "predom_masc".
- Campos não mencionados devem ser null.
- "incerto": liste os NOMES dos campos que o usuário declarou explicitamente não saber,
  não ter decidido ou deixar a critério do consultor. Exemplos:
  "ainda não sei o tamanho" → ["tamanho_preset"]
  "não decidi o modelo" → ["tipo_negocio"]
  "tanto faz o público" / "você decide" → o campo em questão
  Um campo declarado incerto NUNCA deve receber valor — fica null e entra em "incerto".
  Se nada foi declarado incerto, retorne [].
"""


def extrair_slots(mensagem: str, slots_atuais: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Retorna (slots extraídos, campos declarados incertos pelo usuário)."""
    user_prompt = f'Texto do usuário: "{mensagem}"\nSlots já coletados: {json.dumps(slots_atuais, ensure_ascii=False)}'
    texto = _llm_call(_PROMPT_EXTRACAO, user_prompt, max_tokens=512, temperature=0.2)
    try:
        data = json.loads(texto.strip().replace("```json", "").replace("```", "").strip())
        incertos = [s for s in (data.get("incerto") or []) if s in SLOTS_OPCIONAIS]
        slots = {k: v for k, v in data.items() if k in SLOTS_TODOS and v is not None}
        return slots, incertos
    except Exception:
        logger.warning("Falha ao extrair slots. Texto: %s", texto)
        return {}, []


# ── 3. Slot-filler (pergunta o que falta) ─────────────────────────────────

_PROMPT_SLOT_FILLER = """Você é um Agente de IA Especialista em Expansão de Franquias de Academia no Brasil.
Converse de forma estruturada, profissional e natural — como um consultor sênior guiando um franqueado.

Contexto:
- O usuário quer criar uma análise de viabilidade.
- Já temos alguns dados, mas faltam informações.
- Pergunte de forma educada e direta o que falta.
- Se for apenas UF faltando, pergunte de forma leve ("Para confirmar, qual o estado?").
- Se faltar vários dados, faça uma pergunta por vez, priorizando cidade e bairro primeiro.
- NUNCA peça área em m² diretamente — pergunte o tamanho do negócio (pequeno, médio, grande).
- NUNCA use termos técnicos como "slots" ou "parâmetros".

Regras de confiança (obrigatórias):
- NUNCA cite números de mercado (população, renda, preço) de memória — você não tem
  esses dados nesta conversa; eles virão no relatório, com fonte.
- Se mencionar característica de cidade/bairro, mantenha-se em afirmações qualitativas
  gerais, sem inventar estatísticas.
- Nomeie entidades por completo na primeira menção ("o bairro Bessa, em João Pessoa"),
  nunca "lá"/"a região" sem antecedente claro.

Slots já coletados: {{slots}}
Slots faltando: {{faltando}}

Responda com uma única mensagem conversacional em português.
"""


def gerar_pergunta_followup(slots: dict[str, Any], faltando: list[str]) -> str:
    if not faltando:
        return ""
    user_prompt = (
        f"Slots já coletados: {json.dumps(slots, ensure_ascii=False)}\n"
        f"Slots faltando: {json.dumps(faltando, ensure_ascii=False)}"
    )
    return _llm_call(_PROMPT_SLOT_FILLER, user_prompt, max_tokens=512, temperature=0.4).strip()


# ── 4. Helpers: slots reais, incertos, defaults e proposta ────────────────


def _slots_reais(slots: dict[str, Any]) -> dict[str, Any]:
    """Slots de domínio, sem chaves internas (prefixo `_`)."""
    return {k: v for k, v in slots.items() if not k.startswith("_")}


def _incertos_sessao(slots: dict[str, Any]) -> list[str]:
    return [s for s in (slots.get(INCERTOS_KEY) or []) if s in SLOTS_OPCIONAIS]


def _aplicar_defaults(slots: dict[str, Any]) -> dict[str, Any]:
    """Preenche lacunas com defaults. Chamar SOMENTE após o usuário confirmar
    a proposta (aguardando_confirmacao → pronto_para_pipeline) — nunca durante
    a coleta, para não mascarar o que ainda falta perguntar (BUG-001)."""
    result = dict(DEFAULTS)
    result.update(_slots_reais(slots))
    preset = result.get("tamanho_preset", "m")
    if preset in TAMANHO_PRESET_AREAS and not result.get("area_m2_min"):
        result["area_m2_min"], result["area_m2_max"] = TAMANHO_PRESET_AREAS[preset]
    return result


def _slots_faltando(slots: dict[str, Any]) -> list[str]:
    reais = _slots_reais(slots)
    return [s for s in SLOTS_OBRIGATORIOS if not reais.get(s)]


def _slots_a_perguntar(slots: dict[str, Any]) -> list[str]:
    """Slots ainda não coletados. Obrigatórios sempre; opcionais chave só se o
    usuário não os declarou incertos — incerteza declarada não vira pergunta
    repetida, vira sugestão explícita na proposta de confirmação."""
    faltando = _slots_faltando(slots)
    if not faltando:
        reais = _slots_reais(slots)
        incertos = _incertos_sessao(slots)
        for opt in ["tamanho_preset", "publico_alvo", "tipo_negocio"]:
            if not reais.get(opt) and opt not in incertos:
                faltando.append(opt)
    return faltando


_PROMPT_CONFIRMACAO = """Você analisa a resposta de um usuário a uma proposta de configuração de análise de viabilidade.

A proposta listou os parâmetros (cidade, bairro, tipo, tamanho, público) e perguntou se pode seguir.

Classifique a resposta do usuário. Responda APENAS com o JSON:
{"decisao": "confirmar" | "ajustar" | "cancelar"}

- "confirmar": concordância clara ("sim", "pode seguir", "fechado", "perfeito", "manda ver", "ok")
- "ajustar": o usuário quer mudar algum parâmetro ("na verdade quero crossfit", "muda para grande", "prefiro público jovem", "sem estacionamento")
- "cancelar": o usuário desiste ou não quer prosseguir agora ("deixa pra lá", "não quero mais", "depois eu vejo")

Em caso de dúvida entre confirmar e ajustar, escolha "ajustar".
"""


def _detectar_confirmacao(mensagem: str) -> str:
    texto = _llm_call(_PROMPT_CONFIRMACAO, f'Resposta do usuário: "{mensagem}"', max_tokens=64, temperature=0.1)
    try:
        data = json.loads(texto.strip().replace("```json", "").replace("```", "").strip())
        decisao = data.get("decisao", "ajustar")
        return decisao if decisao in ("confirmar", "ajustar", "cancelar") else "ajustar"
    except Exception:
        logger.warning("Falha ao detectar confirmação. Texto: %s", texto)
        return "ajustar"


def _formatar_valor_slot(slot: str, valor: Any) -> str:
    if slot == "tamanho_preset":
        faixa = TAMANHO_PRESET_AREAS.get(valor)
        sufixo = f" ({faixa[0]}–{faixa[1]} m²)" if faixa else ""
        return f"{str(valor).upper()}{sufixo}"
    if slot == "publico_alvo":
        return f"{valor} anos"
    if slot == "tipo_negocio":
        return str(valor).replace("_", " ").title()
    if slot == "genero_alvo":
        return str(valor).replace("_", " ").replace("predom", "predominantemente").replace("excl", "exclusivamente")
    if slot == "estacionamento_obrigatorio":
        return "necessário" if valor else "não necessário"
    return str(valor)


def _mensagem_proposta(slots: dict[str, Any]) -> str:
    """Resumo da configuração com sugestões marcadas explicitamente.
    Nada é assumido em silêncio: todo default aparece como '(sugestão)' e o
    usuário precisa confirmar antes de o pipeline rodar."""
    reais = _slots_reais(slots)
    incertos = _incertos_sessao(slots)
    finais = _aplicar_defaults(slots)

    cidade = finais.get("cidade", "")
    bairro = finais.get("bairro", "")
    uf = finais.get("uf", "")
    local = f"**{bairro}**, {cidade}" + (f"/{uf}" if uf else "")

    linhas = []
    assumidos_rotulos = []
    for slot in ("tipo_negocio", "tamanho_preset", "publico_alvo", "genero_alvo", "estacionamento_obrigatorio"):
        rotulo = ROTULOS_SLOTS[slot]
        valor = _formatar_valor_slot(slot, finais.get(slot))
        if reais.get(slot) is not None:
            linhas.append(f"• {rotulo}: {valor}")
        else:
            linhas.append(f"• {rotulo}: {valor} *(sugestão)*")
            assumidos_rotulos.append(rotulo.lower())

    msg = f"Antes de começar, deixa eu confirmar a configuração da análise para {local}:\n\n"
    msg += "\n".join(linhas) + "\n\n"
    if incertos or assumidos_rotulos:
        msg += (
            "Para os itens que você ainda não definiu, sugeri os valores mais comuns "
            "nesse perfil de mercado — dá para refinar depois com os dados do relatório.\n\n"
        )
    msg += "Posso seguir com essa configuração? Se quiser ajustar qualquer item, é só me dizer."
    return msg


# ── 5. Dispatcher ─────────────────────────────────────────────────────────


def _mensagem_confirmacao(slots: dict[str, Any]) -> str:
    cidade = slots.get("cidade", "")
    bairro = slots.get("bairro", "")
    uf = slots.get("uf", "")
    tamanho = slots.get("tamanho_preset", "m").upper()
    publico = slots.get("publico_alvo", "25-40")
    tipo = slots.get("tipo_negocio", "academia")
    return (
        f"Perfeito! Estou preparando sua análise de viabilidade para **{bairro}**, {cidade}/{uf}.\n\n"
        f"Resumo do que entendi:\n"
        f"• Tipo: {tipo.replace('_', ' ').title()}\n"
        f"• Tamanho: {tamanho} ({slots.get('area_m2_min')}–{slots.get('area_m2_max')} m²)\n"
        f"• Público-alvo: {publico} anos\n\n"
        f"O relatório ficará pronto em alguns minutos. Você pode acompanhar o andamento por aqui."
    )


# ── Processar mensagem ────────────────────────────────────────────────────

_DISCLAIMER_KEY = "_disclaimer_mostrado"


def _com_disclaimer(sessao: Any, retorno: dict[str, Any]) -> dict[str, Any]:
    """Anexa o aviso legal à PRIMEIRA resposta da sessão (T01.3) e marca a
    flag em slot interno (prefixo `_` fica fora de `_slots_reais`)."""
    if retorno.get("resposta") and not (sessao.slots or {}).get(_DISCLAIMER_KEY):
        retorno["resposta"] = retorno["resposta"] + _DISCLAIMER
        atualizar_sessao(sessao.id, slots={**sessao.slots, _DISCLAIMER_KEY: True})
    return retorno


def processar_mensagem(
    user_id: str,
    mensagem: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Processa uma mensagem do usuário no fluxo conversacional.

    Retorna dict com:
      session_id, intencao, slots, slots_faltando, resposta,
      relatorio_id, status
    """
    # 1. Recuperar ou criar sessão
    if session_id:
        from services.chat_state import buscar_sessao
        sessao = buscar_sessao(session_id)
    else:
        sessao = buscar_ultima_sessao_ativa(user_id)

    if not sessao:
        sessao = criar_sessao(user_id)

    # 2. Classificar intenção
    intencao, confianca = classificar_intencao(mensagem)

    # Guardrail (vídeo 01): fora de escopo recusa SEM herdar intenção da sessão
    # e sem tocar slots — recusa determinística, pipeline jamais dispara daqui.
    if intencao == "fora_de_escopo":
        return _com_disclaimer(sessao, {
            "session_id": sessao.id,
            "intencao": "fora_de_escopo",
            "slots": _slots_reais(sessao.slots),
            "slots_faltando": [],
            "resposta": _RESPOSTA_FORA_DE_ESCOPO,
            "relatorio_id": None,
            "status": sessao.status,
        })

    # Se a sessão já tinha intenção definida e o usuário respondeu algo vago,
    # tratamos como clarificacao para continuar o slot-filling
    if sessao.intencao and intencao in ("indefinido", "clarificacao"):
        intencao = sessao.intencao

    # 3. Salvar intenção na sessão
    if intencao != sessao.intencao:
        sessao = atualizar_sessao(sessao.id, intencao=intencao)

    # 4. Roteamento por intenção
    if intencao == "encerrar":
        atualizar_sessao(sessao.id, status="encerrado")
        return {
            "session_id": sessao.id,
            "intencao": "encerrar",
            "slots": sessao.slots,
            "slots_faltando": [],
            "resposta": "Foi um prazer ajudar! Se precisar de mais análises ou tiver dúvidas sobre o setor fitness, é só chamar. 💪",
            "relatorio_id": None,
            "status": "encerrado",
        }

    if intencao == "ajuda":
        return _com_disclaimer(sessao, {
            "session_id": sessao.id,
            "intencao": "ajuda",
            "slots": sessao.slots,
            "slots_faltando": [],
            "resposta": (
                "Sou o especialista em expansão de academias. O que eu faço:\n\n"
                "1. **Análise de viabilidade** — concorrência, preços, demografia e imóveis "
                "disponíveis em qualquer bairro do Brasil\n"
                "2. **Comparação de bairros** — alternativas ranqueadas quando o bairro está saturado\n"
                "3. **Plano de abertura** — cronograma e fornecedores a partir do relatório\n\n"
                "O que eu **não** faço: recomendação de investimento financeiro.\n\n"
                'Exemplos: *"academia média no Bessa, João Pessoa"* · '
                '*"compare Cocó e Aldeota em Fortaleza"*'
            ),
            "relatorio_id": None,
            "status": sessao.status,
        })

    if intencao in ("pergunta_simples", "status_relatorio"):
        # Usa o chat Q&A existente (tinker_bot) — delegamos para o endpoint /chat
        return {
            "session_id": sessao.id,
            "intencao": intencao,
            "slots": sessao.slots,
            "slots_faltando": [],
            "resposta": None,  # Sinaliza para o caller usar o endpoint /chat
            "relatorio_id": sessao.relatorio_id,
            "status": sessao.status,
        }

    # 5. Sessão aguardando confirmação → interpretar resposta à proposta
    if sessao.status == "aguardando_confirmacao":
        decisao = _detectar_confirmacao(mensagem)

        if decisao == "confirmar":
            slots_finais = _aplicar_defaults(sessao.slots)
            sessao = atualizar_sessao(sessao.id, slots=slots_finais)
            return _com_disclaimer(sessao, {
                "session_id": sessao.id,
                "intencao": intencao,
                "slots": slots_finais,
                "slots_faltando": [],
                "resposta": _mensagem_confirmacao(slots_finais),
                "relatorio_id": None,  # Será preenchido pelo caller após criar stub
                "status": "pronto_para_pipeline",
            })

        if decisao == "cancelar":
            sessao = atualizar_sessao(sessao.id, status="coletando_slots")
            return {
                "session_id": sessao.id,
                "intencao": intencao,
                "slots": _slots_reais(sessao.slots),
                "slots_faltando": _slots_a_perguntar(sessao.slots),
                "resposta": (
                    "Sem problemas, não vou gerar a análise agora. "
                    "Se quiser mudar a cidade, o bairro ou qualquer outro detalhe, é só me dizer."
                ),
                "relatorio_id": None,
                "status": "coletando_slots",
            }

        # decisao == "ajustar" → extrai os ajustes e reapresenta a proposta

    # 6. Extrair slots (novo_relatorio, clarificacao ou ajuste da proposta)
    novos_slots, novos_incertos = extrair_slots(mensagem, _slots_reais(sessao.slots))
    incertos = [s for s in {*_incertos_sessao(sessao.slots), *novos_incertos} if s not in novos_slots]
    slots_merged = {**sessao.slots, **novos_slots, INCERTOS_KEY: incertos}
    sessao = atualizar_sessao(sessao.id, slots=slots_merged)

    # 7. Verificar o que ainda precisa ser perguntado
    faltando = _slots_a_perguntar(slots_merged)

    if faltando:
        pergunta = gerar_pergunta_followup(_slots_reais(slots_merged), faltando)
        if sessao.status == "aguardando_confirmacao":
            sessao = atualizar_sessao(sessao.id, status="coletando_slots")
        return _com_disclaimer(sessao, {
            "session_id": sessao.id,
            "intencao": intencao,
            "slots": _slots_reais(slots_merged),
            "slots_faltando": faltando,
            "resposta": pergunta,
            "relatorio_id": None,
            "status": "coletando_slots",
        })

    # 8. Nada mais a perguntar → propor configuração e aguardar confirmação
    #    explícita. O pipeline NUNCA dispara sem o usuário aceitar a proposta.
    sessao = atualizar_sessao(sessao.id, status="aguardando_confirmacao")
    return _com_disclaimer(sessao, {
        "session_id": sessao.id,
        "intencao": intencao,
        "slots": _slots_reais(slots_merged),
        "slots_faltando": [],
        "resposta": _mensagem_proposta(slots_merged),
        "relatorio_id": None,
        "status": "aguardando_confirmacao",
    })
