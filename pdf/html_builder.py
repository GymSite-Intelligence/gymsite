"""PDF de produção via HTML/CSS → WeasyPrint (migração do ReportLab).

Arquitetura-alvo (aceita): o LLM NÃO escreve o documento. O template HTML (Jinja2) cruza o
dado DETERMINÍSTICO do pipeline (A4/A9/demanda/demografia — já no RelatorioPdfModel) com os
insights estruturados. Garante conformidade financeira (número vem da variável, não da
memória do LLM) e mata a classe de bug do markdown-do-LLM (<b> literal, financeiro
divergente, seção não-narrada, gaps genéricos).

Relatório completo: sumário+scores, contexto de mercado, demografia+pirâmide idade×sexo,
concorrentes, viabilidade financeira (3 cenários), posicionamento ERRC, GAPs+ticket,
demanda futura datada, top candidatos, alertas. Layout/marca do mockup aprovado.
WeasyPrint precisa libs de sistema (pango/cairo) — no Dockerfile; em dev `gerar_html` roda.
"""
from __future__ import annotations

import os
from typing import Any

from pdf.models import RelatorioPdfModel

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

_TEMPLATE = """
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><style>
@page { size: A4; margin: 15mm 13mm;
  @bottom-right { content: "Página " counter(page) " de " counter(pages); font-family: Helvetica; font-size: 8pt; color:#64748B; }
  @bottom-left { content: "{{ rodape }}"; font-family: Helvetica; font-size: 8pt; font-style: italic; color:#64748B; } }
body { margin:0; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; color:#1E293B; font-size:9pt; line-height:1.45; }
.header { width:100%; border-collapse:collapse; border-bottom:2px solid #A3E635; padding-bottom:10px; margin-bottom:12px; }
.logo { font-weight:900; font-size:20pt; letter-spacing:-0.5px; color:#1B2A4A; line-height:1; }
.logo .a { color:#A3E635; }
.logo-sub { display:block; font-weight:500; font-size:7.5pt; color:#64748B; letter-spacing:2.5px; text-transform:uppercase; margin-top:3px; }
.doc-title { font-size:14pt; font-weight:bold; color:#0F172A; margin:0 0 3px; text-transform:uppercase; letter-spacing:0.5px; }
.doc-sub { font-size:9pt; color:#64748B; margin:0; }
.meta { font-size:8pt; color:#475569; margin-bottom:16px; text-align:right; }
.tag { background:#F8FAFC; border:1px solid #E2E8F0; padding:3px 8px; border-radius:4px; margin-left:5px; color:#334155; }
.veredito { background:#FAFAF9; border:1px solid #E5E7EB; border-left:4px solid {{ vc }}; padding:14px 18px; margin-bottom:18px; }
.veredito .lbl { font-size:7.5pt; color:#64748B; text-transform:uppercase; font-weight:bold; letter-spacing:0.5px; margin-bottom:4px; }
.veredito .val { font-size:14pt; color:{{ vc }}; font-weight:bold; margin-bottom:6px; text-transform:uppercase; }
.veredito p { font-size:9pt; color:#334155; margin:0; line-height:1.55; }
.sec { font-size:11pt; font-weight:bold; color:#0E5C66; border-bottom:1px solid #CBD5E1; padding-bottom:6px; margin:22px 0 12px; text-transform:uppercase; letter-spacing:0.5px; page-break-after:avoid; }
.intro { color:#475569; margin-bottom:12px; text-align:justify; }
.kpis { display:table; width:100%; border:1px solid #E2E8F0; background:#F8FAFC; margin-bottom:6px; }
.kpis .c { display:table-cell; padding:11px 8px; border-right:1px solid #E2E8F0; text-align:center; }
.kpis .c:last-child { border-right:none; }
.kpi-t { font-size:7.5pt; color:#64748B; text-transform:uppercase; font-weight:bold; margin-bottom:3px; }
.kpi-n { font-size:17pt; font-weight:bold; color:#0E5C66; }
.errc { width:100%; border-collapse:separate; border-spacing:8px; margin:0 -8px; }
.errc td { width:50%; padding:13px; background:#F8FAFC; border:1px solid #E2E8F0; vertical-align:top; }
.errc .h { font-weight:bold; font-size:9.5pt; margin-bottom:8px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid rgba(0,0,0,.05); padding-bottom:5px; }
.errc ul { margin:0; padding-left:14px; font-size:8.5pt; color:#334155; }
.errc li { margin-bottom:5px; line-height:1.4; }
.card { border:1px solid #E2E8F0; padding:14px; background:#fff; }
table.d { width:100%; border-collapse:collapse; }
table.d th { text-align:left; padding:7px 9px; font-size:8pt; font-weight:bold; color:#fff; background:#0E5C66; text-transform:uppercase; }
table.d td { padding:7px 9px; font-size:8.5pt; color:#1E293B; border-bottom:1px solid #F1F5F9; }
table.d tr:nth-child(even) td { background:#F8FAFC; }
.rec td { background:#ECFDF5 !important; font-weight:bold; }
.pill { display:inline-block; padding:1px 7px; border-radius:9px; font-size:7.5pt; font-weight:bold; }
.pill.ok { background:#DCFCE7; color:#166534; } .pill.no { background:#FEE2E2; color:#991B1B; } .pill.mid { background:#FEF9C3; color:#854D0E; }
.bar-row { display:flex; align-items:center; gap:8px; font-size:8.5pt; margin-bottom:3px; }
.bar-row .lab { width:115px; color:#475569; }
.bar-wrap { flex:1; height:13px; background:#E2E8F0; border-radius:3px; overflow:hidden; }
.bar { height:100%; background:#0E5C66; opacity:.35; }
.bar-row .num { width:60px; text-align:right; font-weight:bold; }
.bar-row .sx { width:74px; text-align:right; color:#64748B; }
.note { font-size:8pt; color:#64748B; margin-top:6px; line-height:1.4; }
.timing { display:table; width:100%; border:1px solid #E2E8F0; background:#F8FAFC; }
.timing .c { display:table-cell; width:33.33%; padding:12px; border-right:1px solid #E2E8F0; text-align:center; }
.timing .c:last-child { border-right:none; }
.timing-d { font-size:8.5pt; color:#475569; text-align:justify; padding:12px; border:1px solid #E2E8F0; border-top:none; }
.alert { background:#FEF2F2; border:1px solid #FECACA; border-radius:5px; padding:12px 14px; }
.alert ul { margin:0; padding-left:16px; font-size:9pt; color:#7F1D1D; } .alert li { margin-bottom:3px; }
</style></head><body>
<table class="header"><tr>
  <td style="vertical-align:bottom; width:42%;"><div class="logo"><span class="a">GYM</span>SITE</div><div class="logo-sub">Intelligence</div></td>
  <td style="text-align:right; vertical-align:bottom; width:58%;"><div class="doc-title">Relatório de Viabilidade</div><div class="doc-sub">Inteligência de Mercado Fitness · Pipeline A0–A9</div></td>
</tr></table>
<div class="meta">
  <span class="tag"><strong>Praça:</strong> {{ bairro }} ({{ cidade }}{% if uf %}/{{ uf }}{% endif %})</span>
  <span class="tag"><strong>Negócio:</strong> {{ tipo }} · {{ area }}</span>
  <span class="tag"><strong>Data:</strong> {{ data }}</span>
  <span class="tag"><strong>Ref:</strong> {{ ref }}</span>
</div>

{% if veredito %}<div class="veredito"><div class="lbl">Veredito do Headroom de Renda (Censo IBGE 2022 × Concorrentes)</div>
  <div class="val">{{ veredito }}</div>{% if justificativa %}<p>{{ justificativa }}</p>{% endif %}</div>{% endif %}

<div class="sec">1. Sumário de Scores</div>
<div class="kpis">
  <div class="c"><div class="kpi-t">Score Bairro</div><div class="kpi-n">{{ scores.bairro }}</div></div>
  <div class="c"><div class="kpi-t">Top Candidato</div><div class="kpi-n">{{ scores.top1 }}</div></div>
  <div class="c"><div class="kpi-t">Saturação</div><div class="kpi-n" style="font-size:12pt; padding-top:3px;">{{ scores.saturacao }}</div></div>
  <div class="c"><div class="kpi-t">Concorrentes</div><div class="kpi-n">{{ scores.concorrentes }}</div></div>
  {% if modelo_recomendado %}<div class="c"><div class="kpi-t">Modelo</div><div class="kpi-n" style="font-size:12pt; padding-top:3px; color:#1B2A4A;">{{ modelo_recomendado }}</div></div>{% endif %}
</div>

{% if mercado %}
<div class="sec">2. Contexto de Mercado</div>
<table class="d"><tr><th>Indicador</th><th>Valor</th></tr>
  {% if mercado.ticket %}<tr><td>Ticket médio local</td><td>{{ mercado.ticket }}</td></tr>{% endif %}
  {% if mercado.aluguel %}<tr><td>Aluguel comercial</td><td>{{ mercado.aluguel }}</td></tr>{% endif %}
  {% if mercado.renda %}<tr><td>Renda do bairro</td><td>{{ mercado.renda }}</td></tr>{% endif %}
  {% if mercado.tendencia %}<tr><td>Tendência</td><td>{{ mercado.tendencia }}</td></tr>{% endif %}
  {% if mercado.parque %}<tr><td>Parque ativo (CNPJ)</td><td>{{ mercado.parque }}</td></tr>{% endif %}
  {% if mercado.novos %}<tr><td>Novos CNPJ fitness (90d)</td><td>{{ mercado.novos }}</td></tr>{% endif %}
</table>{% endif %}

{% if demografia %}
<div class="sec">3. Demografia do Bairro</div>
{% if demografia.renda or demografia.pop %}<table class="d"><tr><th>Dimensão</th><th>Valor (fonte real do bairro)</th></tr>
  {% if demografia.renda %}<tr><td>Renda per capita</td><td>{{ demografia.renda }}</td></tr>{% endif %}
  {% if demografia.pop %}<tr><td>População</td><td>{{ demografia.pop }}</td></tr>{% endif %}
</table>{% endif %}
{% if demografia.piramide %}
<div style="margin-top:10px; font-size:8pt; color:#64748B; text-transform:uppercase; font-weight:bold; letter-spacing:0.5px;">Público por idade × sexo (bairro real, Censo 2022 por setor)</div>
<div style="margin-top:6px;">
{% for p in demografia.piramide %}
  <div class="bar-row"><span class="lab">{{ p.faixa }} · {{ p.nome }}</span>
    <div class="bar-wrap"><div class="bar" style="width:{{ p.pct }}%;"></div></div>
    <span class="num">{{ p.total }}</span><span class="sx">{{ p.m }}♀/{{ p.h }}♂</span></div>
{% endfor %}
</div>
<div class="note">Público predominante: <strong>{{ demografia.dominante }}</strong> · perfil <strong>{{ demografia.tendencia }}</strong>. Idade REAL do bairro (agregação de {{ demografia.n_setores }} setores) — não herdada do município.</div>
{% endif %}{% endif %}

{% if competidores %}
<div class="sec">4. Inteligência Competitiva</div>
<table class="d"><tr><th>Concorrente</th><th>Rating</th><th>Avaliações</th><th>Bairro</th><th>24h</th></tr>
{% for c in competidores %}<tr><td>{{ c.nome }}</td><td>{{ c.rating }}</td><td>{{ c.aval }}</td><td>{{ c.bairro }}</td><td>{{ c.h24 }}</td></tr>{% endfor %}
</table>{% endif %}

{% if cenarios %}
<div class="sec">5. Viabilidade Financeira (3 Cenários)</div>
<table class="d"><tr><th>Modelo</th><th>Ticket</th><th>Receita/mês</th><th>Lucro/mês</th><th>Margem</th><th>Payback</th><th>Viabilidade</th></tr>
{% for c in cenarios %}<tr class="{{ 'rec' if c.recomendado }}"><td>{{ c.modelo }}{{ ' ★' if c.recomendado }}</td><td>{{ c.ticket }}</td><td>{{ c.receita }}</td><td>{{ c.lucro }}</td><td>{{ c.margem }}</td><td>{{ c.payback }}</td>
  <td><span class="pill {{ c.viab_cls }}">{{ c.viab }}</span></td></tr>{% endfor %}
</table>{% endif %}

{% if errc %}
<div class="sec">6. Posicionamento Estratégico — Framework ERRC</div>
<p class="intro">Diretrizes derivadas da oferta real dos concorrentes e das dores coletadas na praça:</p>
<table class="errc">
  <tr><td style="border-top:3px solid #DC2626;"><div class="h" style="color:#991B1B;">Eliminar</div><ul>{% for i in errc.eliminar %}<li>{{ i }}</li>{% endfor %}</ul></td>
      <td style="border-top:3px solid #D97706;"><div class="h" style="color:#92400E;">Reduzir</div><ul>{% for i in errc.reduzir %}<li>{{ i }}</li>{% endfor %}</ul></td></tr>
  <tr><td style="border-top:3px solid #2563EB;"><div class="h" style="color:#1E40AF;">Aumentar</div><ul>{% for i in errc.aumentar %}<li>{{ i }}</li>{% endfor %}</ul></td>
      <td style="border-top:3px solid #16A34A;"><div class="h" style="color:#166534;">Criar</div><ul>{% for i in errc.criar %}<li>{{ i }}</li>{% endfor %}</ul></td></tr>
</table>{% endif %}

{% if gaps or ticket_rec %}
<div class="sec">7. GAPs Reais e Proposta Tarifária</div>
<table style="width:100%; border-collapse:collapse;"><tr>
  <td style="width:35%; vertical-align:top; padding-right:12px;"><div class="card" style="height:100%;">
    <div class="kpi-t">Posicionamento Tarifário</div><div class="kpi-n">{{ ticket_rec or '—' }}<span style="font-size:10pt; color:#64748B;"> /mês</span></div>
    {% if ticket_banda %}<div style="font-size:8pt; color:#64748B; margin:5px 0 9px; border-bottom:1px solid #E2E8F0; padding-bottom:8px;">Banda viável: {{ ticket_banda }}</div>{% endif %}
    {% if benchmarks %}<div style="font-size:8pt; color:#475569; line-height:1.5;"><strong>Ancoragem:</strong><br>{% for b in benchmarks %}&bull; {{ b }}<br>{% endfor %}</div>{% endif %}
  </div></td>
  <td style="width:65%; vertical-align:top;"><div class="card" style="height:100%; padding:0;">
    <table class="d"><tr><th>Serviço (GAP no mercado)</th></tr>
    {% for g in gaps %}<tr><td>{{ g }}</td></tr>{% endfor %}{% if not gaps %}<tr><td style="color:#64748B;">Mercado coberto nos serviços-núcleo — foco em qualidade/preço.</td></tr>{% endif %}</table>
  </div></td>
</tr></table>{% endif %}

{% if demanda %}
<div class="sec">8. Janela de Entrada (Demanda Futura Datada)</div>
<div class="timing">
  <div class="c"><div class="kpi-t">Obras residenciais (T+24)</div><div class="kpi-n" style="font-size:15pt;">{{ demanda.n }}</div></div>
  <div class="c"><div class="kpi-t">Captura estimada</div><div class="kpi-n" style="font-size:15pt;">~{{ demanda.captura }} alunos</div></div>
  <div class="c"><div class="kpi-t">Receita/mês T+24</div><div class="kpi-n" style="font-size:13pt; padding-top:2px;">R$ {{ demanda.receita }}</div></div>
</div>
<div class="timing-d"><strong>Diretriz de timing:</strong> {{ demanda.moradores }} novos moradores em obra. Upside captável com marketing, sem CAPEX extra. <em>Fonte: CNO/RFB + IBGE Censo 2022.</em></div>{% endif %}

{% if candidatos %}
<div class="sec">9. Top Candidatos (Imóveis)</div>
<table class="d"><tr><th>#</th><th>Nome</th><th>Tipo</th><th>Geo</th><th>Ancor.</th><th>Endereço</th></tr>
{% for c in candidatos %}<tr><td>{{ c.pos }}</td><td>{{ c.nome }}</td><td>{{ c.tipo }}</td><td>{{ c.geo }}</td><td>{{ c.ancor }}</td><td style="font-size:8pt;">{{ c.endereco }}</td></tr>{% endfor %}
</table>{% endif %}

{% if alertas %}
<div class="sec">10. Alertas e Ressalvas</div>
<div class="alert"><ul>{% for a in alertas %}<li>{{ a }}</li>{% endfor %}</ul></div>{% endif %}

</body></html>
"""

_VEREDITO_COR = {
    "OCEANO_AZUL": "#16A34A", "APROVADO": "#16A34A", "PREMIUM": "#16A34A",
    "TRANSICAO": "#EA580C", "INVESTIGAR MAIS": "#EA580C", "TRANSIÇÃO": "#EA580C",
    "OCEANO_VERMELHO": "#DC2626", "REPROVADO": "#DC2626",
}
_NOME_FAIXA = {"15-24": "Jovem", "25-39": "Core", "40-59": "Maduro", "60+": "Silver"}


def _brl(v) -> str:
    try:
        return f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _viab_cls(v: str) -> str:
    v = (v or "").upper()
    if "INVI" in v:
        return "no"
    if v in ("ALTO", "ALTA", "OK"):
        return "ok"
    return "mid"


def _piramide(demo_bairro: dict) -> dict | None:
    perfil = (demo_bairro or {}).get("perfil_idade_sexo_bairro")
    segs = (perfil or {}).get("segmentos") if isinstance(perfil, dict) else None
    if not isinstance(segs, dict):
        return None
    rows = []
    for faixa in ("15-24", "25-39", "40-59", "60+"):
        s = segs.get(faixa)
        if isinstance(s, dict) and (s.get("total") or 0) > 0:
            rows.append((faixa, s))
    if not rows:
        return None
    maxt = max(int(s["total"]) for _, s in rows)
    dom = max(rows, key=lambda r: int(r[1]["total"]))
    pctm = dom[1].get("pct_mulheres") or 50
    tend = "majoritariamente feminino" if pctm >= 55 else "majoritariamente masculino" if pctm <= 45 else "equilibrado"
    return {
        "piramide": [{
            "faixa": f, "nome": _NOME_FAIXA.get(f, ""), "total": _int(s["total"]),
            "pct": round(100 * int(s["total"]) / maxt), "m": round(s.get("pct_mulheres") or 0),
            "h": round(s.get("pct_homens") or 0),
        } for f, s in rows],
        "dominante": f"{dom[0]} ({_NOME_FAIXA.get(dom[0], '')})",
        "tendencia": tend, "n_setores": perfil.get("n_setores") or "—",
    }


def _contexto(model: RelatorioPdfModel) -> dict[str, Any]:
    pos = model.posicionamento_estrategico if isinstance(model.posicionamento_estrategico, dict) else {}
    meta = model.metadata if isinstance(model.metadata, dict) else {}

    errc_raw = pos.get("framework_errc")
    errc = None
    if isinstance(errc_raw, dict) and any(errc_raw.get(k) for k in ("eliminar", "reduzir", "aumentar", "criar")):
        errc = {k: [str(x) for x in (errc_raw.get(k) or [])] for k in ("eliminar", "reduzir", "aumentar", "criar")}

    ticket = pos.get("ticket")
    ticket_rec = ticket_banda = None
    if isinstance(ticket, dict) and ticket.get("ticket_recomendado") is not None:
        ticket_rec = f"R$ {_brl(ticket.get('ticket_recomendado'))}"
        lo, hi = ticket.get("banda_min"), ticket.get("banda_max")
        if lo and hi:
            ticket_banda = f"R$ {_brl(lo)} a R$ {_brl(hi)}"

    veredito = pos.get("veredito_posicionamento") or model.veredito
    vc = _VEREDITO_COR.get(str(veredito or "").upper().strip(), "#0E5C66")

    mkt = model.market
    mercado = None
    if mkt is not None:
        mercado = {
            "ticket": mkt.ticket_mercado, "aluguel": mkt.aluguel_m2, "renda": mkt.renda,
            "tendencia": mkt.tendencia, "parque": _int(mkt.parque_ativo) if mkt.parque_ativo else None,
            "novos": mkt.novos_cnpj_90d,
        }

    demo_b = meta.get("demografia_bairro") if isinstance(meta.get("demografia_bairro"), dict) else {}
    pir = _piramide(demo_b)
    demografia = None
    renda_b = demo_b.get("renda_media")
    pop_b = demo_b.get("populacao")
    if pir or renda_b or pop_b:
        demografia = {
            "renda": f"R$ {_brl(renda_b)}" if renda_b else None,
            "pop": _int(pop_b) if pop_b else None,
            **(pir or {}),
        }

    cenarios = []
    rec_norm = (model.modelo_recomendado or "").strip().lower()
    for c in (model.cenarios or []):
        cenarios.append({
            "modelo": c.label or c.modelo, "ticket": f"R$ {_brl(c.ticket_medio)}",
            "receita": f"R$ {_brl(c.receita_mensal)}" if c.receita_mensal else "—",
            "lucro": f"R$ {_brl(c.lucro_mensal)}" if c.lucro_mensal is not None else "—",
            "margem": f"{c.margem_pct:.0f}%" if c.margem_pct is not None else "—",
            "payback": f"{c.payback_meses}m" if c.payback_meses else "—",
            "viab": c.viabilidade or "—", "viab_cls": _viab_cls(c.viabilidade or ""),
            "recomendado": bool(rec_norm) and (c.modelo or "").lower() == rec_norm or (c.label or "").lower() == rec_norm,
        })

    competidores = [{
        "nome": c.nome[:38], "rating": c.rating if c.rating is not None else "—",
        "aval": _int(c.num_avaliacoes) if c.num_avaliacoes else "—",
        "bairro": c.bairro or "—", "h24": "sim" if c.tem_24h else "—",
    } for c in (model.competidores or [])]

    candidatos = [{
        "pos": c.posicao, "nome": c.nome[:34], "tipo": (c.tipo_imovel_label or "—")[:18],
        "geo": f"{c.score_geoscout:.1f}" if c.score_geoscout is not None else "—",
        "ancor": f"{c.score_ancoragem:.1f}" if c.score_ancoragem is not None else "—",
        "endereco": (c.endereco or "—")[:60],
    } for c in (model.candidatos or [])]

    demanda = None
    df = meta.get("demanda_futura")
    if isinstance(df, dict) and df.get("status") == "ok" and (df.get("provavel_residencial_n") or 0) > 0:
        demanda = {
            "n": int(df.get("provavel_residencial_n") or 0),
            "captura": int(float(df.get("captura_total_est") or 0)),
            "receita": _brl(df.get("receita_total_mensal_est")),
            "moradores": _brl(df.get("moradores_total_est")),
        }

    return {
        "bairro": model.bairro, "cidade": model.cidade, "uf": model.uf,
        "tipo": (model.tipo_negocio or "").replace("_", " "),
        "area": f"{model.area_m2_min}–{model.area_m2_max} m²",
        "data": model.data_execucao or "—", "ref": (model.relatorio_id or "")[:8],
        "rodape": "Confidencial · GymSite Intelligence · valores estimados (validar em due diligence)",
        "veredito": str(veredito).upper() if veredito else None,
        "justificativa": pos.get("justificativa_recomendacao") or pos.get("justificativa"),
        "vc": vc, "errc": errc, "modelo_recomendado": model.modelo_recomendado,
        "gaps": [str(g) for g in (pos.get("gaps_identificados") or [])][:6],
        "ticket_rec": ticket_rec, "ticket_banda": ticket_banda,
        "benchmarks": [c["nome"][:26] + (f" ({c['bairro']})" if c["bairro"] != "—" else "") for c in competidores[:4]],
        "scores": {
            "bairro": f"{model.score_bairro:.1f}" if model.score_bairro is not None else "—",
            "top1": f"{model.score_top1:.1f}" if model.score_top1 is not None else "—",
            "saturacao": model.nivel_saturacao or "—",
            "concorrentes": model.total_concorrentes if model.total_concorrentes is not None else "—",
        },
        "mercado": mercado, "demografia": demografia, "cenarios": cenarios,
        "competidores": competidores, "candidatos": candidatos, "demanda": demanda,
        "alertas": [str(a) for a in (model.alertas or [])][:12],
    }


def gerar_html(model: RelatorioPdfModel) -> str:
    """HTML do relatório completo (testável sem WeasyPrint)."""
    from jinja2 import Template

    return Template(_TEMPLATE).render(**_contexto(model))


def gerar_pdf_weasy(model: RelatorioPdfModel) -> bytes:
    """HTML → PDF via WeasyPrint. Precisa libs de sistema (Dockerfile)."""
    from weasyprint import HTML

    return HTML(string=gerar_html(model), base_url=_ASSETS).write_pdf()
