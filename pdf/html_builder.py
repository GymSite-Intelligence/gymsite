"""PDF de produção via HTML/CSS → WeasyPrint (migração do ReportLab).

Arquitetura-alvo (aceita): o LLM NÃO escreve o documento. O template HTML (Jinja2) cruza o
dado DETERMINÍSTICO do pipeline (A4/A9/demanda/demografia — já no RelatorioPdfModel) com os
insights estruturados. Garante conformidade financeira (número vem da variável, não da
memória do LLM) e mata a classe de bug do markdown-do-LLM (<b> literal, financeiro
divergente, seção não-narrada, gaps genéricos).

Paridade com a UI (RelatorioViewerPage): veredito dual, scores 3-dim, resumo executivo,
panorama, demografia+pirâmide, competitiva, pico/lotação, anéis competitivos, cobertura
Deep Research, viabilidade (KPI strip + 3 cenários + capex), ERRC, dores/GAPs, posicionamento,
novas unidades, obras CNO, demanda futura, bairros vizinhos, candidatos, alertas.
Toda seção é data-driven: só renderiza se o dado existe.
WeasyPrint precisa libs de sistema (pango/cairo) — no Dockerfile; em dev `gerar_html` roda.
"""
from __future__ import annotations

import os
import re
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
.doc-title { font-size:14pt; font-weight:bold; color:#0F172A; margin:0 0 3px; letter-spacing:0.3px; }
.doc-sub { font-size:9pt; color:#64748B; margin:0; }
.meta { font-size:8pt; color:#475569; margin-bottom:16px; text-align:right; }
.tag { background:#F8FAFC; border:1px solid #E2E8F0; padding:3px 8px; border-radius:4px; margin-left:5px; color:#334155; }
.veredito { background:#FAFAF9; border:1px solid #E5E7EB; border-left:4px solid {{ vc }}; padding:14px 18px; margin-bottom:8px; }
.veredito .lbl { font-size:7.5pt; color:#64748B; font-weight:bold; letter-spacing:0.3px; margin-bottom:4px; }
.veredito .val { font-size:14pt; color:{{ vc }}; font-weight:bold; margin-bottom:6px; text-transform:uppercase; }
.veredito p { font-size:9pt; color:#334155; margin:0; line-height:1.55; }
.duo { display:table; width:100%; border-collapse:separate; border-spacing:8px 0; margin:0 -8px 16px; }
.duo .c { display:table-cell; width:50%; padding:10px 14px; border:1px solid #E2E8F0; background:#F8FAFC; }
.duo .l { font-size:7pt; color:#64748B; font-weight:bold; letter-spacing:0.3px; }
.duo .v { font-size:11pt; font-weight:bold; margin-top:3px; }
.sec { font-size:11pt; font-weight:bold; color:#0E5C66; border-bottom:1px solid #CBD5E1; padding-bottom:6px; margin:22px 0 12px; page-break-after:avoid; }
.intro { color:#475569; margin-bottom:12px; text-align:justify; }
.prose { color:#334155; margin-bottom:10px; text-align:justify; line-height:1.6; }
.kpis { display:table; width:100%; border:1px solid #E2E8F0; background:#F8FAFC; margin-bottom:6px; }
.kpis .c { display:table-cell; padding:11px 8px; border-right:1px solid #E2E8F0; text-align:center; }
.kpis .c:last-child { border-right:none; }
.kpi-t { font-size:7.5pt; color:#64748B; font-weight:bold; margin-bottom:3px; }
.kpi-n { font-size:17pt; font-weight:bold; color:#0E5C66; }
.kpi-s { font-size:7.5pt; color:#94A3B8; margin-top:2px; }
.errc { width:100%; border-collapse:separate; border-spacing:8px; margin:0 -8px; }
.errc td { width:50%; padding:13px; background:#F8FAFC; border:1px solid #E2E8F0; vertical-align:top; }
.errc .h { font-weight:bold; font-size:9.5pt; margin-bottom:8px; letter-spacing:0.3px; border-bottom:1px solid rgba(0,0,0,.05); padding-bottom:5px; }
.errc ul { margin:0; padding-left:14px; font-size:8.5pt; color:#334155; }
.errc li { margin-bottom:5px; line-height:1.4; }
.card { border:1px solid #E2E8F0; padding:14px; background:#fff; }
table.d { width:100%; border-collapse:collapse; page-break-inside:avoid; }
table.d th { text-align:center; padding:7px 9px; font-size:8pt; font-weight:bold; color:#fff; background:#0E5C66; }
table.d td { padding:7px 9px; font-size:8.5pt; color:#1E293B; border-bottom:1px solid #F1F5F9; text-align:center; }
/* 1ª coluna (rótulo/nome) à esquerda — é label, não dado numérico */
table.d th:first-child, table.d td:first-child { text-align:left; }
table.d tr { page-break-inside:avoid; }
table.d tr:nth-child(even) td { background:#F8FAFC; }
.kpis, .timing, .errc, .duo, .veredito, .gapc, .alert, .pico { page-break-inside:avoid; }
.rec td { background:#ECFDF5 !important; font-weight:bold; }
.pill { display:inline-block; padding:1px 7px; border-radius:9px; font-size:7.5pt; font-weight:bold; }
.pill.ok { background:#DCFCE7; color:#166534; } .pill.no { background:#FEE2E2; color:#991B1B; } .pill.mid { background:#FEF9C3; color:#854D0E; }
.bar-row { display:flex; align-items:center; gap:8px; font-size:8.5pt; margin-bottom:3px; }
.bar-row .lab { width:115px; color:#475569; }
.bar-wrap { flex:1; height:13px; background:#E2E8F0; border-radius:3px; overflow:hidden; }
.bar { height:100%; background:#0E5C66; opacity:.35; }
.bar-row .num { width:60px; text-align:right; font-weight:bold; }
.bar-row .sx { width:74px; text-align:right; color:#64748B; }
.pico { display:flex; align-items:flex-end; gap:3px; height:46px; margin:8px 0 4px; }
.pico .col { flex:1; background:#0E5C66; opacity:.30; border-radius:2px 2px 0 0; min-height:2px; }
.pico .col.hot { opacity:.7; background:#A3E635; }
.pico-x { display:flex; gap:3px; font-size:6pt; color:#94A3B8; }
.pico-x span { flex:1; text-align:center; }
.note { font-size:8pt; color:#64748B; margin-top:6px; line-height:1.4; }
.gapc { border:1px solid #E2E8F0; border-left:3px solid #16A34A; background:#F8FAFC; padding:9px 12px; margin-bottom:7px; }
.gapc .t { font-weight:bold; font-size:9pt; color:#0F172A; }
.gapc .d { font-size:8pt; color:#475569; margin-top:2px; line-height:1.45; }
.gapc .m { font-size:7.5pt; color:#166534; font-weight:bold; margin-top:3px; }
.chips span { display:inline-block; background:#ECFEFF; border:1px solid #A5F3FC; color:#155E75; padding:2px 9px; border-radius:10px; font-size:8pt; margin:0 4px 4px 0; }
.chips span.ghost { background:#FEF2F2; border-color:#FECACA; color:#991B1B; }
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
{% if veredito or veredito_oceano %}<div class="duo">
  <div class="c"><div class="l">Viabilidade (demanda × concorrência)</div><div class="v" style="color:{{ vc }};">{{ veredito or '—' }}</div></div>
  <div class="c"><div class="l">Oceano (estratégia de posicionamento)</div><div class="v" style="color:{{ voc }};">{{ veredito_oceano or '—' }}</div></div>
</div>{% endif %}

<div class="sec">Sumário de Scores</div>
<div class="kpis">
  <div class="c"><div class="kpi-t">Score Bairro</div><div class="kpi-n">{{ scores.bairro }}</div></div>
  <div class="c"><div class="kpi-t">Top Candidato</div><div class="kpi-n">{{ scores.top1 }}</div></div>
  <div class="c"><div class="kpi-t">Saturação</div><div class="kpi-n" style="font-size:12pt; padding-top:3px;">{{ scores.saturacao }}</div></div>
  <div class="c"><div class="kpi-t">Concorrentes</div><div class="kpi-n">{{ scores.concorrentes }}</div></div>
  {% if modelo_recomendado %}<div class="c"><div class="kpi-t">Modelo</div><div class="kpi-n" style="font-size:12pt; padding-top:3px; color:#1B2A4A;">{{ modelo_recomendado }}</div></div>{% endif %}
</div>
{% if scores_dim %}<div class="kpis" style="margin-top:6px;">
  <div class="c"><div class="kpi-t">Demográfico</div><div class="kpi-n" style="font-size:14pt;">{{ scores_dim.demografico }}</div></div>
  <div class="c"><div class="kpi-t">Competitivo</div><div class="kpi-n" style="font-size:14pt;">{{ scores_dim.competitivo }}</div></div>
  <div class="c"><div class="kpi-t">Viabilidade</div><div class="kpi-n" style="font-size:14pt;">{{ scores_dim.viabilidade }}</div></div>
</div>{% endif %}

{% if resumo %}
<div class="sec">Resumo Executivo</div>
{% for p in resumo %}<p class="prose">{{ p }}</p>{% endfor %}{% endif %}

{% if mercado or panorama %}
<div class="sec">Contexto e Panorama de Mercado</div>
<table class="d"><tr><th>Indicador</th><th>Valor</th></tr>
  {% if mercado and mercado.ticket %}<tr><td>Ticket médio local</td><td>{{ mercado.ticket }}</td></tr>{% endif %}
  {% if mercado and mercado.aluguel %}<tr><td>Aluguel comercial</td><td>{{ mercado.aluguel }}</td></tr>{% endif %}
  {% if mercado and mercado.renda %}<tr><td>Renda do bairro</td><td>{{ mercado.renda }}</td></tr>{% endif %}
  {% if mercado and mercado.tendencia %}<tr><td>Tendência</td><td>{{ mercado.tendencia }}</td></tr>{% endif %}
  {% if mercado and mercado.parque %}<tr><td>Parque ativo (CNPJ)</td><td>{{ mercado.parque }}</td></tr>{% endif %}
  {% if mercado and mercado.novos %}<tr><td>Novos CNPJ fitness (90d)</td><td>{{ mercado.novos }}</td></tr>{% endif %}
  {% if panorama and panorama.saturacao %}<tr><td>Nível de saturação</td><td>{{ panorama.saturacao }}</td></tr>{% endif %}
  {% if panorama and panorama.rating_medio %}<tr><td>Rating médio dos concorrentes</td><td>{{ panorama.rating_medio }} ★</td></tr>{% endif %}
  {% if panorama and panorama.total %}<tr><td>Concorrentes analisados</td><td>{{ panorama.total }}{% if panorama.raio %} (de {{ panorama.raio }} no raio){% endif %}</td></tr>{% endif %}
</table>{% endif %}

{% if demografia %}
<div class="sec">Demografia do Bairro</div>
{% if demografia.renda or demografia.pop %}<table class="d"><tr><th>Dimensão</th><th>Valor (fonte real do bairro)</th></tr>
  {% if demografia.renda %}<tr><td>Renda per capita</td><td>{{ demografia.renda }}</td></tr>{% endif %}
  {% if demografia.pop %}<tr><td>População</td><td>{{ demografia.pop }}</td></tr>{% endif %}
</table>{% endif %}
{% if demografia.piramide %}
<div style="margin-top:10px; font-size:8pt; color:#64748B; font-weight:bold; letter-spacing:0.3px;">Público por idade × sexo (bairro real, Censo 2022 por setor)</div>
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
<div class="sec">Inteligência Competitiva</div>
<table class="d"><tr><th>Concorrente</th><th>Rating</th><th>Avaliações</th><th>Bairro</th><th>24h</th></tr>
{% for c in competidores %}<tr><td>{{ c.nome }}</td><td>{{ c.rating }}</td><td>{{ c.aval }}</td><td>{{ c.bairro }}</td><td>{{ c.h24 }}</td></tr>{% endfor %}
</table>
{% if pico %}
<div style="margin-top:12px; font-size:8pt; color:#64748B; font-weight:bold; letter-spacing:0.3px;">Janela de demanda — lotação agregada dos concorrentes por hora</div>
<div class="pico">{% for b in pico.barras %}<div class="col {{ 'hot' if b.hora in pico.horas }}" style="height:{{ b.pct }}%;"></div>{% endfor %}</div>
<div class="pico-x">{% for b in pico.barras %}<span>{{ b.hora[:2] }}</span>{% endfor %}</div>
<div class="note">Pico de movimento: <strong>{{ pico.faixa }}</strong> ({{ pico.concentracao_pct }}% da lotação nas 3 horas de topo). Janela de maior disputa — e de maior demanda capturável.</div>
{% endif %}{% endif %}

{% if planos %}
<div class="sec">Planos e preços da concorrência</div>
<table class="d"><tr><th>Academia</th><th>Plano</th><th>Preço/mês</th><th>Fidelidade</th><th>Inclui</th></tr>
{% for p in planos %}<tr><td>{{ p.academia }}</td><td>{{ p.plano }}</td><td>{{ p.preco }}</td><td>{{ p.fidelidade }}</td><td style="font-size:8pt;">{{ p.inclui }}</td></tr>{% endfor %}
</table>
<div class="note">Planos públicos coletados via SearchAPI (busca web) por academia. Referência para o posicionamento tarifário vs concorrência.</div>{% endif %}

{% if ticket_segmentos %}
<div class="sec">Ticket por segmento e serviços entregues</div>
<table class="d"><tr><th>Segmento</th><th>Faixa de ticket</th><th>Planos</th><th>Serviços entregues</th><th>Academias</th></tr>
{% for s in ticket_segmentos %}<tr><td>{{ s.segmento }}</td><td>{{ s.faixa }}</td><td>{{ s.n }}</td><td style="font-size:8pt;">{{ s.servicos }}</td><td style="font-size:8pt;">{{ s.academias }}</td></tr>{% endfor %}
</table>
<div class="note">Segmentos por tertil dos preços reais do mercado (recalibrável). Mostra o que se ENTREGA em cada faixa de ticket — base do posicionamento: subir de faixa exige os serviços da faixa.</div>{% endif %}

{% if dores_quadro %}
<div class="sec">Dores dominantes do mercado (gaps = oportunidade)</div>
<table class="d"><tr><th>Dor (categoria)</th><th>Menções</th><th>Academias que sofrem</th></tr>
{% for d in dores_quadro %}<tr><td>{{ d.categoria }}</td><td>{{ d.mencoes }}</td><td style="font-size:8pt;">{{ d.academias }}</td></tr>{% endfor %}
</table>
<div class="note">Reclamações dos reviews consolidadas por categoria (sem texto literal). Cada dor frequente = um GAP a explorar no posicionamento.</div>{% endif %}

{% if aneis %}
<div class="sec">Anéis Competitivos (score ponderado por distância)</div>
<div class="kpis">
  <div class="c"><div class="kpi-t">No bairro</div><div class="kpi-n">{{ aneis.no_bairro }}</div></div>
  <div class="c"><div class="kpi-t">Fronteira</div><div class="kpi-n">{{ aneis.fronteira }}</div></div>
  <div class="c"><div class="kpi-t">Regional</div><div class="kpi-n">{{ aneis.regional }}</div></div>
  <div class="c"><div class="kpi-t">Score ponderado</div><div class="kpi-n" style="color:#1B2A4A;">{{ aneis.score }}</div></div>
</div>
{% if aneis.portes %}<div class="note">No bairro por porte: {{ aneis.portes }}. Peso por anel — bairro 1.0, fronteira 0.5, regional 0.2 (concorrente distante pressiona menos).</div>{% endif %}
{% if aneis.cross %}
<div style="margin-top:12px; font-size:8pt; color:#64748B; font-weight:bold; letter-spacing:0.3px;">Cross-check da contagem (Google Maps · termos do formulário + gate bairro+tipo)</div>
<div class="kpis" style="margin-top:6px;">
  <div class="c"><div class="kpi-t">Google mostra</div><div class="kpi-n" style="font-size:14pt;">{{ aneis.cross.google_n }}</div></div>
  <div class="c"><div class="kpi-t">No bairro + tipo</div><div class="kpi-n" style="font-size:14pt; color:#1B2A4A;">{{ aneis.cross.gated_n }}</div></div>
  <div class="c"><div class="kpi-t">Analisados a fundo</div><div class="kpi-n" style="font-size:14pt;">{{ aneis.cross.deep_n }}</div></div>
  <div class="c"><div class="kpi-t">Mapeados (novos)</div><div class="kpi-n" style="font-size:14pt;">{{ aneis.cross.novos_n }}</div></div>
</div>
{% if aneis.cross.lista %}
<table class="d" style="margin-top:6px;"><tr><th>Concorrente no bairro</th><th>Rating</th><th>Avaliações</th><th>Status</th></tr>
{% for c in aneis.cross.lista %}<tr><td>{{ c.nome }}</td><td>{{ c.rating }}</td><td>{{ c.aval }}</td><td><span class="pill {{ 'ok' if c.status=='analisado' else 'mid' }}">{{ c.status }}</span></td></tr>{% endfor %}
</table>{% endif %}
<div class="note">Contagem autoritativa de concorrentes no bairro = <strong>{{ aneis.cross.gated_n }}</strong> (gate bairro+tipo sobre a busca do formulário). Google lista {{ aneis.cross.google_n }} (inclui vizinhos/off-tipo); destes, {{ aneis.cross.deep_n }} já tinham reviews analisados e {{ aneis.cross.novos_n }} entram como mapeados.</div>{% endif %}{% endif %}

{% if cobertura %}
<div class="sec">Cobertura Deep Research (redes-alvo)</div>
<div class="chips">{% for r in cobertura.cobertas %}<span>{{ r }} ✓</span>{% endfor %}{% for r in cobertura.faltantes %}<span class="ghost">{{ r }} ✗</span>{% endfor %}</div>
<div class="note">{{ cobertura.cobertas|length }} de {{ cobertura.solicitadas }} redes solicitadas foram localizadas e analisadas no entorno.{% if cobertura.fantasma %} ⚠ Redes-fantasma detectadas (citadas mas não encontradas no terreno).{% endif %}</div>{% endif %}

{% if kpi_fin or cenarios %}
<div class="sec">Viabilidade Financeira</div>
{% if kpi_fin %}<div class="kpis">
  <div class="c"><div class="kpi-t">Área alvo</div><div class="kpi-n" style="font-size:13pt;">{{ kpi_fin.area }}</div><div class="kpi-s">m²</div></div>
  {% if kpi_fin.aluguel %}<div class="c"><div class="kpi-t">Aluguel/mês</div><div class="kpi-n" style="font-size:13pt;">R$ {{ kpi_fin.aluguel }}</div></div>{% endif %}
  {% if kpi_fin.capex %}<div class="c"><div class="kpi-t">CAPEX (mid)</div><div class="kpi-n" style="font-size:13pt;">R$ {{ kpi_fin.capex }}</div></div>{% endif %}
  {% if kpi_fin.payback %}<div class="c"><div class="kpi-t">Payback (mid)</div><div class="kpi-n" style="font-size:13pt;">{{ kpi_fin.payback }}</div></div>{% endif %}
</div>{% endif %}
{% if cenarios %}<table class="d" style="margin-top:6px;"><tr><th>Modelo</th><th>Ticket</th><th>Receita/mês</th><th>Lucro/mês</th><th>Margem</th><th>Payback</th><th>Alunos</th><th>Viabilidade</th></tr>
{% for c in cenarios %}<tr class="{{ 'rec' if c.recomendado }}"><td>{{ c.modelo }}{{ ' ★' if c.recomendado }}</td><td>{{ c.ticket }}</td><td>{{ c.receita }}</td><td>{{ c.lucro }}</td><td>{{ c.margem }}</td><td>{{ c.payback }}</td><td>{{ c.alunos }}</td>
  <td><span class="pill {{ c.viab_cls }}">{{ c.viab }}</span></td></tr>{% endfor %}
</table>{% endif %}
{% if capex %}
<div style="margin-top:12px; font-size:8pt; color:#64748B; font-weight:bold; letter-spacing:0.3px;">Composição do investimento — cenário {{ capex.modelo }}</div>
<div style="margin-top:6px;">
{% for r in capex.itens %}<div class="bar-row"><span class="lab">{{ r.label }}</span>
  <div class="bar-wrap"><div class="bar" style="width:{{ r.pct }}%; opacity:.5;"></div></div>
  <span class="num">R$ {{ r.valor }}</span><span class="sx">{{ r.pct }}%</span></div>{% endfor %}
</div>{% endif %}{% endif %}

{% if errc %}
<div style="page-break-inside:avoid;">
<div class="sec">Posicionamento Estratégico — Framework ERRC</div>
<p class="intro">Diretrizes derivadas da oferta real dos concorrentes e das dores coletadas na praça:</p>
<table class="errc">
  <tr><td style="border-top:3px solid #DC2626;"><div class="h" style="color:#991B1B;">Eliminar</div><ul>{% for i in errc.eliminar %}<li>{{ i }}</li>{% endfor %}</ul></td>
      <td style="border-top:3px solid #D97706;"><div class="h" style="color:#92400E;">Reduzir</div><ul>{% for i in errc.reduzir %}<li>{{ i }}</li>{% endfor %}</ul></td></tr>
  <tr><td style="border-top:3px solid #2563EB;"><div class="h" style="color:#1E40AF;">Aumentar</div><ul>{% for i in errc.aumentar %}<li>{{ i }}</li>{% endfor %}</ul></td>
      <td style="border-top:3px solid #16A34A;"><div class="h" style="color:#166534;">Criar</div><ul>{% for i in errc.criar %}<li>{{ i }}</li>{% endfor %}</ul></td></tr>
</table></div>{% endif %}

{% if gaps or ticket_rec %}
<div class="sec">Dores do Mercado e Proposta Tarifária</div>
<table style="width:100%; border-collapse:collapse;"><tr>
  <td style="width:35%; vertical-align:top; padding-right:12px;"><div class="card" style="height:100%;">
    <div class="kpi-t">Posicionamento Tarifário</div><div class="kpi-n">{{ ticket_rec or '—' }}<span style="font-size:10pt; color:#64748B;"> /mês</span></div>
    {% if ticket_banda %}<div style="font-size:8pt; color:#64748B; margin:5px 0 9px; border-bottom:1px solid #E2E8F0; padding-bottom:8px;">Banda viável: {{ ticket_banda }}</div>{% endif %}
    {% if benchmarks %}<div style="font-size:8pt; color:#475569; line-height:1.5;"><strong>Ancoragem:</strong><br>{% for b in benchmarks %}&bull; {{ b }}<br>{% endfor %}</div>{% endif %}
  </div></td>
  <td style="width:65%; vertical-align:top;">
    {% for g in gaps %}<div class="gapc"><div class="t">{{ g.titulo }}</div>{% if g.desc %}<div class="d">{{ g.desc }}</div>{% endif %}{% if g.potencial %}<div class="m">Potencial: {{ g.potencial }}{% if g.dificuldade %} · implementação {{ g.dificuldade }}{% endif %}</div>{% endif %}</div>{% endfor %}
    {% if not gaps %}<div class="card" style="color:#64748B;">Mercado coberto nos serviços-núcleo — foco em qualidade/preço.</div>{% endif %}
  </td>
</tr></table>{% endif %}

{% if posicionamento_txt %}
<div class="sec">Posicionamento Recomendado</div>
{% for p in posicionamento_txt %}<p class="prose">{{ p }}</p>{% endfor %}{% endif %}

{% if novas_unidades %}
<div class="sec">Novas Unidades (90 dias)</div>
<div class="timing">
  <div class="c"><div class="kpi-t">Aberturas no município</div><div class="kpi-n" style="font-size:15pt;">{{ novas_unidades.total }}</div></div>
  <div class="c"><div class="kpi-t">Janela</div><div class="kpi-n" style="font-size:13pt; padding-top:2px;">{{ novas_unidades.dias }} dias</div></div>
  <div class="c"><div class="kpi-t">Cidade</div><div class="kpi-n" style="font-size:12pt; padding-top:3px;">{{ novas_unidades.cidade }}</div></div>
</div>
<div class="timing-d">Aberturas de CNPJ fitness (RFB) nos últimos {{ novas_unidades.dias }} dias — sinal de aquecimento/entrada de concorrência no município. <em>Fonte: RFB CNPJ Aberto.</em></div>{% endif %}

{% if obras %}
<div class="sec">Obras Fitness em Andamento (CNO)</div>
<table class="d"><tr><th>Obra</th><th>Bairro</th><th>Área (m²)</th><th>Início</th></tr>
{% for o in obras %}<tr><td>{{ o.nome }}</td><td>{{ o.bairro }}</td><td>{{ o.area }}</td><td>{{ o.inicio }}</td></tr>{% endfor %}
</table>
<div class="note">Obras de academias registradas no Cadastro Nacional de Obras (RFB) — concorrência futura em construção. Fonte: CNO/RFB.</div>{% endif %}

{% if demanda %}
<div class="sec">Janela de Entrada (Demanda Futura Datada)</div>
{% if demanda.janela_quente_n %}<div class="alert" style="background:#FFFBEB; border-color:#FCD34D; margin-bottom:10px;">
  <div style="font-weight:bold; color:#92400E; font-size:9.5pt; margin-bottom:4px;">🔥 Janela quente — {{ demanda.janela_quente_n }} obra(s) na reta final</div>
  <div style="font-size:8.5pt; color:#78350F; line-height:1.5;">Obra em acabamento/entrega iminente. <strong>Contate a construtora/corretor AGORA</strong> para ação de marketing e capte os futuros moradores antes da concorrência.{% for j in demanda.janelas %}<br>&bull; <strong>{{ j.nome }}</strong>{% if j.total %} — obra {{ j.total }}%{% endif %}{% if j.acabamento %} · acabamento {{ j.acabamento }}%{% endif %} · ~{{ j.captura }} alunos captáveis{% if j.responsavel %}<br>&nbsp;&nbsp;&nbsp;↳ <strong>Contate:</strong> {{ j.responsavel }}{% if j.contato %} · {{ j.contato }}{% endif %}{% endif %}{% endfor %}</div>
</div>{% endif %}
<div class="timing">
  <div class="c"><div class="kpi-t">Obras residenciais (T+24)</div><div class="kpi-n" style="font-size:15pt;">{{ demanda.n }}</div></div>
  <div class="c"><div class="kpi-t">Captura estimada</div><div class="kpi-n" style="font-size:15pt;">~{{ demanda.captura }} alunos</div></div>
  <div class="c"><div class="kpi-t">Receita/mês T+24</div><div class="kpi-n" style="font-size:13pt; padding-top:2px;">R$ {{ demanda.receita }}</div></div>
</div>
<div class="timing-d"><strong>Diretriz de timing:</strong> {{ demanda.moradores }} novos moradores em obra. Upside captável com marketing, sem CAPEX extra. <em>Fonte: CNO/RFB + IBGE Censo 2022.</em></div>
{% if demanda.obras %}
<table class="d" style="margin-top:10px;"><tr><th>Empreendimento</th><th>Unidades</th><th>Fonte</th><th>Planta</th><th>Entrega</th><th>Fitness</th><th>Moradores</th><th>Leads</th><th>Receita/mês</th></tr>
{% for o in demanda.obras %}<tr><td>{{ o.nome }}{% if o.quente %} <span class="pill mid">reta final</span>{% endif %}</td><td>{{ o.unidades }}</td><td>{% if o.real %}<span class="pill ok">real</span>{% else %}<span class="pill no">proxy</span>{% endif %}</td><td>{{ o.area }}</td><td>{{ o.entrega }}</td><td>{{ '✓' if o.fitness else '—' }}</td><td>{{ o.moradores }}</td><td>~{{ o.captura }}</td><td>R$ {{ o.receita }}</td></tr>{% endfor %}
<tr class="rec"><td>Total (residenciais)</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>{{ demanda.moradores }}</td><td>~{{ demanda.captura }}</td><td>R$ {{ demanda.receita }}</td></tr>
</table>
<div class="note">Cadeia: moradores (área-média ÷ m²/morador, clamp teto IBGE) → leads = moradores × penetração fitness × market share → receita/mês. Unidades <strong>real</strong> = página do lançamento; <strong>proxy</strong> = área÷m².</div>{% endif %}{% endif %}

{% if bairros_viz %}
<div class="sec">Bairros Vizinhos Recomendados</div>
<table class="d"><tr><th>Bairro</th><th>Concorrentes</th><th>Prioridade</th><th>Por quê</th></tr>
{% for b in bairros_viz %}<tr><td><strong>{{ b.bairro }}</strong></td><td>{{ b.concorrentes }}</td><td>{% if b.prioridade %}<span class="pill {{ b.prio_cls }}">{{ b.prioridade }}</span>{% else %}—{% endif %}</td><td style="font-size:8pt;">{{ b.motivo }}</td></tr>{% endfor %}
</table>
<div class="note">Praças alternativas no mesmo município com perfil de público similar e menor disputa — opções caso o bairro-alvo esteja saturado ou sem imóvel.</div>{% endif %}

{% if candidatos %}
<div class="sec">Top Candidatos (Imóveis)</div>
{% if candidatos_algum_fora %}<div class="note" style="background:#FEF2F2; border:1px solid #FECACA; border-radius:5px; padding:8px 12px; color:#7F1D1D; margin-bottom:6px;">⚠ Imóveis marcados <strong>(fora)</strong> estão em bairro/cidade vizinha — o GeoScout não achou vago em {{ bairro }}. O referencial de viabilidade (demografia, concorrência, aluguel) é de <strong>{{ bairro }}</strong> e independe do imóvel; trate-os como ponto de partida físico, não como o veredito do bairro.</div>{% endif %}
<table class="d"><tr><th>#</th><th>Nome</th><th>Tipo</th><th>Local</th><th>Geo</th><th>Ancor.</th><th>Endereço</th></tr>
{% for c in candidatos %}<tr><td>{{ c.pos }}</td><td>{{ c.nome }}</td><td>{{ c.tipo }}</td><td>{% if c.fora %}<span class="pill no">fora</span>{% else %}<span class="pill ok">bairro</span>{% endif %}</td><td>{{ c.geo }}</td><td>{{ c.ancor }}</td><td style="font-size:8pt;">{{ c.endereco }}</td></tr>{% endfor %}
</table>{% endif %}

{% if alertas %}
<div class="sec">Alertas e Ressalvas</div>
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


def _norm_txt(s: str) -> str:
    """Normaliza p/ comparação tolerante a acento/caixa (bairro vs endereço)."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _mc_money(v, sufixo: str = "") -> str | None:
    """Valor de market_context: se for número cru ('35.71'), formata 'R$ 35,71'+sufixo;
    se já vier com texto/unidade, devolve como está. None/'' → None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if re.fullmatch(r"\d+(?:[.,]\d+)?", s):
        try:
            n = float(s.replace(",", "."))
            corpo = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if n % 1 else f"{int(n):,}".replace(",", ".")
            return f"R$ {corpo}{sufixo}"
        except ValueError:
            return s
    return s


def _viab_cls(v: str) -> str:
    v = (v or "").upper()
    if "INVI" in v:
        return "no"
    if v in ("ALTO", "ALTA", "OK"):
        return "ok"
    return "mid"


def _prio_cls(v: str) -> str:
    v = (v or "").upper()
    if "ALTA" in v:
        return "ok"
    if "BAIXA" in v:
        return "no"
    return "mid"


def _limpar_md(texto: str | None, max_paragrafos: int = 3) -> list[str]:
    """Markdown do A6 → parágrafos de texto plano (tira #, **, listas, links)."""
    if not texto or not str(texto).strip():
        return []
    t = str(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)          # **bold** → bold
    t = re.sub(r"`([^`]+)`", r"\1", t)               # `code`
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)   # [txt](url) → txt
    for pat, repl in _RESUMO_FIELDNAMES.items():     # field-name cru → termo legível
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    paras = []
    for bloco in re.split(r"\n\s*\n", t):
        linha = " ".join(
            l.strip().lstrip("#").lstrip("-").lstrip("*").strip()
            for l in bloco.splitlines()
        ).strip()
        if linha:
            paras.append(linha)
        if len(paras) >= max_paragrafos:
            break
    return paras


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


def _gaps_rich(pos: dict) -> list[dict]:
    """gaps_identificados pode ser list[str] OU list[{gap, descricao, potencial_ticket, ...}]."""
    out = []
    for g in (pos.get("gaps_identificados") or [])[:6]:
        if isinstance(g, dict):
            out.append({
                "titulo": str(g.get("gap") or g.get("titulo") or g.get("nome") or "").strip(),
                "desc": str(g.get("descricao") or "").strip() or None,
                "potencial": str(g.get("potencial_ticket") or g.get("potencial") or "").strip() or None,
                "dificuldade": str(g.get("dificuldade_implementacao") or g.get("dificuldade") or "").strip() or None,
            })
        elif str(g).strip():
            out.append({"titulo": str(g).strip(), "desc": None, "potencial": None, "dificuldade": None})
    return [g for g in out if g["titulo"]]


def _aneis(a: dict) -> dict | None:
    if not isinstance(a, dict):
        return None
    pa = a.get("por_anel") or {}
    porte = a.get("no_bairro_por_porte") or {}
    portes_txt = ", ".join(f"{v} {k}" for k, v in porte.items() if v) if isinstance(porte, dict) else ""
    cc = a.get("cross_check") if isinstance(a.get("cross_check"), dict) else None
    cross = None
    if cc and cc.get("status") == "ok":
        cross = {
            "google_n": cc.get("google_n"), "gated_n": cc.get("gated_n"),
            "deep_n": cc.get("ja_no_set_n"), "novos_n": len(cc.get("novos") or []),
            "lista": [{
                "nome": str(x.get("nome") or "—")[:32],
                "rating": x.get("rating") if x.get("rating") is not None else "—",
                "aval": _int(x.get("num_avaliacoes")) if x.get("num_avaliacoes") else "—",
                "status": "analisado" if x.get("deep") else "mapeado",
            } for x in (cc.get("no_bairro") or [])[:12]],
        }
    return {
        "no_bairro": pa.get("NO_BAIRRO", a.get("concorrentes_no_bairro", "—")),
        "fronteira": pa.get("FRONTEIRA", "—"),
        "regional": pa.get("REGIONAL", "—"),
        "score": (f"{float(a['score_competitivo_ponderado']):.1f}"
                  if a.get("score_competitivo_ponderado") is not None else "—"),
        "portes": portes_txt or None,
        "cross": cross,
    }


def _cobertura(c: dict) -> dict | None:
    if not isinstance(c, dict):
        return None
    cobertas = [str(r) for r in (c.get("redes_cobertas") or [])]
    solicitadas = [str(r) for r in (c.get("redes_solicitadas") or [])]
    if not cobertas and not solicitadas:
        return None
    faltantes = [r for r in solicitadas if r not in cobertas]
    return {
        "cobertas": cobertas, "faltantes": faltantes,
        "solicitadas": len(solicitadas) or len(cobertas),
        "fantasma": bool(c.get("tem_redes_fantasma")),
    }


def _obras(o: dict) -> list[dict]:
    obras = (o or {}).get("obras") if isinstance(o, dict) else None
    if not isinstance(obras, list):
        return []
    rows = []
    for ob in obras[:8]:
        if not isinstance(ob, dict):
            continue
        rows.append({
            "nome": str(ob.get("nome_obra") or "—")[:34],
            "bairro": str(ob.get("bairro") or "—")[:18],
            "area": _brl(ob.get("area_m2")) if ob.get("area_m2") else "—",
            "inicio": str(ob.get("data_inicio") or "—")[:10],
        })
    return rows


_ALERTA_RUIDO = (
    "churn_pct", "capex_por_unidade", "cvm itr", "overlay ri", "ri overlay",
    "preencher ri", "parcial (50%)", "parcial (",
    # Ruído interno de benchmark/sanity: o sistema já caiu no fallback correto.
    "fora da banda", "smft3", "ebitda smart fit", "margem ebitda",
)

# Field-names crus que a prosa do LLM às vezes vaza no resumo (ex.: 'score_concorrencia
# de 0.0'). Trocar por termo legível — não expor nome de campo interno ao cliente.
_RESUMO_FIELDNAMES = {
    r"\bscore_concorrencia\b": "competitividade",
    r"\bscore_demografico\b": "perfil demográfico",
    r"\bscore_viabilidade\b": "viabilidade",
    r"\bscore_bairro\b": "score do bairro",
    r"\bnivel_saturacao\b": "saturação",
    r"\bmarket_share\b": "fatia de mercado",
}


def _filtrar_alertas(alertas) -> list[str]:
    """Tira ruído interno de cobertura de dado (gaps regulatórios CVM/RI, placeholders
    churn_pct/capex_por_unidade) — não é alerta de negócio pro cliente."""
    out = []
    for a in (alertas or []):
        s = str(a).strip()
        if not s:
            continue
        if any(t in s.lower() for t in _ALERTA_RUIDO):
            continue
        out.append(s)
    return out


def _dores_quadro(dores_cons) -> list[dict] | None:
    """Quadro de dores consolidadas: categoria + menções + academias (sem texto literal)."""
    if not isinstance(dores_cons, list) or not dores_cons:
        return None
    out = []
    for d in dores_cons:
        if not isinstance(d, dict) or not d.get("categoria"):
            continue
        acs = d.get("academias") or []
        out.append({
            "categoria": str(d.get("categoria")).replace("_", " ").capitalize(),
            "mencoes": d.get("mencoes"),
            "academias": ", ".join(
                f"{str(a.get('nome') or '')[:16]} (×{a.get('vezes')})"
                for a in acs[:4] if isinstance(a, dict)
            ) or "—",
        })
    return out or None


def _limpar_bairro(b: str | None) -> str:
    """'Lojas 2/3/12/13 - Cocó' → 'Cocó'. Tira prefixo de loja/sala/quadra/lote do
    endereço que o parser às vezes deixa no campo bairro."""
    s = str(b or "").strip()
    if not s:
        return "—"
    # se houver ' - ', o bairro real costuma ser o ÚLTIMO segmento
    if " - " in s:
        s = s.split(" - ")[-1].strip()
    s = re.sub(r"(?i)^(lojas?|salas?|quadra|lote|bloco|s/n)\b[\s\d/.,-]*", "", s).strip()
    return s or "—"


def _preco_num(v) -> float | None:
    """'R$ 129,90' → 129.9. None se não parsear."""
    if v is None:
        return None
    s = re.sub(r"[^\d,.]", "", str(v))
    if not s:
        return None
    # pt-BR: vírgula decimal; ponto de milhar
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None


def _ticket_segmentos(competidores) -> list[dict] | None:
    """Quadro ticket × segmento × SERVIÇOS entregues por plano (dado de posicionamento).
    Bandas por TERTIL dos preços reais coletados (market-derived, recalibrável, sem
    hardcode). Cada segmento agrega os serviços (inclui dos planos) — mostra o que se
    entrega em cada faixa de ticket."""
    planos = []
    for c in (competidores or []):
        for p in (getattr(c, "planos_precos", None) or []):
            if not isinstance(p, dict):
                continue
            preco = _preco_num(p.get("preco_mensal"))
            if preco and preco > 0:
                planos.append((preco, p.get("inclui") or [], c.nome, p.get("plano")))
    if len(planos) < 2:
        return None
    precos = sorted(pp[0] for pp in planos)
    n = len(precos)
    t1, t2 = precos[max(0, n // 3 - 1)], precos[min(n - 1, 2 * n // 3)]
    segs: dict[str, list] = {"Econômico": [], "Intermediário": [], "Premium": []}
    for preco, inclui, nome, _plano in planos:
        k = "Econômico" if preco <= t1 else ("Premium" if preco > t2 else "Intermediário")
        segs[k].append((preco, inclui, nome))
    from tools.catalogos import normalizar_servicos

    rows = []
    for k, items in segs.items():
        if not items:
            continue
        ps = [i[0] for i in items]
        # Serviços = CATEGORIAS limpas do catálogo (não a prosa de marketing do `inclui`).
        textos = []
        for _, inc, _ in items:
            textos.extend(str(x) for x in (inc or []))
        svc = normalizar_servicos(textos)
        faixa = f"R$ {_brl(min(ps))}" if min(ps) == max(ps) else f"R$ {_brl(min(ps))}–{_brl(max(ps))}"
        rows.append({
            "segmento": k, "faixa": faixa, "n": len(items),
            "academias": ", ".join(sorted({i[2][:18] for i in items}))[:40],
            "servicos": ", ".join(svc[:6]) or "—",
        })
    return rows or None


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
    veredito_oceano = meta.get("veredito_oceano")
    voc = _VEREDITO_COR.get(str(veredito_oceano or "").upper().strip(), "#0E5C66")

    mkt = model.market
    mercado = None
    if mkt is not None:
        mercado = {
            "ticket": _mc_money(mkt.ticket_mercado), "aluguel": _mc_money(mkt.aluguel_m2, sufixo="/m²"),
            "renda": _mc_money(mkt.renda), "tendencia": mkt.tendencia,
            "parque": _int(mkt.parque_ativo) if mkt.parque_ativo else None,
            "novos": mkt.novos_cnpj_90d,
        }

    pano = meta.get("panorama") if isinstance(meta.get("panorama"), dict) else None
    panorama = None
    if pano:
        panorama = {
            "saturacao": pano.get("saturacao"),
            "rating_medio": f"{float(pano['rating_medio']):.1f}" if pano.get("rating_medio") else None,
            "total": pano.get("total"), "raio": pano.get("raio"),
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

    # Scores 3-dim (model.scores: Demográfico/Competitivo/Viabilidade)
    sc_map = {s.label.lower(): s.value for s in (model.scores or []) if s.value is not None}
    scores_dim = None
    if sc_map:
        def _s(k):
            v = sc_map.get(k)
            return f"{v:.1f}" if isinstance(v, (int, float)) else "—"
        if any(k in sc_map for k in ("demográfico", "competitivo", "viabilidade")):
            scores_dim = {"demografico": _s("demográfico"), "competitivo": _s("competitivo"), "viabilidade": _s("viabilidade")}

    cenarios = []
    rec_norm = (model.modelo_recomendado or "").strip().lower()
    mid_cen = rec_cen = None
    for c in (model.cenarios or []):
        # Não marcar ★/recomendado num cenário INVIÁVEL (contradição que o usuário pegou:
        # 'Premium ★ ... INVIAVEL'). Recomendado só se bate o modelo E é viável.
        is_rec = (bool(rec_norm)
                  and ((c.modelo or "").lower() == rec_norm or (c.label or "").lower() == rec_norm)
                  and "INVI" not in (c.viabilidade or "").upper())
        cenarios.append({
            "modelo": c.label or c.modelo, "ticket": f"R$ {_brl(c.ticket_medio)}",
            "receita": f"R$ {_brl(c.receita_mensal)}" if c.receita_mensal else "—",
            "lucro": f"R$ {_brl(c.lucro_mensal)}" if c.lucro_mensal is not None else "—",
            "margem": f"{c.margem_pct:.0f}%" if c.margem_pct is not None else "—",
            "payback": f"{c.payback_meses}m" if c.payback_meses else "—",
            "alunos": _int(c.matriculas_realista) if c.matriculas_realista else "—",
            "viab": c.viabilidade or "—", "viab_cls": _viab_cls(c.viabilidade or ""),
            "recomendado": is_rec,
        })
        if (c.modelo or "").lower() == "mid":
            mid_cen = c
        if is_rec:
            rec_cen = c

    # Ticket: prioriza pos.ticket (A9); fallback pro ticket do cenário recomendado
    # (senão "— /mês" quando A9 não emitiu banda). Banda = low↔premium dos cenários.
    if ticket_rec is None:
        base_cen = rec_cen or mid_cen
        if base_cen is not None and base_cen.ticket_medio:
            ticket_rec = f"R$ {_brl(base_cen.ticket_medio)}"
            ticks = sorted(c.ticket_medio for c in (model.cenarios or []) if c.ticket_medio)
            if len(ticks) >= 2 and ticks[0] != ticks[-1]:
                ticket_banda = f"R$ {_brl(ticks[0])} a R$ {_brl(ticks[-1])}"
    # KPI strip financeiro: área + aluguel + capex/payback do cenário mid
    kpi_fin = None
    if mid_cen is not None or model.aluguel_mensal:
        kpi_fin = {
            "area": f"{model.area_m2_min}–{model.area_m2_max}",
            "aluguel": _brl(model.aluguel_mensal) if model.aluguel_mensal else None,
            "capex": _brl(mid_cen.capex_total) if mid_cen and mid_cen.capex_total else None,
            "payback": f"{mid_cen.payback_meses}m" if mid_cen and mid_cen.payback_meses else None,
        }
    # Capex breakdown do cenário recomendado (ou mid)
    capex = None
    cap_cen = next((c for c in (model.cenarios or [])
                    if (c.modelo or "").lower() == rec_norm or (c.label or "").lower() == rec_norm), mid_cen)
    if cap_cen is not None:
        itens_raw = [
            ("Obra/adaptação", cap_cen.capex_obra),
            ("Equipamentos", cap_cen.capex_equipamentos),
            ("Contingência", cap_cen.capex_contingencia),
        ]
        itens_raw = [(lab, float(v)) for lab, v in itens_raw if v]
        tot = sum(v for _, v in itens_raw)
        if tot > 0:
            capex = {
                "modelo": cap_cen.label or cap_cen.modelo,
                "itens": [{"label": lab, "valor": _brl(v), "pct": round(100 * v / tot)} for lab, v in itens_raw],
            }

    competidores = [{
        "nome": c.nome[:38], "rating": c.rating if c.rating is not None else "—",
        "aval": _int(c.num_avaliacoes) if c.num_avaliacoes else "—",
        "bairro": _limpar_bairro(c.bairro), "h24": "sim" if c.tem_24h else "—",
    } for c in (model.competidores or [])]

    # Quadro planos × preços da concorrência (SearchAPI). Só com dado real.
    planos = []
    for c in (model.competidores or []):
        for p in (c.planos_precos or [])[:2]:
            if isinstance(p, dict) and p.get("preco_mensal"):
                inclui = p.get("inclui") or []
                planos.append({
                    "academia": (c.nome or "—")[:24],
                    "plano": str(p.get("plano") or "—")[:24],
                    "preco": str(p.get("preco_mensal") or "—")[:14],
                    "fidelidade": str(p.get("fidelidade") or "—")[:16],
                    "inclui": ", ".join(str(x) for x in inclui[:2])[:46] if isinstance(inclui, list) else "—",
                })

    # Candidato fora do bairro/cidade-alvo: GeoScout às vezes devolve imóvel de outra
    # praça (sem vago no bairro). Flag espelha o aviso da UI — o referencial de
    # viabilidade é do bairro-alvo; o imóvel é só ponto de partida físico.
    _alvo_b = _norm_txt(model.bairro)
    candidatos = []
    algum_fora = False
    for c in (model.candidatos or []):
        end_norm = _norm_txt(c.endereco or "")
        # Espelha a UI: fora = bairro-alvo não aparece no endereço (mesmo na mesma cidade).
        fora = bool(_alvo_b) and _alvo_b not in end_norm
        if fora:
            algum_fora = True
        candidatos.append({
            "pos": c.posicao, "nome": c.nome[:34], "tipo": (c.tipo_imovel_label or "—")[:18],
            "geo": f"{c.score_geoscout:.1f}" if c.score_geoscout is not None else "—",
            "ancor": f"{c.score_ancoragem:.1f}" if c.score_ancoragem is not None else "—",
            "endereco": (c.endereco or "—")[:60], "fora": fora,
        })

    bairros_viz = [{
        "bairro": b.bairro or "—",
        "concorrentes": b.concorrentes if b.concorrentes is not None else "—",
        "prioridade": b.prioridade, "prio_cls": _prio_cls(b.prioridade or ""),
        "motivo": (b.motivo or "—")[:120],
    } for b in (model.bairros_alternativos or []) if b.bairro]

    demanda = None
    df = meta.get("demanda_futura")
    if isinstance(df, dict) and df.get("status") == "ok" and (df.get("provavel_residencial_n") or 0) > 0:
        # Ficha por obra (A) — top empreendimentos residenciais com dado real.
        obras_ficha = []
        for ob in (df.get("obras") or []):
            if not isinstance(ob, dict) or not ob.get("provavel_residencial"):
                continue
            obras_ficha.append({
                "nome": str(ob.get("empreendimento") or ob.get("construtora") or "—")[:28],
                "unidades": _int(ob.get("unidades_est")),
                "real": (ob.get("unidades_fonte") == "lancamento_exato"),
                "area": f"{ob.get('area_privativa_media')} m²" if ob.get("area_privativa_media") else "—",
                "entrega": str(ob.get("entrega") or "—")[:7],
                "fitness": bool(ob.get("amenidade_fitness")),
                "moradores": _int(ob.get("moradores_est")) if ob.get("moradores_est") else "—",
                "captura": (round(float(ob.get("captura_est"))) if ob.get("captura_est") else "—"),
                "receita": _brl(ob.get("receita_mensal_est")) if ob.get("receita_mensal_est") else "—",
                "quente": bool(ob.get("janela_quente")),
            })
        # Janela quente (C) — obras na reta final → diretriz de contato/MKT.
        janelas = []
        for j in (df.get("janelas_quentes") or []):
            if not isinstance(j, dict):
                continue
            prog = j.get("obra_progresso") or {}
            resp = j.get("responsavel") or {}
            janelas.append({
                "nome": str(j.get("empreendimento") or "—")[:34],
                "total": prog.get("total_pct"), "acabamento": prog.get("acabamento_pct"),
                "captura": _int(j.get("captura_est")) if j.get("captura_est") else "—",
                "responsavel": (resp.get("responsavel_parceria") or "")[:40] or None,
                "contato": (resp.get("contato") or "")[:30] or None,
            })
        demanda = {
            "n": int(df.get("provavel_residencial_n") or 0),
            "captura": int(float(df.get("captura_total_est") or 0)),
            "receita": _brl(df.get("receita_total_mensal_est")),
            "moradores": _brl(df.get("moradores_total_est")),
            "obras": obras_ficha[:6],
            "janela_quente_n": int(df.get("janela_quente_n") or 0),
            "janelas": janelas[:4],
        }

    # Novas unidades 90d
    ent = meta.get("entrantes_cnpj_90d")
    novas_unidades = None
    if isinstance(ent, dict) and (ent.get("total") or 0) > 0:
        novas_unidades = {
            "total": _int(ent.get("total")), "dias": ent.get("dias") or 90,
            "cidade": str(ent.get("cidade") or "—")[:20],
        }

    return {
        "bairro": model.bairro, "cidade": model.cidade, "uf": model.uf,
        "tipo": (model.tipo_negocio or "").replace("_", " "),
        "area": f"{model.area_m2_min}–{model.area_m2_max} m²",
        "data": model.data_execucao or "—", "ref": (model.relatorio_id or "")[:8],
        "rodape": "Confidencial · GymSite Intelligence · valores estimados (validar em due diligence)",
        "veredito": str(veredito).upper() if veredito else None,
        "veredito_oceano": str(veredito_oceano).upper().replace("_", " ") if veredito_oceano else None,
        "justificativa": pos.get("justificativa_recomendacao") or pos.get("justificativa"),
        "vc": vc, "voc": voc, "errc": errc, "modelo_recomendado": model.modelo_recomendado,
        "gaps": _gaps_rich(pos),
        "ticket_rec": ticket_rec, "ticket_banda": ticket_banda,
        "benchmarks": [c["nome"][:26] + (f" ({c['bairro']})" if c["bairro"] != "—" else "") for c in competidores[:4]],
        "resumo": _limpar_md(model.resumo_executivo),
        "posicionamento_txt": _limpar_md(model.posicionamento),
        "scores_dim": scores_dim,
        "scores": {
            "bairro": f"{model.score_bairro:.1f}" if model.score_bairro is not None else "—",
            "top1": f"{model.score_top1:.1f}" if model.score_top1 is not None else "—",
            "saturacao": model.nivel_saturacao or "—",
            "concorrentes": model.total_concorrentes if model.total_concorrentes is not None else "—",
        },
        "mercado": mercado, "panorama": panorama, "demografia": demografia,
        "cenarios": cenarios, "kpi_fin": kpi_fin, "capex": capex,
        "competidores": competidores, "planos": planos[:12],
        "ticket_segmentos": _ticket_segmentos(model.competidores),
        "dores_quadro": _dores_quadro(meta.get("dores_consolidadas")), "pico": meta.get("pico"),
        "aneis": _aneis(meta.get("aneis_competitivos")),
        "cobertura": _cobertura(meta.get("cobertura_redes_a0")),
        "obras": _obras(meta.get("obras_cno_em_curso")),
        "novas_unidades": novas_unidades,
        "candidatos": candidatos, "candidatos_algum_fora": algum_fora,
        "bairros_viz": bairros_viz, "demanda": demanda,
        "alertas": _filtrar_alertas(model.alertas)[:12],
    }


# Emoji/símbolos: PDF de produção NÃO leva emoji (regra). Funcionais viram texto;
# o resto (⚠ 🔥 e pictográficos) é removido.
_SUBST_SIMBOLO = {
    "♀": "F", "♂": "M", "✓": "Sim", "✗": "—", "★": " (recom.)", "↳": "->",
    "🔥": "", "⚠": "", "⚠️": "",
}
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U00002190-\U000021FF]"
)


def _sem_emoji(html: str) -> str:
    for k, v in _SUBST_SIMBOLO.items():
        html = html.replace(k, v)
    return _EMOJI_RE.sub("", html)


def gerar_html(model: RelatorioPdfModel) -> str:
    """HTML do relatório completo (testável sem WeasyPrint). Sem emoji (regra PDF)."""
    from jinja2 import Template

    return _sem_emoji(Template(_TEMPLATE).render(**_contexto(model)))


def gerar_pdf_weasy(model: RelatorioPdfModel) -> bytes:
    """HTML → PDF via WeasyPrint. Precisa libs de sistema (Dockerfile)."""
    from weasyprint import HTML

    return HTML(string=gerar_html(model), base_url=_ASSETS).write_pdf()
