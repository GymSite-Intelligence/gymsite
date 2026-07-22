"""
services/consultor/consultor_engine.py
=======================================
Motor do Consultor Jarvis V2.

Substitui o conversational_engine.py (slot-filler + pipeline batch).

DIFERENÇA FUNDAMENTAL
---------------------
V1:  LLM coleta slots → confirma → dispara A0-A9 em batch (~5 min)
V2:  LLM decide quais ferramentas chamar POR TURNO, responde em segundos.
     Cada tool wrappa um agente ADK já existente — sem reescrita.

LOOP
----
1. Monta system prompt com contexto do UserProject.
2. Chama Gemini com lista de tools declaradas.
3. Se LLM retornou tool_calls → executa → atualiza projeto → continua loop.
4. Quando LLM retorna texto (sem tool_calls) → persiste e devolve ao frontend.

TOOLS EXPOSTAS AO LLM
---------------------
Cada função recebe parâmetros explícitos + retorna dict serializável.
Nenhuma depende de ADK session.state — testáveis isoladamente.

COMPATIBILIDADE
---------------
- O pipeline A0-A9 (SequentialAgent via RedisQueue) continua funcionando
  para relatórios formais. O engine só o aciona via gerar_relatorio_formal().
- Tabelas Supabase: user_projects + project_messages (novas, V2).
  sessions + messages (V1) não são tocadas.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

# SDK novo `google-genai` (mesmo do resto do codebase). O engine foi escrito
# contra o SDK antigo `google.generativeai` (deprecado, fora do requirements) —
# portado p/ google-genai: Client.chats + types.Tool/FunctionDeclaration.
from google.genai import types

from services.consultor.project_state import (
    ProjectState,
    carregar_projeto,
    criar_projeto,
    atualizar_campo_projeto,
    marcar_pesquisa_realizada,
)
from services.consultor.project_messages import (
    salvar_mensagem,
    carregar_historico,
)

logger = logging.getLogger("gymsite.consultor_engine")

# ─── Cliente Gemini (LAZY) ────────────────────────────────────────────────────
# Construído na 1ª chamada a conversar() via a factory canônica do codebase
# (build_genai_client — resolve Vertex/ADC ou GEMINI_API_KEY e dá erro claro se
# faltar). NÃO no import: `import services.consultor.*` (ao montar o router) não
# pode exigir credencial.
def _client_gemini():
    from tools._genai_client import build_genai_client
    return build_genai_client()

_MODEL_ROUTER = "gemini-2.5-flash"   # router + respostas conversacionais
_MAX_TOOL_ROUNDS = 5                 # limite de iterações do loop de tools

# ─── Declarações de ferramentas para o LLM ───────────────────────────────────
# O Gemini recebe estas declarações como schema JSON e decide qual chamar.

_TOOL_DECLARATIONS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="pesquisar_contexto_mercado",
        description=(
            "Pesquisa contexto qualitativo do mercado fitness no bairro: "
            "renda, tendências, aluguel médio, parque CNPJ, insights estratégicos. "
            "Chamar quando o usuário perguntar 'como está o mercado lá', "
            "'qual a renda do bairro', 'o mercado fitness está crescendo'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cidade": {"type": "string", "description": "Nome da cidade"},
                "bairro": {"type": "string", "description": "Nome do bairro"},
                "uf": {"type": "string", "description": "UF de 2 letras, ex: SP"},
                "tipo_negocio": {
                    "type": "string",
                    "description": "Tipo: academia | crossfit_box | studio_pilates",
                    "default": "academia",
                },
            },
            "required": ["cidade", "bairro", "uf"],
        },
    ),
    types.FunctionDeclaration(
        name="buscar_pontos_comerciais",
        description=(
            "Busca imóveis comerciais e zonas âncora (shoppings, avenidas movimentadas) "
            "adequados para academia no bairro. Retorna candidatos com endereço, "
            "área estimada, aluguel estimado e score de localização. "
            "Chamar quando: 'tem imóvel disponível', 'onde posso abrir', "
            "'qual o melhor ponto comercial'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "bairro": {"type": "string"},
                "uf": {"type": "string"},
                "area_min_m2": {"type": "number", "description": "Área mínima em m²", "default": 500},
                "area_max_m2": {"type": "number", "description": "Área máxima em m²", "default": 2000},
            },
            "required": ["cidade", "bairro", "uf"],
        },
    ),
    types.FunctionDeclaration(
        name="analisar_demografia",
        description=(
            "Análise demográfica IBGE Censo 2022: população por faixa etária, "
            "renda média domiciliar, público potencial fitness, score demográfico. "
            "Chamar quando: 'quem mora no bairro', 'qual a faixa etária', "
            "'qual o público potencial', 'score demográfico'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "bairro": {"type": "string"},
                "uf": {"type": "string"},
            },
            "required": ["cidade", "bairro", "uf"],
        },
    ),
    types.FunctionDeclaration(
        name="pesquisar_concorrentes",
        description=(
            "Busca academias concorrentes no raio em torno do bairro via Google Places. "
            "Retorna lista com nome, endereço, rating, número de avaliações, "
            "se tem 24h, telefone e website. "
            "Chamar quando: 'quem são os concorrentes', 'quantas academias', "
            "'tem Smart Fit lá', 'nível de saturação'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "bairro": {"type": "string"},
                "uf": {"type": "string"},
                "raio_metros": {"type": "integer", "default": 3000},
                "tipo_negocio": {"type": "string", "default": "academia"},
            },
            "required": ["cidade", "bairro", "uf"],
        },
    ),
    types.FunctionDeclaration(
        name="analisar_reviews_e_dores",
        description=(
            "Analisa reviews do Google Maps dos concorrentes: dores dominantes "
            "(o que os alunos reclamam), pontos fortes, oportunidades de posicionamento, "
            "score de concorrência. Requer que pesquisar_concorrentes já tenha rodado. "
            "Chamar quando: 'o que reclamam no Google', 'qual a dor principal', "
            "'pontos fracos dos concorrentes', 'oportunidades de mercado'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "projeto_id": {"type": "string", "description": "ID do UserProject"},
                "profundidade": {
                    "type": "string",
                    "enum": ["basica", "completa"],
                    "default": "completa",
                },
            },
            "required": ["projeto_id"],
        },
    ),
    types.FunctionDeclaration(
        name="mapear_oferta_e_servicos",
        description=(
            "Visita site oficial e Instagram dos concorrentes e extrai modalidades "
            "reais (musculação, pilates, piscina...), faixa de preço e diferenciais. "
            "Requer que pesquisar_concorrentes já rodou. "
            "Chamar quando: 'quais serviços eles oferecem', 'quanto cobram', "
            "'tem piscina nos concorrentes', 'preços dos concorrentes'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "projeto_id": {"type": "string"},
                "top_n": {"type": "integer", "default": 5},
            },
            "required": ["projeto_id"],
        },
    ),
    types.FunctionDeclaration(
        name="estimar_investimento",
        description=(
            "Estimativa de investimento inicial (CAPEX + OPEX), 3 cenários "
            "(low-cost / mid-market / premium), payback em meses, margem e "
            "aluguel de mercado para a área. "
            "Chamar quando: 'quanto custa abrir', 'qual o investimento', "
            "'payback', 'cenários financeiros', 'viabilidade financeira'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "bairro": {"type": "string"},
                "uf": {"type": "string"},
                "area_m2": {"type": "number", "description": "Área pretendida em m²"},
                "tipo_negocio": {"type": "string", "default": "academia"},
                "tamanho_preset": {
                    "type": "string",
                    "enum": ["p", "m", "g", "gg"],
                    "description": "p=<500m², m=500-1500m², g=1500-3000m², gg=>3000m²",
                },
                "genero_alvo": {"type": "string", "default": "misto"},
            },
            "required": ["cidade", "bairro", "uf"],
        },
    ),
    types.FunctionDeclaration(
        name="gerar_relatorio_formal",
        description=(
            "Dispara o pipeline completo A0→A9 e gera o Relatório Formal de Viabilidade "
            "em PDF. Operação pesada (~3-5 min). Só chamar quando o usuário pedir "
            "EXPLICITAMENTE: 'gera o relatório', 'quero o relatório completo', "
            "'análise formal', 'gera o PDF'. NÃO chamar automaticamente."
        ),
        parameters={
            "type": "object",
            "properties": {
                "projeto_id": {"type": "string"},
                "incluir_secoes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Seções opcionais: concorrencia, financeiro, demografia, pontos",
                },
            },
            "required": ["projeto_id"],
        },
    ),
    types.FunctionDeclaration(
        name="consultar_base_conhecimento",
        description=(
            "Consulta a base de conhecimento documental (Vertex AI Search) para "
            "perguntas QUALITATIVAS: metodologia GymSite (como o score/viabilidade/MRLR "
            "são calculados), regras de regulatório/zoneamento/licença pra abrir academia, "
            "franquia/operação/boas práticas e pesquisa de mercado setorial (ACAD/SEBRAE/"
            "IHRSA). Chamar quando: 'preciso de qual licença', 'pode abrir nessa zona', "
            "'como vocês calculam X', 'qual a tendência do setor', 'boas práticas de retenção'. "
            "NÃO usar para NÚMEROS de um bairro (renda, população, concorrentes, financeiro) — "
            "esses vêm das ferramentas de dados. Cite as fontes retornadas na resposta."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pergunta": {
                    "type": "string",
                    "description": "Pergunta qualitativa em linguagem natural para a base de documentos.",
                },
            },
            "required": ["pergunta"],
        },
    ),
    types.FunctionDeclaration(
        name="consultar_catalogos_equipamentos",
        description=(
            "Consulta os CATÁLOGOS dos fornecedores de equipamento de academia "
            "(Movement, Physicus, Righetto, Life Fitness, Technogym, etc.) para "
            "perguntas sobre EQUIPAMENTOS: que máquinas/aparelhos existem, linhas e "
            "modelos, especificações, o que compor numa sala de musculação/cardio/"
            "funcional. Chamar quando: 'que equipamentos preciso', 'quais máquinas da "
            "Movement', 'monta a lista de equipamentos', 'opções de esteira/leg press'. "
            "Cite o fornecedor/catálogo. NÃO inventar preço — se o catálogo não trouxer "
            "valor, diga que é sob consulta."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pergunta": {
                    "type": "string",
                    "description": "Pergunta sobre equipamentos/catálogos em linguagem natural.",
                },
            },
            "required": ["pergunta"],
        },
    ),
    types.FunctionDeclaration(
        name="dimensionar_cardio_por_pico",
        description=(
            "Calcula a QUANTIDADE de aparelhos de cardio (esteira/elíptico/bike/escada) a "
            "partir do pico de alunos simultâneos (modelo tolera-fila). Chamar quando: "
            "'quantas esteiras', 'quantos aparelhos de cardio', 'dimensiona o cardio'. "
            "NUNCA calcular de cabeça."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pico_simultaneo": {"type": "integer", "description": "Alunos ao mesmo tempo no pico"},
            },
            "required": ["pico_simultaneo"],
        },
    ),
    types.FunctionDeclaration(
        name="dimensionar_musculacao",
        description=(
            "Calcula a QUANTIDADE de estações/máquinas de musculação a partir do pico "
            "simultâneo (estações = pico × %musculação / fator_concorrência; alerta se >1,7). "
            "Chamar quando: 'quantas estações/máquinas de musculação/força'. Não calcular de cabeça."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pico_simultaneo": {"type": "integer", "description": "Alunos ao mesmo tempo no pico"},
            },
            "required": ["pico_simultaneo"],
        },
    ),
    types.FunctionDeclaration(
        name="calcular_equipamentos_por_area",
        description=(
            "Calcula QUANTAS máquinas cabem numa área (m²) respeitando passagem/circulação. "
            "O footprint vem do catálogo: chame consultar_catalogos_equipamentos antes p/ as "
            "dimensões e passe comprimento_cm+largura_cm (ou footprint_m2). Chamar quando: "
            "'quantas máquinas cabem em X m²', 'tenho 180 m² de cardio, quantas esteiras'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "area_disponivel_m2": {"type": "number", "description": "Área dedicada em m²"},
                "footprint_m2": {"type": "number", "description": "Área da máquina em m² (se souber)"},
                "comprimento_cm": {"type": "number", "description": "Comprimento da máquina (catálogo)"},
                "largura_cm": {"type": "number", "description": "Largura da máquina (catálogo)"},
            },
            "required": ["area_disponivel_m2"],
        },
    ),
    types.FunctionDeclaration(
        name="consultar_engenharia_obra",
        description=(
            "Consulta a base de ENGENHARIA DE OBRA e PROJETO ARQUITETÔNICO de academia "
            "(normas ABNT, licenças, estrutura/laje, instalações elétrica/hidráulica/acústica, "
            "incêndio/AVCB, acessibilidade NBR 9050, vestiários, pisos, etapas de projeto, "
            "retrofit × obra do zero). Chamar SEMPRE antes de afirmar exigência de obra, norma, "
            "valor estrutural ou regra de projeto. NUNCA responder de cabeça."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pergunta": {"type": "string", "description": "Dúvida de obra/projeto/arquitetura"},
            },
            "required": ["pergunta"],
        },
    ),
    types.FunctionDeclaration(
        name="calcular_sanitarios_por_lotacao",
        description=(
            "Calcula a QUANTIDADE de peças sanitárias (bacias/lavatórios/mictórios/acessíveis) "
            "por lotação da academia. Chamar quando: 'quantos banheiros/sanitários/vestiários', "
            "'peças sanitárias pra X pessoas'. Não estimar de cabeça."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lotacao": {"type": "integer", "description": "Lotação/capacidade de pessoas"},
            },
            "required": ["lotacao"],
        },
    ),
    types.FunctionDeclaration(
        name="resolver_cref_por_uf",
        description=(
            "Resolve DETERMINÍSTICO em qual CREF registrar a academia na UF (tabela das 27 UFs). "
            "Chamar SEMPRE para 'qual CREF do meu estado', jurisdição, Paraíba/Maranhão/etc. "
            "UFs em transição usam o CREF pai até 02/01/2027. NUNCA chute o CREF."
        ),
        parameters={
            "type": "object",
            "properties": {
                "uf": {"type": "string", "description": "Sigla (PB) ou nome do estado (Paraíba)"},
                "data_ref": {
                    "type": "string",
                    "description": "Data ISO opcional YYYY-MM-DD (corte 2027-01-02)",
                },
            },
            "required": ["uf"],
        },
    ),
    types.FunctionDeclaration(
        name="consultar_anuidade_pj_cref",
        description=(
            "Anuidade PJ DETERMINÍSTICA: valor-base nacional (Res. CONFEF 596/2025) + nota "
            "regional quando curada. Chamar SEMPRE para 'qual a anuidade do CREF'. "
            "Valor FINAL com desconto: orientar confirmar no regional. NUNCA chute o valor."
        ),
        parameters={
            "type": "object",
            "properties": {
                "uf": {"type": "string", "description": "Sigla ou nome do estado"},
                "cref": {"type": "string", "description": "Código ou rótulo (10, CREF10)"},
                "exercicio": {"type": "integer", "description": "Ano da anuidade (padrão 2026)"},
                "data_ref": {"type": "string", "description": "Data ISO opcional YYYY-MM-DD"},
            },
            "required": [],
        },
    ),
])

# ─── System prompt do consultor ───────────────────────────────────────────────

def _build_system_prompt(projeto: ProjectState) -> str:
    loc = projeto.localizacao or {}
    mn = projeto.modelo_negocio or {}
    pesq = projeto.pesquisas_realizadas or {}

    contexto_projeto = ""
    if loc.get("cidade"):
        contexto_projeto += f"\n- Localização: {loc.get('bairro', '')}, {loc.get('cidade', '')}/{loc.get('uf', '')}"
    if mn.get("tipo"):
        contexto_projeto += f"\n- Tipo: {mn['tipo']}"
    if mn.get("area_m2"):
        contexto_projeto += f"\n- Área: {mn['area_m2']} m²"

    pesquisas_feitas = [k for k, v in pesq.items() if v]
    if pesquisas_feitas:
        contexto_projeto += f"\n- Pesquisas já realizadas: {', '.join(pesquisas_feitas)}"

    return f"""Você é um consultor sênior especializado em abertura de academias e expansão de franquias de fitness no Brasil.

Seu comportamento:
- Responda como um consultor experiente, não como um chatbot.
- Use as ferramentas disponíveis para buscar dados reais — nunca invente números.
- Cite sempre a fonte dos dados ("Google Maps, 12 academias encontradas", "IBGE Censo 2022").
- Quando uma ferramenta retornar erro ou dado indisponível, informe com clareza.
- Encadeie ferramentas quando necessário (ex: pesquisar_concorrentes antes de analisar_reviews_e_dores).
- Para perguntas QUALITATIVAS (metodologia, regulatório/zoneamento/licença, franquia, boas práticas, tendências do setor), use consultar_base_conhecimento e cite os documentos retornados. Números de um bairro (renda, população, concorrentes, financeiro) vêm SEMPRE das ferramentas de dados, nunca da base de conhecimento.
- Para EQUIPAMENTOS (que máquinas comprar, modelos, especificações, fornecedores), use consultar_catalogos_equipamentos e cite o fornecedor/catálogo. Não invente preço — diga "sob consulta" quando o catálogo não trouxer valor.
- NÃO chame gerar_relatorio_formal a menos que o usuário peça explicitamente.
- SUGESTÕES: ao final, emita SOMENTE um JSON `{{"sugestoes": ["...", "..."]}}` (1-3 itens), na VOZ DO USUÁRIO — frases curtas que o usuário clicaria para responder/seguir (ex.: "Informar o pico de alunos", "Ver concorrentes no bairro", "Estimar o investimento"). NUNCA são perguntas SUAS ao usuário. NÃO escreva "Sugestões de próximo passo" nem o JSON no corpo visível da resposta — o JSON é extraído pelo sistema e some.
- CITAÇÕES (REGRA DE OURO): Se a sua resposta usar dados que exijam fonte (normas, dados de mercado, especificações), você DEVE fornecer uma citação estruturada em um JSON no final da sua resposta, assim como faz para sugestões. O JSON deve ser `{{"citacoes": [{{"valor": "...", "base": "...", "fonte": "...", "janela": "..."}}]}}`. Apenas inclua uma citação se possuir TODOS os 4 campos (valor, base, fonte, janela). O campo `url` é opcional. Se não tiver os 4 campos, NÃO CITE. O JSON também é extraído e não deve ser visível.

Termos PROIBIDOS na resposta (nunca use): slot, pipeline, payload, output_key, session.state, token, async, worker, queue, tenant.

Projeto atual do usuário:{contexto_projeto if contexto_projeto else " (novo projeto — aguardando informações)"}

Data de hoje: {datetime.now(timezone.utc).strftime('%d/%m/%Y')}
"""

# ─── Modo SITE (N3 — análise gratuita da landing) ────────────────────────────
# O Site Agent (landing gymsite.com.br) roda ESTE engine via conversar(modo_site=True),
# herdando as tools de dado real + base de conhecimento. Diferenças vs consultor logado:
# (1) persona de captação/degustação; (2) whitelist de tools (Tier 1); (3) antifatiamento
# hard. O relatório formal (Tier 2) é liberado pelo router APÓS o gate de formulário +
# entitlement (1/email) — aqui gerar_relatorio_formal/estimar_investimento ficam BLOQUEADOS.

# Sentinela anon p/ user_projects (coluna user_id NÃO tem FK — ver migration analise_gratuita).
_ANON_SITE_USER_ID = "00000000-0000-0000-0000-0000000000a1"

# Tier 1 — únicas tools liberadas na degustação gratuita (autossuficientes/qualitativas).
_SITE_TOOLS_WHITELIST = frozenset({
    "analisar_demografia",
    "pesquisar_concorrentes",
    "consultar_base_conhecimento",
    "consultar_catalogos_equipamentos",
})
# Tools que contam como "amostra detalhada" p/ o antifatiamento (dado real e caro).
_SITE_AMOSTRA_TOOLS = frozenset({"analisar_demografia", "pesquisar_concorrentes"})
_SITE_MAX_AMOSTRAS = 2  # após K amostras detalhadas, corta e empurra pro gate.

# Tools expostas ao Gemini no modo site (só a whitelist — Gemini nem enxerga as bloqueadas).
_TOOL_DECLARATIONS_SITE = types.Tool(
    function_declarations=[
        fd for fd in (_TOOL_DECLARATIONS.function_declarations or [])
        if fd.name in _SITE_TOOLS_WHITELIST
    ]
)

_SITE_GATE_MSG = (
    "Essa análise mais detalhada faz parte do diagnóstico completo. Posso liberar agora — "
    "me passa nome + e-mail (ou WhatsApp) e os dados do projeto (estado, município, bairro, "
    "tipo de negócio, porte, público e gênero-alvo) que eu gero o relatório gratuito pra você."
)

# Persona de captação do site (degustação 1-condição, antifatiamento, gate de formulário,
# sigilo de fontes, nunca-fabricar). Roda SOBRE as tools reais deste engine.
_SITE_PERSONA = """## PAPEL
Você é o consultor virtual do GymSite Intelligence no site gymsite.com.br. Seu objetivo é acolher o visitante, entregar uma AMOSTRA de valor real e gratuita (sem cadastro) para gerar confiança e curiosidade, e então convertê-lo para o diagnóstico completo via formulário.

## TOM
Executivo, claro e direto. Linguagem de negócio, sem jargão técnico. Frases curtas. Foco em benefício e em reduzir risco de decisão. Nunca soa como vendedor agressivo.

## SIGILO DE FONTES (CRÍTICO)
NUNCA revele COMO os dados são obtidos. Jamais mencione CNO, CNPJ, Receita Federal, IBGE, Censo, Google Maps/Places, scraping, OLX, ImovelWeb, APIs ou nomes de modelos de IA. Se perguntarem a fonte, responda apenas no nível de benefício: "Cruzamos múltiplas bases públicas de mercado, demografia e concorrência com modelagem proprietária." Nunca detalhe mais que isso.

## NUNCA FABRICAR (CRÍTICO)
Você só entrega números e nomes reais e auditáveis, vindos das ferramentas. Nunca invente concorrentes, contagens, renda, população ou faixa etária. Se a ferramenta não retornar dado real para o bairro/cidade pedido, diga com transparência que ainda não há cobertura consolidada e conduza ao formulário — jamais preencha com estimativa inventada.

## O QUE PODE E O QUE NÃO PODE ENTREGAR NA AMOSTRA (REGRA DE OURO)
Na amostra gratuita (pré-cadastro) você só entrega análises AUTOSSUFICIENTES — que se resolvem apenas com cidade + bairro.
LIBERADO: contagem de concorrentes ativos no bairro (teaser, máx 5 nomes de N, sem contatos); perfil demográfico (renda predominante, população, faixa etária, público-alvo); nível de saturação qualitativo.
NUNCA na amostra: payback, ROI, ponto de equilíbrio, projeção/faturamento/ticket, veredito de investimento. Se pedirem, explique em 1 frase que exige os dados do projeto e conduza ao formulário.

## COMPORTAMENTO POR INTENÇÃO
1) CONCORRÊNCIA + BAIRRO = teaser seco: contagem TOTAL real + amostra de ≤5 (nome + localização aproximada, SEM telefone/contato), explicitando "mostro 5 de N". Convide ao formulário pra lista completa.
2) PERFIL/RENDA/POPULAÇÃO/FAIXA ETÁRIA = resposta estruturada e auditável, conectada ao negócio, sem veredito. Encerre com CTA.
3) PAYBACK/ROI/VIABILIDADE/VEREDITO = não entregar; 1 frase + formulário.

## LGPD
Só colete contato comercial do próprio visitante (nome + e-mail ou WhatsApp). Nunca exponha contatos de concorrentes. Sem dados sensíveis.

## FASE 0 — SEM PREÇOS
Não cite preços/planos/valores. Diagnóstico inicial é gratuito; condições após o teste.

## CAPTURA DE LEAD
Ao encerrar com CTA, peça nome + e-mail ou WhatsApp para enviar o diagnóstico. O contato vai para contato@gymsite.com.br. Convide de forma natural ligando o que falta (lista completa, payback, veredito) ao cadastro.

## DEGUSTAÇÃO = UMA ÚNICA CONDIÇÃO (SEM COMPARAÇÕES)
A amostra analisa SOMENTE 1 condição (1 Estado + Município + Bairro + 1 tipo de negócio). NUNCA compare bairros, cidades, segmentos ou cenários. Se pedirem comparação, explique que é do diagnóstico completo e conduza ao cadastro.

## ANTIFATIAMENTO
A amostra é degustação, não substitui o relatório. Não deixe remontar o relatório via consultas recortadas. A partir da 2ª amostra, fique mais sucinto e reforce o cadastro. Quando o sistema indicar que o limite de amostras foi atingido, PARE de entregar novas amostras detalhadas e peça os dados do formulário com cordialidade.

## GATE DE LIBERAÇÃO = FORMULÁRIO COMPLETO
Para liberar o diagnóstico, colete de forma conversacional (um passo de cada vez, confirmando) TODAS as variáveis: LOCALIZAÇÃO (Estado, Município, Bairro); IMÓVEL/NEGÓCIO (Tipo: Academia tradicional | CrossFit/Box | Estúdio Pilates | Studio Funcional | Outro; Porte: PP 250-400 | P 400-800 | M 800-1500 | G 1500-2500 | GG 2500-5000 m²; Público: 18-29 | 25-40 | 30-50 | 40+; Gênero: Misto | Predom. feminino | Predom. masculino | Excl. feminino | Excl. masculino; Estacionamento obrigatório: sim/não); CONTATO (Nome; E-mail ou WhatsApp). Conduza leve, não interrogatório. Não libere enquanto localização + tipo + porte + público + gênero + contato não estiverem preenchidos. Nunca invente valores; pergunte."""


# Persona do "Responsável Técnico" — especialista de EQUIPAMENTOS (RAG segmentado:
# só o data store de catálogos de equipamentos via consultar_catalogos_equipamentos).
_PERSONA_TECNICO = """## PAPEL
Você é o Responsável Técnico do GymSite Intelligence — especialista em EQUIPAMENTOS de academia. Ajuda a montar a sala: que máquinas comprar, especificações, quantidade por m², layout e fornecedores.

## COMO AGIR (responda no nível da pergunta — pergunte SÓ o que muda a resposta)
Pergunte APENAS a informação que altera a ESTRUTURA da resposta àquela pergunta. Se um dado não muda o que você vai responder, NÃO peça. Nunca despeje a lista cheia de qualificadores; pergunta fechada → resposta fechada.
- QUANTIDADE de UM equipamento (ex.: "quantas esteiras pra minha área de cardio") → peça só o pico de alunos simultâneos no horário de maior movimento (ou a área em m² dedicada ao cardio) e dimensione. NÃO pergunte tipo de academia nem foco do público — não mudam a conta de esteiras.
- MIX COMPLETO ("monte minha academia", "o que comprar pra 300 m²") → aí sim pergunte porte (m²), tipo (musculação / crossfit / funcional / estúdio) e foco do público, porque mudam o mix inteiro.
- SPEC/modelo de uma máquina → vá direto ao catálogo (consultar_catalogos_equipamentos), sem perguntar antes.
Se o usuário já deu o dado necessário, não repergunte — responda na hora. Conduza pra recomendação, não pra um menu de capacidades.

## DIMENSIONAMENTO (use a TOOL, nunca calcule de cabeça)
- "quantas esteiras / aparelhos de cardio" a partir do PICO de alunos → chame `dimensionar_cardio_por_pico` (devolve esteira/elíptico/bike/escada, modelo tolera-fila).
- "quantas estações/máquinas de musculação" → chame `dimensionar_musculacao`.
- "quantas máquinas cabem em X m²" (ex.: "180 m² de cardio") → chame `calcular_equipamentos_por_area`; o footprint vem do catálogo (chame `consultar_catalogos_equipamentos` antes p/ as dimensões e passe comprimento_cm+largura_cm).
Reporte o número com as premissas que a tool devolve (são de PLANEJAMENTO). NUNCA chute "30-40 esteiras" de cabeça.

## REGRA DE OURO (FONTE)
Recomende SEMPRE com base em consultar_catalogos_equipamentos e CITE o fornecedor/catálogo (ex.: Matrix, Life Fitness, Total Health). Ao citar uma fonte, inclua-a em um JSON `{{"citacoes": [...]}}` no final da resposta, com os campos `valor`, `base`, `fonte` e `janela`. NUNCA invente specs, modelos ou preços. Catálogo sem valor → "sob consulta". Sem dado no catálogo → diga com transparência e ofereça encaminhar ao time.

## ESCOPO
Só equipamentos/montagem (máquinas, cardio, peso livre, funcional, layout, quantidade, fornecedores). Viabilidade/concorrência/demografia/financeiro/regulatório → diga que é com os outros especialistas e ofereça redirecionar.

## TOM / FASE 0
Técnico mas acessível, frases curtas. Sem preço de plano. Colete contato só se o visitante quiser receber uma proposta de equipamentos."""


# Persona do agente Regulatório — registro/licença/CREF (RAG: consultar_base_conhecimento,
# que carrega os docs regulatórios CONFEF/Lei 9.696/anuidades CREF ingeridos no market-docs).
_PERSONA_REGULATORIO = """## PAPEL
Você é o agente Regulatório do GymSite Intelligence. Ajuda quem quer abrir academia a entender o que precisa LEGALMENTE: registro no CREF (pessoa jurídica), responsável técnico (profissional de educação física), Lei 9.696/1998, anuidades do CREF da região e licenças/notas técnicas de funcionamento.

## LOOKUPS DETERMINÍSTICOS (obrigatório)
- CREF por UF/estado → SEMPRE `resolver_cref_por_uf` (não chute; não dependa só do RAG).
- Anuidade PJ → SEMPRE `consultar_anuidade_pj_cref` (valor-base Res. CONFEF 596/2025 + nota regional). Valor FINAL = confirmar no CREF regional.
- Prosa legal (Lei 9.696, RT, processo, licenças) → `consultar_base_conhecimento`.

## REGRA DE OURO (FONTE)
Carimbo obrigatório `valor · base · fonte · janela` em toda exigência/prazo/valor. Fonte = lei nº + ano + artigo (ou resolução CONFEF/CREF) — NUNCA "Vertex AI Search" nem nome de arquivo. Exigência municipal só com município+UF. Ao final emita JSON `{{"citacoes": [{{"valor": "...", "base": "...", "fonte": "...", "janela": "..."}}]}}` só com os 4 campos. Sem carimbo completo → não cite; oriente CREF/prefeitura local.

## ESCOPO
Só regulatório de abertura (registro PJ no CREF, responsável técnico, Lei 9.696, anuidades CREF, licenças de funcionamento, zoneamento quando houver). Viabilidade/concorrência/equipamentos/financeiro → diga que é com os outros especialistas e ofereça redirecionar.

## TOM
Claro e objetivo, sem juridiquês. Cite a fonte. Lembre que a orientação não substitui consulta ao CREF/contador."""


_PERSONA_ARQUITETO = """## PAPEL
Você é o Arquiteto do GymSite Intelligence — projeta o ESPAÇO da academia: zonas (musculação, cardio, funcional, alongamento), fluxos, recepção/vestiários/sanitários, acessibilidade, pisos e as etapas do projeto arquitetônico.

## REGRA DE OURO (FONTE)
Chame SEMPRE consultar_engenharia_obra ANTES de afirmar regra de projeto, norma, área mínima ou exigência de acessibilidade. Carimbo `valor · base · fonte · janela` (ex.: NBR 9050 / NBR 13532 / COE municipal + município+UF). Sanitários via calcular_sanitarios_por_lotacao = estimativa NÃO-oficial. JSON final `{{"citacoes": [...]}}` só com 4 campos. Sem carimbo → não cite. NUNCA invente número ou norma.

## ESCOPO
Projeto/arquitetura/ambientes/acessibilidade. QUE equipamento e quantos cabem → Responsável Técnico; estrutura/instalações/licenças de obra → Engenheiro de Obra; regras do CREF → Regulatório. Deixe claro que o projeto deve ser assinado por arquiteto (RRT) e aprovado pela prefeitura.

## TOM
Técnico e didático, frases curtas."""


_PERSONA_ENGENHEIRO = """## PAPEL
Você é o Engenheiro de Obra do GymSite Intelligence — diz se a obra VIABILIZA a academia: estrutura (carga de laje), instalações (elétrica, hidráulica, climatização, acústica), prevenção de incêndio e licenciamento da obra. Distingue sempre RETROFIT de imóvel existente vs. CONSTRUÇÃO DO ZERO.

## COMO AGIR
Primeiro descubra o CENÁRIO (retrofit ou obra nova) — muda tudo. Depois responda com o checklist do cenário certo.

## REGRA DE OURO (FONTE)
Chame SEMPRE consultar_engenharia_obra ANTES de afirmar norma, carga estrutural, exigência de instalação ou licença. Carimbo `valor · base · fonte · janela` (NBR 6120/16280/5410/…, IT bombeiros com UF). JSON final `{{"citacoes": [...]}}` só com 4 campos. Toda obra/laudo exige ART (CREA). Em retrofit, recomende SEMPRE laudo estrutural. Sem carimbo → não cite. NUNCA invente valor estrutural, norma ou prazo.

## ESCOPO
Obra/estrutura/instalações/licenças. Projeto do espaço → Arquiteto; QUE equipamento → Responsável Técnico; CREF → Regulatório.

## TOM
Técnico, frases curtas."""


# Registry dos agentes do site (RAG SEGMENTADO por agente). Cada agente = persona +
# whitelist de tools — e cada tool aponta pro SEU data store (mercado/D2 vs equip).
# Generaliza o modo_site: conversar(modo_site=True, agente="responsavel_tecnico").
_AGENTES_SITE: dict[str, dict] = {
    "degustacao": {  # captação/mercado (default) — dados reais + D2/regulatório
        "persona": _SITE_PERSONA,
        "tools": _SITE_TOOLS_WHITELIST,
        "amostra_tools": _SITE_AMOSTRA_TOOLS,
    },
    "responsavel_tecnico": {  # equipamentos — só o RAG de catálogos (gymsite-equip-app)
        "persona": _PERSONA_TECNICO,
        "tools": frozenset({"consultar_catalogos_equipamentos", "consultar_base_conhecimento",
                            "dimensionar_cardio_por_pico", "dimensionar_musculacao",
                            "calcular_equipamentos_por_area"}),
        "amostra_tools": frozenset(),  # RAG é barato → sem antifatiamento de amostra
    },
    "regulatorio": {  # registro/licença/CREF — lookups CWA + RAG prosa
        "persona": _PERSONA_REGULATORIO,
        "tools": frozenset({
            "resolver_cref_por_uf",
            "consultar_anuidade_pj_cref",
            "consultar_base_conhecimento",
        }),
        "amostra_tools": frozenset(),
    },
    "arquiteto": {  # projeto do espaço — base de engenharia/obra + sanitários por lotação
        "persona": _PERSONA_ARQUITETO,
        "tools": frozenset({"consultar_engenharia_obra", "calcular_sanitarios_por_lotacao"}),
        "amostra_tools": frozenset(),
    },
    "engenheiro_obra": {  # viabilidade construtiva — base de engenharia/obra
        "persona": _PERSONA_ENGENHEIRO,
        "tools": frozenset({"consultar_engenharia_obra"}),
        "amostra_tools": frozenset(),
    },
}
_AGENTE_DEFAULT = "degustacao"


def _agente_cfg(agente: str | None) -> dict:
    return _AGENTES_SITE.get((agente or _AGENTE_DEFAULT), _AGENTES_SITE[_AGENTE_DEFAULT])


def _tool_decls_agente(agente: str | None) -> types.Tool:
    """Tool declarations expostas ao Gemini p/ o agente (só o RAG/tools do escopo dele)."""
    wl = _agente_cfg(agente)["tools"]
    return types.Tool(function_declarations=[
        fd for fd in (_TOOL_DECLARATIONS.function_declarations or []) if fd.name in wl
    ])


def _build_system_prompt_site(projeto: ProjectState, agente: str = _AGENTE_DEFAULT) -> str:
    cfg = _agente_cfg(agente)
    loc = projeto.localizacao or {}
    mn = projeto.modelo_negocio or {}
    amostras = int((mn.get("_site") or {}).get("amostras", 0))

    ctx = ""
    if loc.get("cidade"):
        ctx += f"\n- Localização informada: {loc.get('bairro', '')}, {loc.get('cidade', '')}/{loc.get('uf', '')}"
    if mn.get("tipo"):
        ctx += f"\n- Tipo de negócio: {mn['tipo']}"
    if cfg["amostra_tools"]:
        ctx += f"\n- Amostras detalhadas já entregues nesta conversa: {amostras} (limite {_SITE_MAX_AMOSTRAS})."

    return (
        cfg["persona"]
        + "\n\n## CONTEXTO DA CONVERSA" + (ctx or " (início)")
        + f"\n\nData de hoje: {datetime.now(timezone.utc).strftime('%d/%m/%Y')}"
        + "\n\n## FORMATO\nAo final, emita SOMENTE um JSON {\"sugestoes\": [\"...\"]} (1-3 itens) com próximos passos NA VOZ DO USUÁRIO — frases curtas que o visitante clicaria para responder/seguir (ex.: \"Informar o pico de alunos\", \"Ver concorrentes no bairro\"). NUNCA são perguntas suas. NÃO escreva \"Sugestões\" nem o JSON no corpo visível — o sistema extrai e some."
    )

# ─── Execução das ferramentas ─────────────────────────────────────────────────

async def _executar_ferramenta(
    nome: str,
    args: dict[str, Any],
    projeto: ProjectState,
    usuario_id: str,
    modo_site: bool = False,
    agente: str = _AGENTE_DEFAULT,
) -> tuple[dict[str, Any], str]:
    """
    Executa a tool pelo nome, wrappando os agentes ADK existentes.
    Retorna (resultado_dict, resumo_curto).

    modo_site=True (N3 landing): aplica a whitelist do `agente` (RAG segmentado) e o
    antifatiamento hard ANTES de rodar — o Gemini não deve enxergar as tools fora do
    escopo (já filtradas em _tool_decls_agente), mas o guard aqui é a barreira real.
    """
    t0 = time.perf_counter()

    # ── Guard do modo site (hard, por agente — independe do prompt) ──
    if modo_site:
        _cfg = _agente_cfg(agente)
        if nome not in _cfg["tools"]:
            return ({"bloqueado": True, "mensagem": _SITE_GATE_MSG,
                     "_meta": {"ferramenta": nome, "tier": "bloqueada", "elapsed_s": 0.0}}, "gate")
        if nome in _cfg["amostra_tools"]:
            _mn = dict((await carregar_projeto(projeto.id, projeto.user_id)).modelo_negocio or {})
            _site = dict(_mn.get("_site") or {})
            _usadas = int(_site.get("amostras", 0))
            if _usadas >= _SITE_MAX_AMOSTRAS:
                return ({"bloqueado": True, "mensagem": _SITE_GATE_MSG,
                         "_meta": {"ferramenta": nome, "tier": "limite_amostras", "elapsed_s": 0.0}}, "gate")
            _site["amostras"] = _usadas + 1
            _mn["_site"] = _site
            await atualizar_campo_projeto(projeto.id, "modelo_negocio", _mn, projeto.user_id)

    try:
        if nome == "pesquisar_contexto_mercado":
            resultado = await _tool_mercado(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "mercado", projeto.user_id)
            resumo = _resumo_mercado(resultado)

        elif nome == "buscar_pontos_comerciais":
            resultado = await _tool_pontos_comerciais(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "pontos_comerciais", projeto.user_id)
            resumo = _resumo_pontos(resultado)

        elif nome == "analisar_demografia":
            resultado = await _tool_demografia(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "demografia", projeto.user_id)
            resumo = _resumo_demografia(resultado)

        elif nome == "pesquisar_concorrentes":
            resultado = await _tool_concorrentes(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "concorrentes", projeto.user_id)
            # Merge no objeto concorrencia (NÃO sobrescrever): preserva o cache de
            # concorrentes brutos que reviews/oferta vão ler depois.
            conc = dict((await carregar_projeto(projeto.id, projeto.user_id)).concorrencia or {})
            conc.update({
                "total": resultado.get("total_concorrentes", 0),
                "nivel_saturacao": resultado.get("nivel_saturacao"),
                "snapshot_ts": datetime.now(timezone.utc).isoformat(),
                "_concorrentes_brutos_cache": resultado,
            })
            await atualizar_campo_projeto(projeto.id, "concorrencia", conc, projeto.user_id)
            resumo = _resumo_concorrentes(resultado)

        elif nome == "analisar_reviews_e_dores":
            resultado = await _tool_reviews(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "reviews", projeto.user_id)
            resumo = _resumo_reviews(resultado)

        elif nome == "mapear_oferta_e_servicos":
            resultado = await _tool_oferta(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "oferta_concorrentes", projeto.user_id)
            resumo = _resumo_oferta(resultado)

        elif nome == "estimar_investimento":
            resultado = await _tool_financeiro(args, projeto)
            await marcar_pesquisa_realizada(projeto.id, "investimento", projeto.user_id)
            await atualizar_campo_projeto(projeto.id, "financeiro", {
                "modelo_recomendado": resultado.get("recomendacao_modelo"),
                "score_viabilidade": resultado.get("score_viabilidade"),
                "snapshot_ts": datetime.now(timezone.utc).isoformat(),
            }, projeto.user_id)
            resumo = _resumo_financeiro(resultado)

        elif nome == "gerar_relatorio_formal":
            resultado = await _tool_relatorio(args, projeto, usuario_id)
            resumo = "Relatório em geração"

        elif nome == "consultar_base_conhecimento":
            # Conhecimento auxiliar (RAG) — NÃO marca pesquisas_realizadas (não é uma
            # das 7 pesquisas de viabilidade; preserva o gate pode_gerar_relatorio).
            resultado = await _tool_base_conhecimento(args, projeto, modo_site)
            resumo = _resumo_base_conhecimento(resultado)

        elif nome == "consultar_catalogos_equipamentos":
            resultado = await _tool_catalogos_equipamentos(args, projeto)
            resumo = _resumo_base_conhecimento(resultado)

        elif nome == "dimensionar_cardio_por_pico":
            from agents_site.tools import dimensionar_cardio_por_pico
            resultado = dimensionar_cardio_por_pico(int(args.get("pico_simultaneo") or 0))
            resumo = f"esteiras {resultado.get('esteiras', {}).get('min')}-{resultado.get('esteiras', {}).get('max')}"

        elif nome == "dimensionar_musculacao":
            from agents_site.tools import dimensionar_musculacao
            resultado = dimensionar_musculacao(int(args.get("pico_simultaneo") or 0))
            resumo = f"{resultado.get('estacoes')} estações"

        elif nome == "calcular_equipamentos_por_area":
            from agents_site.tools import calcular_equipamentos_por_area
            resultado = calcular_equipamentos_por_area(
                float(args.get("area_disponivel_m2") or 0),
                footprint_m2=float(args.get("footprint_m2") or 0),
                comprimento_cm=float(args.get("comprimento_cm") or 0),
                largura_cm=float(args.get("largura_cm") or 0),
            )
            resumo = f"{resultado.get('n_maquinas')} máquinas" if "n_maquinas" in resultado else "erro"

        elif nome == "consultar_engenharia_obra":
            from agents_site.tools import consultar_engenharia_obra
            resultado = consultar_engenharia_obra(str(args.get("pergunta") or ""))
            resumo = "base de engenharia/obra consultada"

        elif nome == "calcular_sanitarios_por_lotacao":
            from agents_site.tools import calcular_sanitarios_por_lotacao
            resultado = calcular_sanitarios_por_lotacao(int(args.get("lotacao") or 0))
            resumo = f"sanitários p/ lotação {args.get('lotacao')}"

        elif nome == "resolver_cref_por_uf":
            from tools.regulatorio_lookup import resolver_cref_por_uf
            resultado = resolver_cref_por_uf(
                str(args.get("uf") or ""),
                data_ref=args.get("data_ref") or None,
            )
            resumo = resultado.get("cref_registro") or "CREF não resolvido"

        elif nome == "consultar_anuidade_pj_cref":
            from tools.regulatorio_lookup import consultar_anuidade_pj_cref
            ex = args.get("exercicio")
            resultado = consultar_anuidade_pj_cref(
                uf=args.get("uf") or None,
                cref=args.get("cref") or None,
                exercicio=int(ex) if ex is not None else None,
                data_ref=args.get("data_ref") or None,
            )
            if resultado.get("valor_base_centavos") is not None:
                resumo = f"R$ {resultado.get('valor_base_reais')} ({resultado.get('cref_registro')})"
            else:
                resumo = resultado.get("status") or "anuidade"

        else:
            resultado = {"erro": f"Ferramenta desconhecida: {nome}"}
            resumo = "erro"

    except Exception as e:
        logger.exception("[consultor_engine] tool %s falhou", nome)
        resultado = {"erro": f"{type(e).__name__}: {e}"}
        resumo = "erro"

    elapsed = round(time.perf_counter() - t0, 2)
    resultado = {**resultado, "_meta": {"elapsed_s": elapsed, "ferramenta": nome}}
    return resultado, resumo

# ─── Wrappers das tools (chamam as macros ADK existentes) ────────────────────

async def _tool_mercado(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A0 ContextBuilder — carrega market_bundle + CNPJ."""
    from tools.market_bundle import carregar_market_bundle
    from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
    from tools.local_market_facts import fatos_competicao_local

    cidade = args["cidade"]
    bairro = args["bairro"]
    uf = args["uf"]

    bundle, cnpj_data, local = await asyncio.gather(
        asyncio.to_thread(carregar_market_bundle, cidade, bairro, uf),
        asyncio.to_thread(dados_parque_cnpj_para_a0, cidade, uf, 90, bairro),
        asyncio.to_thread(fatos_competicao_local, cidade, bairro, uf),
    )

    return {
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
        "bundle": bundle,
        "parque_cnpj": cnpj_data,
        "competicao_local": local,
        "fonte": "market_bundle + CNPJ/RFB + OSM",
        "data_coleta": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


async def _tool_pontos_comerciais(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A1 GeoScout — macro de pontos comerciais.

    A macro é `analisar_pontos_comerciais_completo(tool_context, bairro, cidade, uf)`
    e lê `tool_context.state.input_params` (area_m2_min/max, bairro) p/ a cascata de
    listings + MRLR. Passamos um shim de state com esses params (mesma forma que A3a).
    """
    from tools.anchoring_tools import analisar_pontos_comerciais_completo

    bairro = args["bairro"]
    cidade = args["cidade"]
    uf = args["uf"]

    class _StateShim:
        def __init__(self, state: dict):
            self.state = state

    shim = _StateShim({
        "bairro": bairro, "cidade": cidade,
        "input_params": {
            "bairro": bairro,
            "area_m2_min": int(args.get("area_min_m2") or 500),
            "area_m2_max": int(args.get("area_max_m2") or 2000),
        },
    })

    resultado = await asyncio.to_thread(
        analisar_pontos_comerciais_completo, shim, bairro, cidade, uf
    )
    return resultado if isinstance(resultado, dict) else {"candidatos": [], "total_candidatos": 0}


async def _tool_demografia(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A2 DemoAnalyst — IBGE Censo 2022."""
    from tools.ibge_tools import analise_demografica_completa

    resultado = await asyncio.to_thread(
        analise_demografica_completa,
        args["cidade"],
        args["uf"],
        "18-45",
        args.get("bairro"),
    )
    return resultado if isinstance(resultado, dict) else {"erro": "IBGE indisponível"}


async def _tool_concorrentes(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A3a CompetitorSearch — busca + enrichment de concorrentes."""
    from tools.competitor_tools import analisar_concorrentes_a3a_completo

    class _StateShim:
        def __init__(self, state: dict):
            self.state = state

    state = {
        "bairro": args["bairro"],
        "cidade": args["cidade"],
        "input_params": {
            "tipo_negocio": args.get("tipo_negocio", "academia"),
            "raio_metros": args.get("raio_metros", 3000),
        },
    }
    resultado = await analisar_concorrentes_a3a_completo(
        _StateShim(state), args["bairro"], args["cidade"]
    )
    # O cache (_concorrentes_brutos_cache) é persistido pelo chamador
    # (_executar_ferramenta), com merge no objeto `concorrencia`, para
    # reviews/oferta lerem depois. Aqui só devolvemos o resultado.
    return resultado if isinstance(resultado, dict) else {"concorrentes_brutos": []}


async def _tool_reviews(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A3b CompetitorAnalysis — lê concorrentes_brutos do cache do projeto."""
    from tools.competitor_tools import analisar_concorrentes_completo

    # Recupera concorrentes já buscados (evita rebuscar)
    proj_atual = await carregar_projeto(projeto.id, projeto.user_id)
    concorrentes_brutos = (
        (proj_atual.concorrencia or {}).get("_concorrentes_brutos_cache") or {}
    )

    class _StateShim:
        def __init__(self, state: dict):
            self.state = state

    state = {"concorrentes_brutos": concorrentes_brutos}
    resultado = analisar_concorrentes_completo(_StateShim(state))
    return resultado if isinstance(resultado, dict) else {"inteligencia_competitiva": {}}


async def _tool_oferta(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A3c CompetitorMapper — scrape de site/Instagram dos concorrentes."""
    from tools.offer_mapper_tool import mapear_oferta_competidores_completo

    proj_atual = await carregar_projeto(projeto.id, projeto.user_id)
    concorrentes_brutos = (
        (proj_atual.concorrencia or {}).get("_concorrentes_brutos_cache") or {}
    )
    top_n = args.get("top_n", 5)

    class _StateShim:
        def __init__(self, state: dict):
            self.state = state

    state = {"concorrentes_brutos": concorrentes_brutos, "top_n_oferta": top_n}
    resultado = mapear_oferta_competidores_completo(_StateShim(state))
    return resultado if isinstance(resultado, dict) else {"oferta_concorrentes": {}}


async def _tool_financeiro(args: dict, projeto: ProjectState) -> dict:
    """Wrappa A4 FinancialEstimator — 3 cenários CAPEX/OPEX/payback."""
    from tools.financial_tools import analise_financeira_a4_completo

    cidade = args["cidade"]
    bairro = args["bairro"]
    uf = args["uf"]
    area_m2 = float(args.get("area_m2") or 1150.0)
    tipo = args.get("tipo_negocio", "academia")
    tamanho = args.get("tamanho_preset") or _inferir_tamanho(area_m2)
    genero = args.get("genero_alvo", "misto")

    resultado = await analise_financeira_a4_completo(
        bairro, cidade, uf, area_m2,
        area_m2_min=int(area_m2 * 0.8),
        area_m2_max=int(area_m2 * 1.2),
        tipo_negocio=tipo,
        tamanho_preset=tamanho,
    )
    return resultado if isinstance(resultado, dict) else {"erro": "Financeiro indisponível"}


async def _tool_relatorio(args: dict, projeto: ProjectState, usuario_id: str) -> dict:
    """
    Dispara o pipeline A0→A9 — MESMO fluxo do endpoint POST /api/relatorios:
    create_relatorio_stub() (garante FK) + enqueue {"type":"pipeline",...} no Redis.
    Retorna o relatorio_id real imediatamente; o worker do api.py roda async.
    """
    # Imports LAZY: api.py importa este módulo ao montar o router → import no topo
    # seria circular. No call-time o api.py já está totalmente carregado.
    from api import NovoRelatorioInput, create_relatorio_stub
    from tools.redis_queue import RedisQueue

    loc = projeto.localizacao or {}
    mn = projeto.modelo_negocio or {}
    area = int(mn.get("area_m2") or 1250)

    payload = NovoRelatorioInput(
        cidade=loc.get("cidade", ""),
        uf=loc.get("uf"),
        bairro=loc.get("bairro", ""),
        area_m2_min=max(50, int(area * 0.8)),
        area_m2_max=min(10000, int(area * 1.2)),
        tamanho_preset=mn.get("tamanho_preset", "m"),
        genero_alvo=mn.get("genero_alvo", "misto"),
        tipo_negocio=mn.get("tipo", "academia"),
    )

    # Stub cria a linha em `relatorios` (status=queued) e devolve o ID real.
    relatorio_id, _created = await asyncio.to_thread(
        create_relatorio_stub, payload, org_id=None, user_id=usuario_id
    )

    # RedisQueue.enqueue só faz lpush no QUEUE_KEY que o worker singleton do api.py
    # consome → instância efêmera (worker_func no-op, nunca iniciada) basta pra enfileirar.
    fila = RedisQueue(worker_func=lambda _job: None)
    await fila.enqueue({
        "type": "pipeline",
        "relatorio_id": relatorio_id,
        "payload": payload.model_dump(),
    })

    await atualizar_campo_projeto(projeto.id, "relatorio_id", relatorio_id, projeto.user_id)
    await atualizar_campo_projeto(projeto.id, "status", "CONSOLIDANDO", projeto.user_id)

    return {
        "relatorio_id": relatorio_id,
        "status": "CONSOLIDANDO",
        "mensagem": (
            "Vou consolidar tudo em um Relatório Formal de Viabilidade. "
            "O processo leva de 3 a 5 minutos. Assim que estiver pronto, "
            "um link aparecerá aqui."
        ),
    }


async def disparar_relatorio_formal(projeto_id: str, usuario_id: str) -> dict[str, Any]:
    """Dispara o pipeline A0→A9 de forma DETERMINÍSTICA (não passa pelo LLM).

    Ponto de entrada do endpoint POST /projetos/{id}/relatorio — o disparo é uma
    decisão de negócio do backend (P-005), nunca uma tool que o Gemini pode ou não
    escolher chamar. Carrega o projeto, enfileira o pipeline e persiste a mensagem
    no histórico para auditoria. Retorna {relatorio_id, status, mensagem}.
    """
    projeto = await carregar_projeto(projeto_id, usuario_id)
    resultado = await _tool_relatorio({"projeto_id": projeto_id}, projeto, usuario_id)
    await salvar_mensagem(
        projeto_id=projeto_id,
        role="assistant",
        content=resultado.get("mensagem", ""),
        tool_calls=[{
            "ferramenta": "gerar_relatorio_formal",
            "status": "sucesso",
            "resumo": "Relatório em geração",
        }],
    )
    return resultado


async def _tool_base_conhecimento(args: dict, projeto: ProjectState, modo_site: bool = False) -> dict:
    """Base de conhecimento qualitativa (Vertex AI Search). Retorna trechos + citações;
    o próprio Gemini do Consultor sintetiza. NÃO produz número.

    Consultor LOGADO: market-docs (fato de mercado neutro) + consultor-docs (BI/estratégia
    interna). Degustação (modo_site): SÓ market-docs — barreira anti-vazamento, a base interna
    nunca chega ao visitante público."""
    from tools.discovery_engine_tools import buscar_conhecimento, buscar_conhecimento_consultor

    pergunta = (args.get("pergunta") or "").strip()
    resultado = await asyncio.to_thread(buscar_conhecimento, pergunta)
    if not isinstance(resultado, dict):
        resultado = {"resultados": [], "n_docs": 0}

    if not modo_site:
        interno = await asyncio.to_thread(buscar_conhecimento_consultor, pergunta)
        if isinstance(interno, dict) and interno.get("resultados"):
            resultado["resultados"] = (resultado.get("resultados") or []) + interno["resultados"]
            resultado["n_docs"] = len(resultado.get("resultados") or [])
    return resultado


async def _tool_catalogos_equipamentos(args: dict, projeto: ProjectState) -> dict:
    """Catálogos de equipamento (data store/engine separado). Trechos + citações."""
    from tools.discovery_engine_tools import buscar_catalogos_equipamentos

    pergunta = (args.get("pergunta") or "").strip()
    resultado = await asyncio.to_thread(buscar_catalogos_equipamentos, pergunta)
    return resultado if isinstance(resultado, dict) else {"resultados": [], "n_docs": 0}

# ─── Helpers de resumo (texto curto para as pills do frontend) ────────────────

def _resumo_mercado(r: dict) -> str:
    parque = r.get("parque_cnpj", {})
    total = parque.get("academias_ativas_cidade_cnpj") or parque.get("parque_ativo_total")
    if total:
        return f"{total} academias ativas (CNPJ)"
    return "contexto carregado"

def _resumo_pontos(r: dict) -> str:
    total = r.get("total_candidatos", 0)
    return f"{total} candidatos" if total else "nenhum candidato"

def _resumo_demografia(r: dict) -> str:
    score = r.get("score_demografico")
    pub = r.get("publico_potencial_fitness")
    if score and pub:
        return f"score {score:.1f} · {pub:,} potenciais".replace(",", ".")
    return "IBGE carregado"

def _resumo_concorrentes(r: dict) -> str:
    brutos = r.get("concorrentes_brutos") or []
    total = len(brutos) if isinstance(brutos, list) else r.get("total_concorrentes", 0)
    sat = r.get("nivel_saturacao", "")
    return f"{total} encontrados · {sat}" if sat else f"{total} encontrados"

def _resumo_reviews(r: dict) -> str:
    ic = r.get("inteligencia_competitiva") or r
    dores = ic.get("dores_dominantes") or []
    if dores:
        top = dores[0].get("dor", "")
        return f"dor principal: {top}" if top else f"{len(dores)} dores mapeadas"
    return "reviews analisados"

def _resumo_oferta(r: dict) -> str:
    total = r.get("total_processados", 0)
    suc = r.get("sucessos", 0)
    return f"{suc}/{total} mapeados"

def _resumo_financeiro(r: dict) -> str:
    modelo = r.get("recomendacao_modelo", "")
    score = r.get("score_viabilidade")
    if score is not None:
        return f"score {score:.1f} · {modelo}"
    return modelo or "estimativa gerada"

def _resumo_base_conhecimento(r: dict) -> str:
    n = r.get("n_docs", 0)
    if r.get("erro"):
        return "base indisponível"
    return f"{n} doc(s)" if n else "nada na base"

def _inferir_tamanho(area_m2: float) -> str:
    if area_m2 < 500:
        return "p"
    if area_m2 < 1500:
        return "m"
    if area_m2 < 3000:
        return "g"
    return "gg"

# ─── Atualização de projeto a partir da conversa ──────────────────────────────

async def _atualizar_projeto_de_resposta(
    projeto: ProjectState,
    tool_name: str,
    args: dict,
) -> None:
    """
    Atualiza campos do UserProject com base nos argumentos da tool chamada.
    Permite que dados de localização/modelo sejam persistidos mesmo antes
    da tool retornar (para o frontend mostrar imediatamente).
    """
    updates: dict[str, Any] = {}

    if "cidade" in args:
        loc = dict(projeto.localizacao or {})
        loc.update({k: args[k] for k in ("cidade", "bairro", "uf") if k in args})
        updates["localizacao"] = loc

    if "area_m2" in args or "tipo_negocio" in args or "tamanho_preset" in args:
        mn = dict(projeto.modelo_negocio or {})
        # args usa "tipo_negocio"; o projeto guarda como "tipo". Demais chaves 1:1.
        _MAPA = {"tipo_negocio": "tipo"}
        for k in ("tipo_negocio", "tamanho_preset", "genero_alvo", "area_m2"):
            if k in args:
                mn[_MAPA.get(k, k)] = args[k]
        updates["modelo_negocio"] = mn

    for campo, valor in updates.items():
        await atualizar_campo_projeto(projeto.id, campo, valor, projeto.user_id)

# ─── Extração de sugestões da resposta do LLM ────────────────────────────────

def _extrair_sugestoes(texto: str) -> tuple[str, list[str]]:
    """
    O LLM às vezes inclui sugestões em formato JSON no final da resposta:
    {"sugestoes": ["...", "..."]}
    Extrai e remove do texto visível.
    """
    import re
    sugestoes: list[str] = []
    if not texto:
        return texto, sugestoes

    def _norm(parsed) -> list[str]:
        """Aceita {'sugestoes': [...]}, [str,...] ou [{'proximo_passo'|'sugestao'|...}]."""
        if isinstance(parsed, dict):
            arr = parsed.get("sugestoes")
            parsed = arr if isinstance(arr, list) else [parsed]
        out: list[str] = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict):
                    for k in ("proximo_passo", "sugestao", "texto", "passo", "titulo", "value"):
                        v = item.get(k)
                        if isinstance(v, str):
                            out.append(v)
                            break
        return [s.strip() for s in out if isinstance(s, str) and s.strip()]

    # 1) Bloco cercado no fim: ```json [...] ``` ou ``` {...} ```
    m = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```\s*$', texto, re.DOTALL)
    # 2) JSON cru no fim: {"sugestoes":...} ou array de objetos [{...}]
    if not m:
        m = re.search(r'(\{\s*"sugestoes".*\}|\[\s*\{.*\}\s*\])\s*$', texto, re.DOTALL)
    if m:
        try:
            sugestoes = _norm(json.loads(m.group(1)))
            texto = texto[:m.start()].rstrip()
        except (json.JSONDecodeError, TypeError):
            sugestoes = []
    return texto, sugestoes

# ─── Extração de citações da resposta do LLM ─────────────────────────────────

def _extrair_citacoes(texto: str) -> tuple[str, list[dict]]:
    """
    Extrai um bloco JSON de citações do final da resposta do LLM.
    {"citacoes": [{"valor": "...", "base": "...", "fonte": "...", "janela": "..."}]}
    """
    import re
    citacoes: list[dict] = []
    if not texto:
        return texto, citacoes

    # Regex para encontrar um bloco JSON com a chave "citacoes" no final do texto
    m = re.search(r'```(?:json)?\s*(\{.*"citacoes".*\})\s*```\s*$', texto, re.DOTALL)
    if not m:
        m = re.search(r'(\{\s*"citacoes".*\})\s*$', texto, re.DOTALL)
    
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict) and "citacoes" in parsed and isinstance(parsed["citacoes"], list):
                # Validação mínima para garantir que os itens são dicionários
                citacoes = [c for c in parsed["citacoes"] if isinstance(c, dict)]
                texto = texto[:m.start()].rstrip()
        except (json.JSONDecodeError, TypeError):
            citacoes = []
            
    return texto, citacoes

# ─── Cálculo de custo estimado ────────────────────────────────────────────────

_CUSTO_BRL_POR_TOOL: dict[str, float] = {
    "pesquisar_contexto_mercado": 0.25,
    "buscar_pontos_comerciais": 0.10,
    "analisar_demografia": 0.05,
    "pesquisar_concorrentes": 0.20,
    "analisar_reviews_e_dores": 0.30,
    "mapear_oferta_e_servicos": 0.20,
    "estimar_investimento": 0.15,
    "gerar_relatorio_formal": 3.50,
    "consultar_base_conhecimento": 0.05,
    "consultar_catalogos_equipamentos": 0.05,
    "dimensionar_cardio_por_pico": 0.0,
    "dimensionar_musculacao": 0.0,
    "calcular_equipamentos_por_area": 0.0,
    "resolver_cref_por_uf": 0.0,
    "consultar_anuidade_pj_cref": 0.0,
}

def _custo_tools(tools_executadas: list[str]) -> float:
    return round(sum(_CUSTO_BRL_POR_TOOL.get(t, 0.10) for t in tools_executadas), 2)

# ─── Função principal: conversar ──────────────────────────────────────────────

async def conversar(
    mensagem: str,
    usuario_id: str,
    projeto_id: str | None = None,
    modo_site: bool = False,
    agente: str = _AGENTE_DEFAULT,
) -> dict[str, Any]:
    """
    Processa uma mensagem do usuário e retorna a resposta do consultor.

    Parâmetros
    ----------
    mensagem   : texto enviado pelo usuário
    usuario_id : UUID do usuário autenticado (Supabase auth.uid)
    projeto_id : UUID do UserProject existente (None = criar novo)

    Retorno
    -------
    {
        projeto_id          : str,
        mensagem            : str,          # resposta conversacional
        status              : str,          # status do projeto
        acoes_executadas    : list[dict],   # ferramentas que rodaram
        sugestoes           : list[str],    # próximos passos sugeridos
        pode_gerar_relatorio: bool,
        dados_faltantes     : list[str],
        projeto             : dict,         # ProjetoStatus completo para o frontend
        citacoes            : list[dict],   # Citações estruturadas
    }
    """

    client = _client_gemini()  # factory canônica (lazy) — erro claro se sem credencial

    # 1. Carrega ou cria projeto
    if projeto_id:
        projeto = await carregar_projeto(projeto_id, usuario_id)
    else:
        projeto = await criar_projeto(usuario_id)
        projeto_id = projeto.id

    # 2. Carrega histórico de mensagens (últimas 20)
    historico = await carregar_historico(projeto_id, limite=20)

    # 3. Persiste mensagem do usuário
    await salvar_mensagem(
        projeto_id=projeto_id,
        role="user",
        content=mensagem,
    )

    # 4. Monta histórico no formato google-genai (types.Content), SEM a msg atual
    #    (ela vai no primeiro send_message).
    history_contents: list = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in historico
    ]

    # 5. Loop de function calling (SDK google-genai: client.chats)
    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt_site(projeto, agente) if modo_site else _build_system_prompt(projeto),
        tools=[_tool_decls_agente(agente) if modo_site else _TOOL_DECLARATIONS],
        temperature=0.3,
        max_output_tokens=2048,
    )

    acoes_executadas: list[dict] = []
    tools_executadas: list[str] = []
    resposta_final = ""
    sugestoes_finais: list[str] = []
    citacoes_finais: list[dict] = []

    chat = client.chats.create(model=_MODEL_ROUTER, config=config, history=history_contents)
    response = await asyncio.to_thread(chat.send_message, mensagem)

    def _partes(resp):
        """Itera as parts com segurança: candidates/content/parts podem vir None
        (resposta bloqueada por safety, MAX_TOKENS sem conteúdo, etc.) — evita
        crash do worker e deixa cair no fallback de fim de loop."""
        for c in (getattr(resp, "candidates", None) or []):
            content = getattr(c, "content", None)
            for p in (getattr(content, "parts", None) or []):
                yield p

    for _round in range(_MAX_TOOL_ROUNDS):
        # Verifica se há function calls
        fc_parts = [
            p for p in _partes(response)
            if hasattr(p, "function_call") and p.function_call
        ]

        if not fc_parts:
            # LLM retornou texto — fim do loop
            texto_bruto = "".join(
                p.text for p in _partes(response)
                if hasattr(p, "text") and p.text
            )
            texto_sem_sugestoes, sugestoes_finais = _extrair_sugestoes(texto_bruto)
            resposta_final, citacoes_finais = _extrair_citacoes(texto_sem_sugestoes)
            break

        # Executa todas as tool calls do turno (podem ser paralelas)
        tool_results: list = []
        tasks = [
            _executar_ferramenta(fc.function_call.name, dict(fc.function_call.args), projeto, usuario_id, modo_site, agente)
            for fc in fc_parts
        ]
        resultados = await asyncio.gather(*tasks)

        for fc, (resultado, resumo) in zip(fc_parts, resultados):
            nome = fc.function_call.name
            tools_executadas.append(nome)

            status = "erro" if "erro" in resultado else "sucesso"
            acoes_executadas.append({
                "ferramenta": nome,
                "status": status,
                "resumo": resumo,
            })

            # Atualiza campos de localização/modelo a partir dos args
            await _atualizar_projeto_de_resposta(projeto, nome, dict(fc.function_call.args))

            tool_results.append(
                types.Part.from_function_response(
                    name=nome,
                    response=_truncar_resultado(resultado),
                )
            )

        # Reenvia os function_responses para o LLM continuar (config já fixado no chat)
        response = await asyncio.to_thread(chat.send_message, tool_results)

    # 6. Fallback se loop estourou sem resposta
    if not resposta_final:
        resposta_final = (
            "Concluí as pesquisas solicitadas. "
            "Os resultados estão disponíveis no painel ao lado."
        )

    # 7. Recarrega projeto atualizado
    projeto = await carregar_projeto(projeto_id, usuario_id)
    custo_tools = _custo_tools(tools_executadas)

    # Atualiza custo acumulado
    custo_total = round((projeto.custo_brl_ate_agora or 0.0) + custo_tools + 0.02, 2)
    await atualizar_campo_projeto(projeto_id, "custo_brl_ate_agora", custo_total, usuario_id)

    # 8. Persiste resposta do assistente
    await salvar_mensagem(
        projeto_id=projeto_id,
        role="assistant",
        content=resposta_final,
        tool_calls=acoes_executadas if acoes_executadas else None,
        # TODO: Adicionar campo `citacoes` na tabela `project_messages`
        # citacoes=citacoes_finais,
    )

    # 9. Verifica se pode gerar relatório
    pesq = projeto.pesquisas_realizadas or {}
    pode_relatorio = (
        bool(projeto.localizacao.get("cidade"))
        and bool(projeto.localizacao.get("bairro"))
        and (pesq.get("concorrentes") or pesq.get("investimento"))
    )

    dados_faltantes = []
    if not projeto.localizacao.get("cidade"):
        dados_faltantes.append("cidade")
    if not projeto.localizacao.get("bairro"):
        dados_faltantes.append("bairro")
    if not projeto.modelo_negocio.get("area_m2"):
        dados_faltantes.append("área em m²")

    # 10. Sugestões padrão se LLM não sugeriu
    if not sugestoes_finais:
        sugestoes_finais = _sugestoes_padrao(projeto, pesq)

    return {
        "projeto_id": projeto_id,
        "mensagem": resposta_final,
        "status": projeto.status,
        "acoes_executadas": acoes_executadas,
        "sugestoes": sugestoes_finais[:3],
        "pode_gerar_relatorio": pode_relatorio,
        "dados_faltantes": dados_faltantes,
        "projeto": _serializar_projeto(projeto, custo_total),
        "citacoes": citacoes_finais,
    }

# ─── Sugestões padrão baseadas no estado do projeto ──────────────────────────

def _sugestoes_padrao(projeto: ProjectState, pesq: dict) -> list[str]:
    sugestoes = []
    if not pesq.get("concorrentes"):
        sugestoes.append("Pesquisar concorrentes na região")
    if pesq.get("concorrentes") and not pesq.get("reviews"):
        sugestoes.append("Analisar reviews e dores dos alunos")
    if not pesq.get("investimento") and projeto.localizacao.get("cidade"):
        sugestoes.append("Estimar investimento inicial")
    if not pesq.get("demografia"):
        sugestoes.append("Analisar o perfil demográfico do bairro")
    if not pesq.get("pontos_comerciais"):
        sugestoes.append("Buscar pontos comerciais disponíveis")
    if (
        pesq.get("concorrentes")
        and pesq.get("reviews")
        and pesq.get("investimento")
    ):
        sugestoes.append("Gerar Relatório Formal de Viabilidade")
    return sugestoes[:3]

# ─── Truncagem de resultado para evitar payload gigante no function_call ──────

def _truncar_resultado(resultado: dict, max_chars: int = 8000) -> dict:
    """
    Gemini tem limite de payload em function_response.
    Remove campos pesados (raw_texto, reviews completos) antes de reenviar.
    """
    leve = {k: v for k, v in resultado.items() if k not in ("_meta",)}

    # Remove campos grandes conhecidos
    for campo_pesado in (
        "briefing_completo_md", "enrichment_search_grounding_text",
        "raw_texto", "raw_meta_description",
    ):
        leve.pop(campo_pesado, None)
        for sub in leve.values():
            if isinstance(sub, dict):
                sub.pop(campo_pesado, None)

    serializado = json.dumps(leve, ensure_ascii=False, default=str)
    if len(serializado) <= max_chars:
        return leve

    # Trunca reviews individuais se ainda grande
    for k in ("concorrentes_brutos", "concorrentes_detalhados"):
        lista = leve.get(k)
        if isinstance(lista, list):
            leve[k] = lista[:3]  # top 3 apenas

    return leve

# ─── Serialização do projeto para o frontend ──────────────────────────────────

def _serializar_projeto(projeto: ProjectState, custo_total: float) -> dict:
    pesq = projeto.pesquisas_realizadas or {}
    return {
        "id": projeto.id,
        "status": projeto.status,
        "localizacao": projeto.localizacao or {},
        "modelo_negocio": projeto.modelo_negocio or {},
        "pesquisas_realizadas": {
            "mercado": bool(pesq.get("mercado")),
            "concorrentes": bool(pesq.get("concorrentes")),
            "reviews": bool(pesq.get("reviews")),
            "oferta_concorrentes": bool(pesq.get("oferta_concorrentes")),
            "demografia": bool(pesq.get("demografia")),
            "pontos_comerciais": bool(pesq.get("pontos_comerciais")),
            "investimento": bool(pesq.get("investimento")),
        },
        "total_concorrentes": (projeto.concorrencia or {}).get("total"),
        "total_reviews": None,
        "custo_brl_ate_agora": custo_total,
        "pode_gerar_relatorio": (
            bool((projeto.localizacao or {}).get("cidade"))
            and (pesq.get("concorrentes") or pesq.get("investimento"))
        ),
        "dados_faltantes": [],
        "relatorio_id": projeto.relatorio_id,
    }
