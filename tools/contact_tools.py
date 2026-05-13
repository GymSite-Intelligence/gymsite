# tools/contact_tools.py
import httpx
from typing import Optional

RECEITA_WS_BASE = "https://www.receitaws.com.br/v1/cnpj"


def buscar_cnpj(cnpj: str) -> dict:
    """Consulta dados de PJ pelo CNPJ (ReceitaWS, pública, 3 req/min)."""
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    try:
        with httpx.Client(timeout=15) as c:
            data = c.get(f"{RECEITA_WS_BASE}/{cnpj_limpo}").json()
        if data.get("status") == "ERROR":
            return {"erro": data.get("message", "CNPJ não encontrado")}
        socios = [
            {"nome": s.get("nome", ""), "qualificacao": s.get("qual", "")}
            for s in data.get("qsa", [])
        ]
        return {
            "razao_social": data.get("nome", ""),
            "nome_fantasia": data.get("fantasia", ""),
            "cnpj": data.get("cnpj", ""),
            "telefone": data.get("telefone", ""),
            "email": data.get("email", ""),
            "endereco": (
                f"{data.get('logradouro','')} {data.get('numero','')}, "
                f"{data.get('bairro','')} - {data.get('municipio','')}/{data.get('uf','')}"
            ),
            "situacao": data.get("situacao", ""),
            "socios": socios,
        }
    except Exception as e:
        return {"erro": str(e)}


def gerar_script_abordagem(
    nome_decisor: Optional[str],
    nome_imovel: str,
    endereco: str,
    cidade: str,
    score_geral: float,
) -> str:
    """Gera script de abordagem para WhatsApp/ligação com o proprietário."""
    decisor = nome_decisor or "proprietário(a)"
    qualidade = (
        "excelente" if score_geral >= 8.0
        else "muito bom" if score_geral >= 6.0
        else "interessante"
    )
    return f"""
📍 *GymSite Intelligence — Script de Abordagem*
Canal: WhatsApp / Ligação
Para: {decisor} | Imóvel: {nome_imovel} — {endereco}

━━━━━━━━━━━━━━━━━━━━
ABERTURA
━━━━━━━━━━━━━━━━━━━━
"Olá, {decisor}! Tudo bem? Me chamo [SEU NOME], sou consultor de expansão de academias.

Identificamos o imóvel em {endereco}, {cidade}, como um ponto com potencial {qualidade}
para abertura de uma academia premium — analisamos fluxo, área, estacionamento
e perfil demográfico da região."

━━━━━━━━━━━━━━━━━━━━
QUALIFICAÇÃO
━━━━━━━━━━━━━━━━━━━━
- O imóvel ainda está disponível para locação?
- Qual seria o valor atual de aluguel?
- Há flexibilidade para carência de obras (3-4 meses)?
- Aceita benfeitoria como pagamento parcial do aluguel inicial?
- Quem é o responsável pela decisão final sobre o imóvel?

━━━━━━━━━━━━━━━━━━━━
PROPOSTA DE VALOR
━━━━━━━━━━━━━━━━━━━━
- Academias são inquilinos de longo prazo — contratos de 5 a 10 anos
- Geramos fluxo constante de pessoas e valorizamos o entorno comercial
- Investimento médio em obras e equipamentos: R$1,5M a R$2M no imóvel
- Podemos agendar visita técnica esta semana para avaliação formal?

━━━━━━━━━━━━━━━━━━━━
FECHAMENTO
━━━━━━━━━━━━━━━━━━━━
- Posso enviar nossa proposta formal por e-mail?
- Qual o melhor horário para conversarmos com mais calma?
- Temos interesse em avançar rápido — podemos protocolar uma proposta em até 48h.
""".strip()


def identificar_tipo_ponto(tipos_google: list[str]) -> str:
    """Classifica o tipo de ponto com base nos tipos retornados pelo Maps."""
    mapa = {
        "shopping_mall": "SHOPPING",
        "supermarket": "SUPERMERCADO_VAGO",
        "store": "LOJA_COMERCIAL",
        "gym": "ACADEMIA_EXISTENTE",
        "fitness_center": "FITNESS_EXISTENTE",
        "car_dealer": "CONCESSIONARIA",
        "restaurant": "RESTAURANTE",
        "establishment": "ESTABELECIMENTO_GENERICO",
    }
    for tipo in tipos_google:
        if tipo in mapa:
            return mapa[tipo]
    return "COMERCIAL_GENERICO"


def formatar_contato_whatsapp(telefone: str, mensagem_inicial: str) -> str:
    """Gera link wa.me para abertura direta no WhatsApp."""
    import urllib.parse
    tel = "".join(filter(str.isdigit, telefone))
    if not tel.startswith("55"):
        tel = "55" + tel
    msg_encoded = urllib.parse.quote(mensagem_inicial[:200])
    return f"https://wa.me/{tel}?text={msg_encoded}"


# ── Macro-tool consolidadora A5 (Task #57 — mesmo padrão A1/A3a/A3b/A4) ──
def gerar_contato_decisor_completo(tool_context) -> dict:
    """
    Macro-tool A5 ContactHunter — consolida 4 tools em 1 call.

    Por que existe (refinamento Fase 1):
    A5 antigo iterava em 3 calls do LLM (~112k tok = 27% do custo total),
    chamando tool por tool. Esta macro lê top 1 candidato do session state
    e executa todo o pipeline determinístico em código Python.

    Pipeline:
      1. Lê top1 de `candidatos_geoscout` no state
      2. identificar_tipo_ponto(tipos) — classifica tipo do imóvel
      3. Score viabilidade do A4 (se disponível) entra no script
      4. gerar_script_abordagem — script WhatsApp/ligação personalizado
      5. formatar_contato_whatsapp — só se telefone presente (raro p/ supermercados)
      6. Decide canal recomendado e timing baseado no tipo

    A5 vira "redator" com 1 tool, 1 call.
    """
    from tools.competitor_tools import _parse_market_context

    state = getattr(tool_context, "state", {}) or {}

    # Top 1 candidato (output do A1 GeoScout)
    geo = _parse_market_context(state.get("candidatos_geoscout"))
    candidatos = geo.get("candidatos") if isinstance(geo, dict) else []
    top1 = (candidatos or [{}])[0] if candidatos else {}

    # Fallbacks — A5 NUNCA pede dados ao usuário, sempre executa
    nome_imovel = top1.get("nome") or "Ponto comercial identificado na região de busca"
    endereco = top1.get("endereco") or ""
    tipos = top1.get("tipos") or ["establishment"]
    score_geral = float(top1.get("score_geoscout") or 6.0)
    telefone = top1.get("telefone") or ""

    # Cidade — vem do market_context (A0) ou endereço como fallback
    mc = _parse_market_context(state.get("market_context"))
    inner_mc = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
    cidade = (inner_mc.get("cidade") if isinstance(inner_mc, dict) else "") or "região alvo"

    # Tipo do ponto via tools determinística
    tipo_ponto = identificar_tipo_ponto(tipos)

    # Decisor — quando há CNPJ disponível tentamos enriquecer; aqui é raro,
    # pq candidatos GeoScout vêm de Maps (sem CNPJ direto)
    decisor = "proprietário(a)"

    # Estratégia por tipo (replica regras antigas do prompt do A5)
    estrategia_canal = {
        "SUPERMERCADO_VAGO": ("WHATSAPP", "Contato direto rede (RH/expansão)"),
        "ACADEMIA_EXISTENTE": ("LIGACAO", "Não abordar como concorrente — verificar venda/sublocação"),
        "FITNESS_EXISTENTE": ("LIGACAO", "Não abordar como concorrente — verificar venda/sublocação"),
        "LOJA_COMERCIAL": ("WHATSAPP", "Imobiliária provavelmente gerencia — pesquisar anúncio online"),
        "CONCESSIONARIA": ("LIGACAO", "Proprietário marca local ou holding regional"),
        "SHOPPING": ("EMAIL", "Departamento comercial do shopping"),
        "ESTABELECIMENTO_GENERICO": ("WHATSAPP", "Pesquisar CNPJ pelo endereço no Google Maps"),
        "COMERCIAL_GENERICO": ("WHATSAPP", "Pesquisar CNPJ pelo endereço no Google Maps"),
    }
    canal, observacao_canal = estrategia_canal.get(
        tipo_ponto, ("WHATSAPP", "Pesquisar contato via Google")
    )

    # Script de abordagem (síncrono)
    script = gerar_script_abordagem(
        nome_decisor=decisor,
        nome_imovel=nome_imovel,
        endereco=endereco,
        cidade=cidade,
        score_geral=score_geral,
    )

    # WhatsApp link só se telefone disponível (geralmente não está pra supermercados)
    whatsapp_link = "N/A"
    if telefone:
        try:
            whatsapp_link = formatar_contato_whatsapp(
                telefone, "Olá! Identificamos seu imóvel como ponto estratégico."
            )
        except Exception:
            whatsapp_link = "N/A"

    # Nível de confiança baseado em quanto temos dos dados
    tem_dados_basicos = bool(nome_imovel and endereco)
    tem_telefone = bool(telefone)
    tem_cnpj_disponivel = False  # não temos CNPJ direto do Maps
    if tem_telefone and tem_dados_basicos:
        confianca = "ALTO"
    elif tem_dados_basicos:
        confianca = "MEDIO"
    else:
        confianca = "BAIXO"

    proximos_passos = [
        f"Confirmar disponibilidade do imóvel '{nome_imovel}' para locação ou venda",
        "Pesquisar imobiliária ou administradora que gerencia o imóvel",
        f"Identificar CNPJ do estabelecimento atual via consulta na Receita Federal" if not tem_cnpj_disponivel else "Validar dados do CNPJ enriquecido",
        "Agendar visita técnica para medir pé-direito, vão livre e infraestrutura elétrica",
    ]

    return {
        "tipo_ponto": tipo_ponto,
        "decisor_identificado": decisor,
        "empresa": "N/A",  # Sem CNPJ não conseguimos enriquecer empresa real
        "telefone": telefone or "N/A",
        "email": "N/A",
        "whatsapp_link": whatsapp_link,
        "canal_recomendado": canal,
        "observacao_canal": observacao_canal,
        "melhor_horario": "Terça a quinta (melhor taxa de resposta); Segunda pela manhã (decisores receptivos); evitar sexta à tarde",
        "script_abordagem": script,
        "nivel_confianca_contato": confianca,
        "proximos_passos": proximos_passos,
        "top_candidato_referencia": {
            "nome": nome_imovel,
            "endereco": endereco,
            "tipo_ponto": tipo_ponto,
            "score_geoscout": score_geral,
        },
    }
