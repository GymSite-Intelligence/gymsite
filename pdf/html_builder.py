"""PDF de produção via HTML/CSS → WeasyPrint (migração do ReportLab).

Arquitetura-alvo (recomendação aceita): o LLM NÃO escreve o documento. Aqui o template
HTML (Jinja2) cruza o dado DETERMINÍSTICO do pipeline (A4/A9/demanda — já no
RelatorioPdfModel) com os insights estruturados. Garante conformidade financeira (o
número vem da variável, não da memória do LLM) e mata a classe de bug do markdown-do-LLM
(<b> literal, seção não-narrada, gaps genéricos).

Fase 1 (esta): seção de POSICIONAMENTO (A9) — header marca, veredito determinístico,
matriz ERRC 2×2, GAPs reais + ticket, demanda futura datada. Layout do mockup aprovado.
WeasyPrint precisa de libs de sistema (pango/cairo) — instaladas no Dockerfile; em dev
Windows o `gerar_pdf_weasy` degrada, mas `gerar_html` (testável) sempre roda.
"""
from __future__ import annotations

import os
from typing import Any

from pdf.models import RelatorioPdfModel

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

# Cores da marca (identidade aprovada): navy 1B2A4A, lime A3E635, teal 0E5C66.
_TEMPLATE = """
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><style>
@page { size: A4; margin: 16mm 14mm;
  @bottom-right { content: "Página " counter(page); font-family: Helvetica; font-size: 8pt; color:#64748B; }
  @bottom-left { content: "{{ rodape }}"; font-family: Helvetica; font-size: 8pt; font-style: italic; color:#64748B; } }
body { margin:0; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; color:#1E293B; font-size:9pt; line-height:1.45; }
.header { width:100%; border-collapse:collapse; border-bottom:2px solid #A3E635; padding-bottom:10px; margin-bottom:14px; }
.logo { font-weight:900; font-size:20pt; letter-spacing:-0.5px; color:#1B2A4A; line-height:1; }
.logo .a { color:#A3E635; }
.logo-sub { display:block; font-weight:500; font-size:7.5pt; color:#64748B; letter-spacing:2.5px; text-transform:uppercase; margin-top:3px; }
.doc-title { font-size:14pt; font-weight:bold; color:#0F172A; margin:0 0 3px; text-transform:uppercase; letter-spacing:0.5px; }
.doc-sub { font-size:9pt; color:#64748B; margin:0; }
.meta { font-size:8pt; color:#475569; margin-bottom:18px; text-align:right; }
.tag { background:#F8FAFC; border:1px solid #E2E8F0; padding:3px 8px; border-radius:4px; margin-left:5px; color:#334155; }
.veredito { background:#FAFAF9; border:1px solid #E5E7EB; border-left:4px solid {{ vc }}; padding:16px 18px; margin-bottom:24px; }
.veredito .lbl { font-size:7.5pt; color:#64748B; text-transform:uppercase; font-weight:bold; letter-spacing:0.5px; margin-bottom:4px; }
.veredito .val { font-size:14pt; color:{{ vc }}; font-weight:bold; margin-bottom:8px; text-transform:uppercase; }
.veredito p { font-size:9pt; color:#334155; margin:0; line-height:1.6; }
.sec { font-size:11pt; font-weight:bold; color:#0E5C66; border-bottom:1px solid #CBD5E1; padding-bottom:6px; margin:26px 0 14px; text-transform:uppercase; letter-spacing:0.5px; }
.intro { color:#475569; margin-bottom:14px; text-align:justify; }
.errc { width:100%; border-collapse:separate; border-spacing:9px; margin:0 -9px; }
.errc td { width:50%; padding:14px; background:#F8FAFC; border:1px solid #E2E8F0; vertical-align:top; }
.errc .h { font-weight:bold; font-size:9.5pt; margin-bottom:9px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid rgba(0,0,0,.05); padding-bottom:5px; }
.errc ul { margin:0; padding-left:14px; font-size:8.5pt; color:#334155; }
.errc li { margin-bottom:5px; line-height:1.4; }
.card { border:1px solid #E2E8F0; padding:14px; background:#fff; }
.kpi-t { font-size:8pt; color:#64748B; text-transform:uppercase; font-weight:bold; margin-bottom:4px; }
.kpi-n { font-size:20pt; font-weight:bold; color:#0E5C66; }
table.d { width:100%; border-collapse:collapse; }
table.d th { text-align:left; padding:8px 10px; font-size:8pt; font-weight:bold; color:#64748B; text-transform:uppercase; border-bottom:1px solid #CBD5E1; }
table.d td { padding:9px 10px; font-size:8.5pt; color:#1E293B; border-bottom:1px solid #F1F5F9; }
.timing { display:table; width:100%; border:1px solid #E2E8F0; background:#F8FAFC; }
.timing .c { display:table-cell; width:33.33%; padding:14px; border-right:1px solid #E2E8F0; text-align:center; }
.timing .c:last-child { border-right:none; }
.timing-d { font-size:8.5pt; color:#475569; text-align:justify; padding:13px; border:1px solid #E2E8F0; border-top:none; }
</style></head><body>
<table class="header"><tr>
  <td style="vertical-align:bottom; width:42%;">
    <div class="logo"><span class="a">GYM</span>SITE</div><div class="logo-sub">Intelligence</div>
  </td>
  <td style="text-align:right; vertical-align:bottom; width:58%;">
    <div class="doc-title">Posicionamento Estratégico</div>
    <div class="doc-sub">Framework ERRC &amp; Diretrizes de Mercado</div>
  </td>
</tr></table>
<div class="meta">
  <span class="tag"><strong>Praça:</strong> {{ bairro }} ({{ cidade }}{% if uf %}/{{ uf }}{% endif %})</span>
  <span class="tag"><strong>Data:</strong> {{ data }}</span>
  <span class="tag"><strong>Ref:</strong> {{ ref }}</span>
</div>
{% if veredito %}
<div class="veredito"><div class="lbl">Veredito do Headroom de Renda (Censo IBGE 2022 × Concorrentes)</div>
  <div class="val">{{ veredito }}</div>
  {% if justificativa %}<p>{{ justificativa }}</p>{% endif %}
</div>{% endif %}
{% if errc %}
<div class="sec">1. Diagnóstico Estratégico — Framework ERRC</div>
<p class="intro">Diretrizes derivadas da oferta real dos concorrentes e das dores coletadas na praça. Operação deve seguir estritamente os quatro eixos:</p>
<table class="errc">
  <tr>
    <td style="border-top:3px solid #DC2626;"><div class="h" style="color:#991B1B;">Eliminar</div><ul>{% for i in errc.eliminar %}<li>{{ i }}</li>{% endfor %}</ul></td>
    <td style="border-top:3px solid #D97706;"><div class="h" style="color:#92400E;">Reduzir</div><ul>{% for i in errc.reduzir %}<li>{{ i }}</li>{% endfor %}</ul></td>
  </tr>
  <tr>
    <td style="border-top:3px solid #2563EB;"><div class="h" style="color:#1E40AF;">Aumentar</div><ul>{% for i in errc.aumentar %}<li>{{ i }}</li>{% endfor %}</ul></td>
    <td style="border-top:3px solid #16A34A;"><div class="h" style="color:#166534;">Criar</div><ul>{% for i in errc.criar %}<li>{{ i }}</li>{% endfor %}</ul></td>
  </tr>
</table>{% endif %}
{% if gaps or ticket_rec %}
<div class="sec">2. GAPs Reais e Proposta Tarifária</div>
<table style="width:100%; border-collapse:collapse;"><tr>
  <td style="width:35%; vertical-align:top; padding-right:14px;">
    <div class="card" style="height:100%;">
      <div class="kpi-t">Posicionamento Tarifário</div>
      <div class="kpi-n">{{ ticket_rec or '—' }}<span style="font-size:10pt; color:#64748B;"> /mês</span></div>
      {% if ticket_banda %}<div style="font-size:8pt; color:#64748B; margin:6px 0 10px; border-bottom:1px solid #E2E8F0; padding-bottom:9px;">Banda viável: {{ ticket_banda }}</div>{% endif %}
      {% if benchmarks %}<div style="font-size:8pt; color:#475569; line-height:1.5;"><strong>Ancoragem competitiva:</strong><br>{% for b in benchmarks %}&bull; {{ b }}<br>{% endfor %}</div>{% endif %}
    </div>
  </td>
  <td style="width:65%; vertical-align:top;">
    <div class="card" style="height:100%; padding:0;">
      <table class="d"><thead><tr><th>Serviço (GAP no mercado)</th></tr></thead><tbody>
      {% for g in gaps %}<tr><td>{{ g }}</td></tr>{% endfor %}
      {% if not gaps %}<tr><td style="color:#64748B;">Mercado coberto nos serviços-núcleo — foco em qualidade/preço.</td></tr>{% endif %}
      </tbody></table>
    </div>
  </td>
</tr></table>{% endif %}
{% if demanda %}
<div class="sec">3. Janela de Entrada e Demanda Futura</div>
<div class="timing">
  <div class="c"><div class="kpi-t">Obras residenciais (T+24)</div><div class="kpi-n" style="font-size:16pt;">{{ demanda.n }}</div></div>
  <div class="c"><div class="kpi-t">Captura estimada</div><div class="kpi-n" style="font-size:16pt;">~{{ demanda.captura }} alunos</div></div>
  <div class="c"><div class="kpi-t">Receita/mês T+24</div><div class="kpi-n" style="font-size:14pt; padding-top:2px;">R$ {{ demanda.receita }}</div></div>
</div>
<div class="timing-d"><strong>Diretriz de timing:</strong> {{ demanda.moradores }} novos moradores em obra. Upside captável com marketing, sem CAPEX extra. <em>Fonte: CNO/RFB + IBGE Censo 2022.</em></div>{% endif %}
</body></html>
"""

_VEREDITO_COR = {
    "OCEANO_AZUL": "#16A34A", "APROVADO": "#16A34A", "PREMIUM": "#16A34A",
    "TRANSICAO": "#EA580C", "INVESTIGAR MAIS": "#EA580C", "TRANSIÇÃO": "#EA580C",
    "OCEANO_VERMELHO": "#DC2626", "REPROVADO": "#DC2626",
}


def _brl(v) -> str:
    try:
        return f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def _contexto(model: RelatorioPdfModel) -> dict[str, Any]:
    pos = model.posicionamento_estrategico or {}
    errc_raw = pos.get("framework_errc") if isinstance(pos, dict) else None
    errc = None
    if isinstance(errc_raw, dict) and any(errc_raw.get(k) for k in ("eliminar", "reduzir", "aumentar", "criar")):
        errc = {k: [str(x) for x in (errc_raw.get(k) or [])] for k in ("eliminar", "reduzir", "aumentar", "criar")}

    ticket = pos.get("ticket") if isinstance(pos, dict) else None
    ticket_rec = ticket_banda = None
    if isinstance(ticket, dict) and ticket.get("ticket_recomendado") is not None:
        ticket_rec = f"R$ {_brl(ticket.get('ticket_recomendado'))}"
        lo, hi = ticket.get("banda_min"), ticket.get("banda_max")
        if lo and hi:
            ticket_banda = f"R$ {_brl(lo)} a R$ {_brl(hi)}"

    benchmarks = []
    for c in (model.competidores or [])[:4]:
        bn = c.nome[:28] + (f" ({c.bairro})" if c.bairro else "")
        benchmarks.append(bn)

    veredito = pos.get("veredito_posicionamento") if isinstance(pos, dict) else None
    veredito = veredito or model.veredito
    vc = _VEREDITO_COR.get(str(veredito or "").upper().strip(), "#0E5C66")

    demanda = None
    df = (model.metadata or {}).get("demanda_futura") if isinstance(model.metadata, dict) else None
    if isinstance(df, dict) and df.get("status") == "ok" and (df.get("provavel_residencial_n") or 0) > 0:
        demanda = {
            "n": int(df.get("provavel_residencial_n") or 0),
            "captura": int(float(df.get("captura_total_est") or 0)),
            "receita": _brl(df.get("receita_total_mensal_est")),
            "moradores": _brl(df.get("moradores_total_est")),
        }

    return {
        "bairro": model.bairro, "cidade": model.cidade, "uf": model.uf,
        "data": model.data_execucao or "—", "ref": (model.relatorio_id or "")[:8],
        "rodape": "Confidencial · GymSite Intelligence · A9 PositioningStrategist",
        "veredito": str(veredito).upper() if veredito else None,
        "justificativa": pos.get("justificativa_recomendacao") or pos.get("justificativa") if isinstance(pos, dict) else None,
        "vc": vc, "errc": errc,
        "gaps": [str(g) for g in (pos.get("gaps_identificados") or [])][:6] if isinstance(pos, dict) else [],
        "ticket_rec": ticket_rec, "ticket_banda": ticket_banda, "benchmarks": benchmarks,
        "demanda": demanda,
    }


def gerar_html(model: RelatorioPdfModel) -> str:
    """HTML do relatório (testável sem WeasyPrint)."""
    from jinja2 import Template

    return Template(_TEMPLATE).render(**_contexto(model))


def gerar_pdf_weasy(model: RelatorioPdfModel) -> bytes:
    """HTML → PDF via WeasyPrint. Precisa libs de sistema (Dockerfile)."""
    from weasyprint import HTML

    return HTML(string=gerar_html(model), base_url=_ASSETS).write_pdf()
