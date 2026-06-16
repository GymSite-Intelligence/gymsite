"""
A8 — Validador Cruzado (pós-A6).

Validação determinística + corroboração opcional via OpenClaw (kimi_search).
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

from tools.parametros_metodologia import param


@dataclass
class Claim:
    categoria: str
    texto: str
    valor: Optional[str]
    fonte_no_relatorio: str
    severidade: str


@dataclass
class AlertaValidacao:
    tipo: str
    claim_relacionada: str
    descricao: str
    recomendacao: str
    severidade: str


def _state_to_dict(state: Any) -> dict[str, Any]:
    """Converte o State do ADK (ou dict) em dict puro.

    Desde ~2026-05-29 o runner entrega google.adk.sessions.State em vez de
    dict; dict(State) cai no protocolo de sequência (state[0] → KeyError: 0)
    e derrubava o A8 silenciosamente — validacoes vazia desde então."""
    if isinstance(state, dict):
        return dict(state)
    if state is None:
        return {}
    to_dict = getattr(state, "to_dict", None)
    if callable(to_dict):
        try:
            d = to_dict()
            if isinstance(d, dict):
                return dict(d)
        except Exception:
            pass
    value = getattr(state, "_value", None)
    if isinstance(value, dict):
        return dict(value)
    try:
        return dict(state)
    except Exception:
        return {}


def _normalize_state(state: dict[str, Any], relatorio: dict[str, Any] | None) -> dict[str, Any]:
    """Unifica keys do ADK state + JSON canônico do A6."""
    out = _state_to_dict(state)
    rel = relatorio or {}
    oc = rel.get("output_consolidado") if isinstance(rel.get("output_consolidado"), dict) else {}
    if not oc and isinstance(out.get("output_consolidado"), dict):
        oc = out["output_consolidado"]

    scores = oc.get("scores") or oc.get("scores_regiao") or {}
    if isinstance(scores, dict):
        out.setdefault("score_bairro", oc.get("score_bairro") or scores.get("score_bairro"))
        out.setdefault("score_concorrencia", scores.get("competitivo") or scores.get("concorrencia"))
        out.setdefault("score_demografico", scores.get("demografico"))
        out.setdefault("score_viabilidade", scores.get("viabilidade"))

    out.setdefault("score_bairro", oc.get("score_bairro"))
    out.setdefault("veredito", oc.get("veredito"))
    out.setdefault("posicionamento_recomendado", oc.get("posicionamento_recomendado"))
    out.setdefault("resumo_executivo", oc.get("resumo_executivo"))
    out.setdefault("total_concorrentes_analisados", oc.get("total_concorrentes_analisados"))
    out.setdefault("bairros_alternativos", oc.get("bairros_alternativos") or [])
    out.setdefault("top_3_candidatos", oc.get("top_3_candidatos") or oc.get("candidatos") or [])
    out.setdefault("cobertura_redes_a0", oc.get("cobertura_redes_a0") or rel.get("cobertura_redes_a0") or {})
    out.setdefault("cenarios_financeiros", rel.get("cenarios") or oc.get("cenarios_financeiros") or [])
    out.setdefault("score_geral", out.get("score_bairro") or oc.get("score_bairro") or 0)
    return out


class A8ValidadorCruzado:
    def __init__(self) -> None:
        self.alertas: list[AlertaValidacao] = []
        self.fontes_independentes: list[str] = []

    async def validar(
        self,
        relatorio_markdown: str,
        state_json: dict[str, Any],
        *,
        relatorio: dict[str, Any] | None = None,
        custo_brl: Optional[float] = None,
    ) -> dict[str, Any]:
        self.alertas = []
        self.fontes_independentes = []
        state = _normalize_state(state_json, relatorio)
        md = relatorio_markdown or ""

        claims = self._extrair_claims(md, state)
        self._validar_coerencia_financeira(claims, state)
        self._validar_coerencia_demografica(claims, state)
        self._validar_coerencia_competitiva(claims, state)
        self._validar_dados_operacionais(md, state)
        self._validar_redes_fantasma(state)
        await self._validar_fontes_externas(claims)
        self._validar_veredito(md, claims, state)
        self._validar_narrativa_vs_financeiro(md, state)
        self._validar_evidencia_oportunidade(state)

        score_validacao = self._calcular_score_validacao()
        return {
            "validacao_id": f"val_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status_validacao": self._status_final(),
            "score_validacao": round(score_validacao, 2),
            "alertas": [asdict(a) for a in self.alertas],
            "claims_verificadas": len(claims),
            "claims_com_alertas": len(
                [a for a in self.alertas if a.severidade in ("CRITICO", "ALTA")]
            ),
            "fontes_independentes": list(dict.fromkeys(self.fontes_independentes)),
            "resumo_executivo_validacao": self._gerar_resumo_validacao(),
            "revisar_manual": any(a.severidade == "CRITICO" for a in self.alertas),
            "a0_research_provider": self._research_provider_label(),
            "custo_brl": custo_brl,
        }

    def _research_provider_label(self) -> str:
        try:
            from tools.research_provider import get_a0_research_provider

            return get_a0_research_provider()
        except Exception:
            return os.getenv("A0_RESEARCH_PROVIDER", "gemini")

    def _extrair_claims(self, md: str, state: dict) -> list[Claim]:
        claims: list[Claim] = []
        patterns = [
            (r"aluguel (?:estimado|mediano).*?R\$\s*([\d\.]+(?:,\d+)?)", "financeiro", "aluguel"),
            (r"payback.*?([\d\.]+)\s*meses", "financeiro", "payback"),
            (r"break[- ]?even.*?([\d\.]+)\s*meses", "financeiro", "breakeven"),
            (r"CAPEX.*?R\$\s*([\d\.]+(?:,\d+)?)", "financeiro", "capex"),
            (r"(\d+[\d\.]*)\s*habitantes", "demografico", "populacao"),
            (r"(\d+)\s*concorrentes", "competitivo", "num_concorrentes"),
            (r"satura[cç][aã]o.*?([\d\.]+)\s*%", "competitivo", "saturacao"),
        ]
        for pattern, cat, sub in patterns:
            for match in re.finditer(pattern, md, re.IGNORECASE):
                claims.append(
                    Claim(
                        categoria=cat,
                        texto=match.group(0),
                        valor=match.group(1) if match.groups() else None,
                        fonte_no_relatorio="relatorio_md",
                        severidade="alta" if sub in ("payback", "num_concorrentes") else "media",
                    )
                )

        n_conc = state.get("total_concorrentes_analisados")
        if n_conc is not None:
            claims.append(
                Claim(
                    categoria="competitivo",
                    texto=f"{n_conc} concorrentes analisados (state)",
                    valor=str(n_conc),
                    fonte_no_relatorio="output_consolidado",
                    severidade="alta",
                )
            )
        return claims

    def _validar_coerencia_financeira(self, claims: list[Claim], state: dict) -> None:
        payback = self._extrair_valor(claims, "payback")
        breakeven = self._extrair_valor(claims, "breakeven")
        if payback and breakeven and payback < breakeven * 0.8:
            self._add(
                "inconsistencia",
                f"Payback {payback}m vs break-even {breakeven}m",
                "Payback menor que 80% do break-even.",
                "Revisar cenários A4.",
                "ALTA",
            )

    def _validar_coerencia_demografica(self, claims: list[Claim], state: dict) -> None:
        pop = self._extrair_valor(claims, "populacao")
        if pop and pop > 500_000:
            self._add(
                "dado_nao_verificavel",
                f"População {pop:,.0f}",
                "População de bairro > 500k é atípica — pode ser dado municipal.",
                "Conferir A2 / fonte IBGE.",
                "MEDIA",
            )

    def _validar_coerencia_competitiva(self, claims: list[Claim], state: dict) -> None:
        n = state.get("total_concorrentes_analisados")
        saturacao = self._extrair_valor(claims, "saturacao")
        if n is not None and saturacao and int(n) < 3 and saturacao > 70:
            self._add(
                "inconsistencia",
                f"{n} concorrentes, saturação {saturacao}%",
                "Poucos concorrentes com saturação alta é inconsistente.",
                "Revisar A3b ou raio de busca.",
                "ALTA",
            )

    def _validar_dados_operacionais(self, md: str, state: dict) -> None:
        veredito = str(state.get("veredito") or "").upper()
        if not veredito and "APROVADO" in md.upper():
            veredito = "APROVADO"
        if not veredito and "REPROVADO" in md.upper():
            veredito = "REPROVADO"

        candidatos = state.get("top_3_candidatos") or []
        n_cand = len(candidatos) if isinstance(candidatos, list) else 0
        n_conc = int(state.get("total_concorrentes_analisados") or 0)

        if veredito == "APROVADO" and n_cand == 0:
            self._add(
                "inconsistencia",
                "APROVADO sem candidatos",
                "Veredito APROVADO com zero candidatos GeoScout.",
                "Rebaixar veredito ou corrigir A1/Maps.",
                "CRITICO",
            )
        if veredito == "APROVADO" and n_conc == 0:
            self._add(
                "dado_nao_verificavel",
                "APROVADO sem concorrentes mapeados",
                "Aprovação sem base competitiva (Maps/OSM/CNPJ vazios).",
                "Exigir rerun com fallback OSM/CNPJ ou INVESTIGAR MAIS.",
                "ALTA",
            )

    def _validar_redes_fantasma(self, state: dict) -> None:
        cob = state.get("cobertura_redes_a0") or {}
        if not isinstance(cob, dict):
            return
        if cob.get("tem_redes_fantasma"):
            redes = cob.get("redes_nao_encontradas") or []
            self._add(
                "dado_nao_verificavel",
                "Redes A0 não confirmadas localmente",
                f"Deep Research citou redes sem match local: {', '.join(redes[:5])}",
                "Usar apenas redes OSM/CNPJ no viewer.",
                "ALTA",
            )

    async def _validar_fontes_externas(self, claims: list[Claim]) -> None:
        if os.getenv("A8_USE_KIMI", "1").lower() in ("0", "false", "no"):
            return
        try:
            from tools.kimi_research import _openclaw_configured, kimi_search
        except ImportError:
            return
        if not _openclaw_configured():
            return

        altas = [c for c in claims if c.severidade == "alta"][:2]

        async def _one(claim: Claim) -> None:
            q = f"Verificar dado mercado fitness Brasil: {claim.texto}"
            try:
                txt = await kimi_search(q)
                self.fontes_independentes.append(txt[:200])
            except Exception as exc:
                self.fontes_independentes.append(f"[kimi_erro] {exc}")

        if altas:
            await asyncio.gather(*[_one(c) for c in altas], return_exceptions=True)

    def _validar_veredito(self, md: str, claims: list[Claim], state: dict) -> None:
        veredito = str(state.get("veredito") or "").upper()
        if not veredito:
            if "INVESTIGAR" in md.upper():
                veredito = "INVESTIGAR MAIS"
            elif "REPROVADO" in md.upper():
                veredito = "REPROVADO"
            elif "APROVADO" in md.upper():
                veredito = "APROVADO"

        score = float(state.get("score_bairro") or state.get("score_geral") or 0)
        if veredito == "APROVADO" and score and score < param("validacao_score_minimo_aprovado"):
            self._add(
                "inconsistencia",
                f"APROVADO com score_bairro {score}",
                "Score regional < 6 com veredito APROVADO.",
                "Alinhar veredito ao score ou revisar pesos A6.",
                "CRITICO",
            )

        score_comp = float(state.get("score_concorrencia") or 0)
        bairros = state.get("bairros_alternativos") or []
        if score_comp and score_comp < param("validacao_score_concorrencia_minimo") and not bairros:
            self._add(
                "inconsistencia",
                "Saturação sem bairros alternativos",
                f"score_concorrencia={score_comp} sem bairros_alternativos.",
                "Forçar bairros alternativos no A6.",
                "ALTA",
            )

    _TERMOS_OTIMISTAS = (
        "oportunidade excepcional",
        "excelente oportunidade",
        "alto potencial",
        "potencial excepcional",
        "oportunidade única",
        "oportunidade unica",
    )
    _MARCADORES_CONDICIONAL = ("apesar", "não fecha", "nao fecha", "inviável", "inviavel", "só se aplica", "so se aplica")

    def _validar_narrativa_vs_financeiro(self, md: str, state: dict) -> None:
        """REPROVADO com posicionamento/resumo vendendo otimismo incondicional
        (caso rpt_1778371974 Meireles: payback 999 + 'oportunidade excepcional')."""
        veredito = str(state.get("veredito") or "").upper()
        if veredito != "REPROVADO":
            return
        texto = " ".join(
            str(state.get(k) or "")
            for k in ("posicionamento_recomendado", "resumo_executivo")
        ).lower()
        if not texto.strip():
            texto = (md or "").lower()
        otimistas = [t for t in self._TERMOS_OTIMISTAS if t in texto]
        condicionado = any(m in texto for m in self._MARCADORES_CONDICIONAL)
        if otimistas and not condicionado:
            self._add(
                "inconsistencia",
                f"REPROVADO com narrativa otimista ('{otimistas[0]}')",
                "Veredito REPROVADO mas posicionamento/resumo vendem otimismo sem condicional financeira — leitor recebe dois vereditos opostos.",
                "Aplicar gate de coerência do A6: posicionamento condicionado à restrição financeira dominante.",
                "ALTA",
            )

    def _validar_evidencia_oportunidade(self, state: dict) -> None:
        """score_oportunidade_mercado >= 9 sustentado por reviews vazios ('Top')."""
        # output_key grava o echo do LLM como STRING no state — parsear pra dict
        # antes de validar, senão o guard isinstance abortava a validação em 100%
        # dos runs (regressão do fix de crash anterior). _parse_market_context
        # tolera str JSON / fence markdown / dict e nunca levanta.
        from tools.competitor_tools import _parse_market_context

        ic_raw = state.get("inteligencia_competitiva")
        ic = ic_raw if isinstance(ic_raw, dict) else _parse_market_context(ic_raw)
        if not isinstance(ic, dict) or not ic:
            return
        inner_raw = ic.get("inteligencia_competitiva")
        inner = inner_raw if isinstance(inner_raw, dict) else ic
        if not isinstance(inner, dict):
            return
        try:
            score = float(inner.get("score_oportunidade_mercado"))
        except (TypeError, ValueError):
            return
        if score < 9:
            return

        informativos = 0
        concorrentes = inner.get("concorrentes_detalhados") or []
        for c in concorrentes if isinstance(concorrentes, list) else []:
            if not isinstance(c, dict):
                continue
            reviews = c.get("reviews_traduzidas") or c.get("reviews") or []
            for r in reviews if isinstance(reviews, list) else []:
                if not isinstance(r, dict):
                    continue
                cat = str(r.get("categoria_dor") or "").strip().lower()
                quote = str(r.get("quote_pt_br") or r.get("quote_curta") or "")
                if cat not in ("", "null", "none") or len(quote) >= 40:
                    informativos += 1
        if informativos < 3:
            self._add(
                "dado_nao_verificavel",
                f"score_oportunidade_mercado={score:g} com {informativos} review(s) informativo(s)",
                "Score de oportunidade máximo sustentado por reviews vazios ('Top') — ausência de dado não é oportunidade.",
                "Coletar mais evidência (reviews, A3c oferta real) ou rebaixar score no A3b.",
                "ALTA",
            )

    def _calcular_score_validacao(self) -> float:
        if not self.alertas:
            return 1.0
        pesos = {
            "CRITICO": param("validacao_peso_critico"),
            "ALTA": param("validacao_peso_alta"),
            "MEDIA": param("validacao_peso_media"),
            "BAIXA": param("validacao_peso_baixa"),
        }
        penalidade = sum(pesos.get(a.severidade, 0) for a in self.alertas)
        return max(0.0, 1.0 - penalidade)

    def _status_final(self) -> str:
        if any(a.severidade == "CRITICO" for a in self.alertas):
            return "REPROVADO_VALIDACAO"
        if any(a.severidade == "ALTA" for a in self.alertas):
            return "APROVADO_COM_RESSALVAS"
        if self.alertas:
            return "APROVADO_MINOR_ISSUES"
        return "APROVADO_LIMPO"

    def _gerar_resumo_validacao(self) -> str:
        if not self.alertas:
            return "Nenhuma inconsistência crítica detectada pelo A8."
        parts = [f"Status: {self._status_final()}. {len(self.alertas)} alerta(s)."]
        for a in self.alertas[:5]:
            parts.append(f"[{a.severidade}] {a.descricao}")
        return " ".join(parts)

    def _add(self, tipo: str, claim: str, desc: str, rec: str, sev: str) -> None:
        self.alertas.append(
            AlertaValidacao(
                tipo=tipo,
                claim_relacionada=claim,
                descricao=desc,
                recomendacao=rec,
                severidade=sev,
            )
        )

    def _extrair_valor(self, claims: list[Claim], subtipo: str) -> Optional[float]:
        for c in claims:
            if subtipo in c.texto.lower() and c.valor:
                try:
                    return float(str(c.valor).replace(".", "").replace(",", "."))
                except ValueError:
                    continue
        return None
