#!/usr/bin/env python3
"""
GymSite A8 — Validador Cruzado (Cross-Checker)
Agente pós-A6 que valida o relatório final, verifica inconsistências
e emite alertas com fontes independentes.

Integração:
  1. Copie para agents/a8_validator.py
  2. Adicione ao SequentialAgent após o A6 (ou chame async pós-pipeline)
  3. Input: output do A6 (relatorio_executivo markdown + JSON state)
  4. Output: validação estruturada que pode ser anexada ao relatório
"""

import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Claim:
    """Uma afirmação extraída do relatório que precisa ser validada."""
    categoria: str           # 'financeiro', 'demografico', 'competitivo', 'geografico'
    texto: str               # afirmação original no relatório
    valor: Optional[str]     # número / dado concreto, se houver
    fonte_no_relatorio: str  # de onde foi extraído (ex: 'A4', 'A2', 'A3b')
    severidade: str          # 'alta' | 'media' | 'baixa' — impacto se estiver errado


@dataclass
class AlertaValidacao:
    """Alerta gerado quando uma claim não passa na validação."""
    tipo: str                # 'inconsistencia' | 'fonte_desatualizada' | 'dado_nao_verificavel' | 'extrapolacao'
    claim_relacionada: str   # texto da claim
    descricao: str           # o que está errado / suspeito
    recomendacao: str        # o que fazer
    severidade: str          # 'CRITICO' | 'ALTA' | 'MEDIA' | 'BAIXA'


class A8ValidadorCruzado:
    """
    Segunda opinião automatizada sobre o relatório do GymSite.
    Não refaz a pesquisa — verifica se os dados internos são coerentes
    e se claims chave podem ser corroboradas por fontes externas.
    """

    def __init__(self):
        self.alertas: List[AlertaValidacao] = []
        self.fontes_independentes: List[str] = []

    async def validar(
        self,
        relatorio_markdown: str,
        state_json: Dict[str, Any],
        custo_brl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Pipeline de validação completo.

        Args:
            relatorio_markdown: texto completo do A6 ReportConsolidator
            state_json: state dump do pipeline (outputs de A0–A5)
            custo_brl: custo real do pipeline (para validar eficiência)

        Returns:
            dict com validação estruturada, pronto para persistir no Supabase
        """
        self.alertas = []
        self.fontes_independentes = []

        # ─── FASE 1: EXTRAÇÃO DE CLAIMS ────────────────────────────────────
        claims = self._extrair_claims(relatorio_markdown, state_json)

        # ─── FASE 2: VALIDAÇÕES INTERNAS (coerência entre agentes) ──────────
        self._validar_coerencia_financeira(claims, state_json)
        self._validar_coerencia_demografica(claims, state_json)
        self._validar_coerencia_competitiva(claims, state_json)

        # ─── FASE 3: VALIDAÇÕES EXTERNAS (fontes independentes) ──────────────
        await self._validar_fontes_externas(claims)

        # ─── FASE 4: VALIDAÇÃO DO VEREDITO ───────────────────────────────────
        self._validar_veredito(relatorio_markdown, claims, state_json)

        # ─── FASE 5: SCORE FINAL ───────────────────────────────────────────
        score_validacao = self._calcular_score_validacao(claims)

        return {
            "validacao_id": f"val_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status_validacao": self._status_final(),
            "score_validacao": score_validacao,
            "alertas": [asdict(a) for a in self.alertas],
            "claims_verificadas": len(claims),
            "claims_com_alertas": len([a for a in self.alertas if a.severidade in ("CRITICO", "ALTA")]),
            "fontes_independentes": list(set(self.fontes_independentes)),
            "resumo_executivo_validacao": self._gerar_resumo_validacao(),
            "revisar_manual": any(a.severidade == "CRITICO" for a in self.alertas),
        }

    # ─── EXTRAÇÃO DE CLAIMS ──────────────────────────────────────────────────

    def _extrair_claims(self, md: str, state: Dict) -> List[Claim]:
        """Extrai claims do markdown + state com regex + heurísticas."""
        claims = []

        # Padrões de claims financeiras
        financeiras = [
            (r"aluguel (estimado|mediano).*?R\$\s*([\d\.]+(?:,\d+)?)", "financeiro", "aluguel"),
            (r"payback.*?([\d\.]+)\s*meses", "financeiro", "payback"),
            (r"break[- ]?even.*?([\d\.]+)\s*meses", "financeiro", "breakeven"),
            (r"CAPEX.*?R\$\s*([\d\.]+(?:,\d+)?)", "financeiro", "capex"),
            (r"LTV.*?R\$\s*([\d\.]+(?:,\d+)?)", "financeiro", "ltv"),
        ]

        for pattern, cat, subcat in financeiras:
            for match in re.finditer(pattern, md, re.IGNORECASE):
                claims.append(Claim(
                    categoria=cat,
                    texto=match.group(0),
                    valor=match.group(1) if len(match.groups()) >= 1 else None,
                    fonte_no_relatorio="A4 (FinancialEstimator)",
                    severidade="alta" if subcat in ("payback", "breakeven") else "media",
                ))

        # Padrões demográficos
        demo_patterns = [
            (r"(\d+[\d\.]*?)\s*habitantes", "demografico", "populacao"),
            (r"renda per capita.*?R\$\s*([\d\.]+(?:,\d+)?)", "demografico", "renda"),
            (r"(\d+[\d\.]*?)%.*?18[-–]\s*45", "demografico", "faixa_etaria"),
        ]
        for pattern, cat, subcat in demo_patterns:
            for match in re.finditer(pattern, md, re.IGNORECASE):
                claims.append(Claim(
                    categoria=cat,
                    texto=match.group(0),
                    valor=match.group(1) if match.groups() else None,
                    fonte_no_relatorio="A2 (DemoAnalyst)",
                    severidade="media",
                ))

        # Padrões competitivos
        comp_patterns = [
            (r"(\d+)\s*concorrentes", "competitivo", "num_concorrentes"),
            (r"satura[cç][aã]o.*?([\d\.]+)%", "competitivo", "saturacao"),
            (r"nota m[eé]dia.*?([\d\.]+)", "competitivo", "nota_media"),
        ]
        for pattern, cat, subcat in comp_patterns:
            for match in re.finditer(pattern, md, re.IGNORECASE):
                claims.append(Claim(
                    categoria=cat,
                    texto=match.group(0),
                    valor=match.group(1) if match.groups() else None,
                    fonte_no_relatorio="A3b (CompetitorAnalysis)",
                    severidade="alta" if subcat == "num_concorrentes" else "media",
                ))

        # Claims do state JSON (fonte primária)
        if "cenarios_financeiros" in state:
            for i, cenario in enumerate(state.get("cenarios_financeiros", [])):
                claims.append(Claim(
                    categoria="financeiro",
                    texto=f"Cenário {i+1}: payback {cenario.get('payback_meses', 'N/A')} meses",
                    valor=str(cenario.get("payback_meses")),
                    fonte_no_relatorio="A4 (FinancialEstimator)",
                    severidade="alta",
                ))

        return claims

    # ─── VALIDAÇÕES INTERNAS ─────────────────────────────────────────────────

    def _validar_coerencia_financeira(self, claims: List[Claim], state: Dict):
        """Verifica se os números financeiros fazem sentido entre si."""

        # Payback vs Break-even devem ser coerentes
        payback_claims = [c for c in claims if c.valor and "payback" in c.texto.lower()]
        breakeven_claims = [c for c in claims if c.valor and "break" in c.texto.lower()]

        if payback_claims and breakeven_claims:
            # pyrefly: ignore [missing-attribute]
            pb = float(payback_claims[0].valor.replace(",", "."))
            # pyrefly: ignore [missing-attribute]
            be = float(breakeven_claims[0].valor.replace(",", "."))
            if pb < be * 0.8:
                self.alertas.append(AlertaValidacao(
                    tipo="inconsistencia",
                    claim_relacionada=payback_claims[0].texto,
                    descricao=f"Payback ({pb} meses) é menor que 80% do break-even ({be} meses). Tipicamente payback ≥ break-even.",
                    recomendacao="Revisar cálculo do A4 ou verificar se break-even está subestimado.",
                    severidade="ALTA",
                ))

        # CAPEX vs aluguel anual deve ter proporção razoável
        capex = self._extrair_valor_numerico(claims, "capex")
        aluguel = self._extrair_valor_numerico(claims, "aluguel")
        if capex and aluguel:
            razao = capex / (aluguel * 12)
            if razao > 15:
                self.alertas.append(AlertaValidacao(
                    tipo="extrapolacao",
                    claim_relacionada=f"CAPEX R$ {capex:,.0f} vs Aluguel anual R$ {aluguel*12:,.0f}",
                    descricao=f"CAPEX é {razao:.1f}x o aluguel anual. Academias tipicamente têm CAPEX 5–10x aluguel anual.",
                    recomendacao="Verificar se CAPEX inclui obra civil ou se está inflacionado.",
                    severidade="MEDIA",
                ))

    def _validar_coerencia_demografica(self, claims: List[Claim], state: Dict):
        """Verifica se dados demográficos são plausíveis."""

        # População do bairro vs cidade
        pop_bairro = self._extrair_valor_numerico(claims, "populacao")
        if pop_bairro and pop_bairro > 500_000:
            self.alertas.append(AlertaValidacao(
                tipo="dado_nao_verificavel",
                claim_relacionada=f"População do bairro: {pop_bairro:,.0f}",
                descricao="Bairro com população > 500k é atípico no Brasil. Pode ser população da cidade inteira.",
                recomendacao="Verificar no A2 se o dado é do bairro ou do município.",
                severidade="MEDIA",
            ))

        # Faixa etária 18-45 deve ser 25–45% da população
        faixa_etaria = self._extrair_valor_numerico(claims, "faixa_etaria")
        if faixa_etaria and (faixa_etaria < 15 or faixa_etaria > 60):
            self.alertas.append(AlertaValidacao(
                tipo="inconsistencia",
                claim_relacionada=f"{faixa_etaria}% na faixa 18–45",
                descricao=f"{faixa_etaria}% fora do range típico (25–45%).",
                recomendacao="Conferir fonte IBGE e recalcular proporção.",
                severidade="BAIXA",
            ))

    def _validar_coerencia_competitiva(self, claims: List[Claim], state: Dict):
        """Verifica se análise competitiva é coerente."""

        num_concorrentes = self._extrair_valor_numerico(claims, "num_concorrentes")
        saturacao = self._extrair_valor_numerico(claims, "saturacao")

        if num_concorrentes and saturacao:
            if num_concorrentes < 3 and saturacao > 70:
                self.alertas.append(AlertaValidacao(
                    tipo="inconsistencia",
                    claim_relacionada=f"{num_concorrentes:.0f} concorrentes com {saturacao}% saturação",
                    descricao="Poucos concorrentes (<3) com saturação >70% é matematicamente inconsistente.",
                    recomendacao="Revisar métrica de saturação no A3b ou verificar raio de busca.",
                    severidade="ALTA",
                ))

    # ─── VALIDAÇÕES EXTERNAS (com kimi_search) ────────────────────────────────

    async def _validar_fontes_externas(self, claims: List[Claim]):
        """Consulta fontes externas independentes para corroborar claims chave."""

        tasks = []
        for claim in claims:
            if claim.severidade == "alta" and claim.categoria == "financeiro":
                tasks.append(self._pesquisar_benchmark_financeiro(claim))
            elif claim.severidade == "alta" and claim.categoria == "demografico":
                tasks.append(self._pesquisar_demografia_ibge(claim))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _pesquisar_benchmark_financeiro(self, claim: Claim):
        """Busca benchmarks independentes para claims financeiras."""
        query = f"benchmark academia Brasil payback break-even CAPEX {claim.valor} 2025 2026"
        # No GymSite: substituir por chamada ao OpenClaw / Kimi
        # resultado = await kimi_search(query)
        self.fontes_independentes.append(f"[BENCHMARK] {query}")

    async def _pesquisar_demografia_ibge(self, claim: Claim):
        """Busca dados IBGE para corroborar claims demográficas."""
        query = f"IBGE Censo 2022 demografia {claim.valor} habitantes renda"
        # No GymSite: substituir por chamada ao OpenClaw / Kimi
        # resultado = await kimi_search(query)
        self.fontes_independentes.append(f"[IBGE] {query}")

    # ─── VALIDAÇÃO DO VEREDITO ───────────────────────────────────────────────

    def _validar_veredito(self, md: str, claims: List[Claim], state: Dict):
        """Verifica se o veredito final é coerente com os dados."""

        veredito = "APROVADO" if "APROVADO" in md else (
            "REPROVADO" if "REPROVADO" in md else (
                "COM RESSALVAS" if "RESSALVAS" in md else "INVESTIGAR MAIS"
            )
        )

        score_geral = state.get("score_geral", 0)

        # Veredito APROVADO com score < 6 é suspeito
        if veredito == "APROVADO" and score_geral < 6.0:
            self.alertas.append(AlertaValidacao(
                tipo="inconsistencia",
                claim_relacionada=f"Veredito: {veredito} | Score: {score_geral}",
                descricao=f"Veredito APROVADO com score geral {score_geral} < 6.0. Regra interna exige score ≥ 8.",
                recomendacao="Revisar lógica do A6 ou verificar se score foi recalculado pós-ajustes.",
                severidade="CRITICO",
            ))

        # Veredito REPROVADO com score > 7 pode ser excessivamente pessimista
        if veredito == "REPROVADO" and score_geral > 7.0:
            self.alertas.append(AlertaValidacao(
                tipo="extrapolacao",
                claim_relacionada=f"Veredito: {veredito} | Score: {score_geral}",
                descricao=f"Veredito REPROVADO com score {score_geral} > 7.0. Pode haver viés conservador excessivo.",
                recomendacao="Revisar pesos das dimensões ou critérios de corte no A6.",
                severidade="MEDIA",
            ))

        # Score competitivo baixo mas sem bairros alternativos
        score_comp = state.get("score_concorrencia", 0)
        bairros_alt = state.get("bairros_alternativos", [])
        if score_comp < 4.0 and not bairros_alt:
            self.alertas.append(AlertaValidacao(
                tipo="inconsistencia",
                claim_relacionada="Score competitivo baixo sem bairros alternativos",
                descricao=f"Score competitivo {score_comp} indica saturação, mas A6 não sugeriu alternativas.",
                recomendacao="Forçar geração de bairros alternativos no A6 quando score_comp < 4.",
                severidade="ALTA",
            ))

    # ─── SCORE E STATUS ──────────────────────────────────────────────────────

    def _calcular_score_validacao(self, claims: List[Claim]) -> float:
        """0–1: quanto do relatório passou nas validações."""
        if not self.alertas:
            return 1.0

        pesos = {"CRITICO": 0.4, "ALTA": 0.25, "MEDIA": 0.15, "BAIXA": 0.05}
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
        linhas = ["## Validação Cruzada (A8)\n"]
        if not self.alertas:
            linhas.append("✅ Nenhuma inconsistência detectada. Relatório coerente e verificável.")
            return "\n".join(linhas)

        linhas.append(f"**Status:** {self._status_final()}\n")
        linhas.append(f"**Alertas:** {len(self.alertas)}\n")

        for i, alerta in enumerate(self.alertas, 1):
            emoji = {"CRITICO": "🛑", "ALTA": "⚠️", "MEDIA": "⚡", "BAIXA": "ℹ️"}.get(alerta.severidade, "•")
            linhas.append(
                f"{i}. {emoji} **[{alerta.severidade}]** {alerta.tipo}: {alerta.descricao}\n"
                f"   → *Recomendação:* {alerta.recomendacao}\n"
            )

        return "\n".join(linhas)

    # ─── UTILITÁRIOS ─────────────────────────────────────────────────────────

    def _extrair_valor_numerico(self, claims: List[Claim], subtipo: str) -> Optional[float]:
        """Extrai valor float de claims por subtipo aproximado."""
        for c in claims:
            if subtipo in c.texto.lower() and c.valor:
                try:
                    return float(c.valor.replace(".", "").replace(",", "."))
                except ValueError:
                    continue
        return None


# ─── INTEGRAÇÃO FASTAPI ────────────────────────────────────────────────────
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/a8-validator")

class ValidacaoInput(BaseModel):
    relatorio_markdown: str
    state_json: dict
    custo_brl: float | None = None

@router.post("/validar")
async def validar_relatorio(payload: ValidacaoInput):
    validador = A8ValidadorCruzado()
    resultado = await validador.validar(
        relatorio_markdown=payload.relatorio_markdown,
        state_json=payload.state_json,
        custo_brl=payload.custo_brl,
    )
    return resultado
"""


if __name__ == "__main__":
    # Teste standalone com dados simulados
    async def test():
        validador = A8ValidadorCruzado()

        relatorio_mock = """
# Relatório Executivo

## Veredito: APROVADO

O ponto em Pinheiros, São Paulo, demonstra excelente viabilidade.

### Financeiro
- Aluguel estimado: R$ 18.000,00
- CAPEX: R$ 850.000,00
- Payback: 18 meses
- Break-even: 22 meses

### Demográfico
- População do bairro: 650.000 habitantes
- 32% na faixa 18–45 anos
- Renda per capita: R$ 8.500

### Competitivo
- 2 concorrentes diretos
- Saturaçao: 85%
- Nota média: 4.2

### Score Geral: 5.8
        """

        state_mock = {
            "score_geral": 5.8,
            "score_concorrencia": 3.5,
            "bairros_alternativos": [],
            "cenarios_financeiros": [
                {"payback_meses": 18},
                {"payback_meses": 24},
                {"payback_meses": 30},
            ]
        }

        resultado = await validador.validar(relatorio_mock, state_mock)
        print(json.dumps(resultado, indent=2, ensure_ascii=False))

    asyncio.run(test())
