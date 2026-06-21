"""
Classificação de segmento operacional para unidades do parque ativo (CNPJ).

Sem bucket "outro": todo registro cai em um segmento de mercado ou em
`saude_clinica` (fora do parque comercial fitness).

Retorna também confiança e sinais — base para validação Places opcional.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# Alinhado ao produto + extensões de mercado (sem "outro")
SEGMENTOS = (
    "academia",
    "crossfit_box",
    "studio_pilates",
    "studio_funcional",
    "studio_bem_estar",
    "lutas",
    "personal_studio",
    "aqua_fitness",
    "saude_clinica",
    "fora_familia",
)

SEGMENTO_LABELS: dict[str, str] = {
    "academia": "Academia tradicional",
    "crossfit_box": "CrossFit / Box",
    "studio_pilates": "Estúdio Pilates",
    "studio_funcional": "Estúdio funcional",
    "studio_bem_estar": "Estúdio bem-estar (yoga, dança)",
    "lutas": "Lutas / artes marciais",
    "personal_studio": "Personal / coaching",
    "aqua_fitness": "Natacao / aquáticos",
    "saude_clinica": "Clínica / reabilitação",
    "fora_familia": "Fora da família fitness (CNAE não-esporte)",
}

# Buckets de EXCLUSÃO do parque comercial: clínica (por nome) + fora_familia (por
# CNAE principal não-esporte).
_SEGMENTOS_EXCLUIDOS = {"saude_clinica", "fora_familia"}
SEGMENTOS_PARQUE_COMERCIAL = tuple(s for s in SEGMENTOS if s not in _SEGMENTOS_EXCLUIDOS)

# ── Portão CNAE: a "família fitness" = grupo CNAE 931 (atividades esportivas) ──
# Fonte da verdade do que É academia/studio/box: a ATIVIDADE registrada, não o nome.
# Nome só separa o TIPO DENTRO da família (academia vs studio vs box compartilham
# CNAE). Decisão de produto: 9312300 (clubes) e 8591100 (ensino esportivo) FORA.
# Sem o portão, 33-36% do parque era joio (fisioterapia, hotel, salão, varejo com
# nome "fit" caíam em academia pelo default).
_CNAE_FAMILIA_FITNESS = frozenset({
    "9311500", "9311501",                       # gestão de instalações esportivas
    "9313100",                                  # condicionamento físico (academia) — núcleo
    "9319101", "9319102", "9319103", "9319199",  # outras atividades esportivas (lutas/eventos)
})

_CNAE_PILATES = frozenset({"9311500", "9311501"})
_CNAE_LUTAS = frozenset({"9319101", "9319102", "9319103"})


def _cnae_digits(c) -> str:
    """Normaliza CNAE pra 7 dígitos (aceita '9313-1/00' ou '9313100')."""
    return re.sub(r"\D", "", str(c or ""))

_RE_ACADEMIA_TYPO = re.compile(
    r"acad[aei][\w]*|academ|acadim|acadi[mn]|gene[sz]e|forma[\s\-]?fit",
    re.I,
)


@dataclass
class ClassificacaoSegmento:
    segmento: str
    confianca: str  # alta | media | baixa
    metodo: str  # heuristica_nome | heuristica_cnae | razao_social | default_mercado | places
    sinais: list[str] = field(default_factory=list)
    requer_validacao: bool = False
    incluir_no_parque: bool = True

    def to_dict(self) -> dict:
        return {
            "segmento_operacao": self.segmento,
            "segmento_label": segmento_label(self.segmento),
            "segmento_confianca": self.confianca,
            "segmento_metodo": self.metodo,
            "segmento_sinais": self.sinais,
            "segmento_requer_validacao": self.requer_validacao,
            "incluir_no_parque": self.incluir_no_parque,
        }


def _norm(text: str) -> str:
    s = (text or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def _parse_cnaes(secundarios: str | None) -> set[str]:
    if not secundarios:
        return set()
    return {re.sub(r"\D", "", c) for c in secundarios.split(",") if c.strip()}


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(n in haystack for n in needles)


def _texto_classificacao(
    nome_fantasia: str | None,
    razao_social: str | None = None,
) -> tuple[str, str]:
    """Combina fontes; retorna (texto, fonte_primaria)."""
    nf = _norm(nome_fantasia or "")
    rs = _norm(razao_social or "")
    if nf:
        return nf, "nome_fantasia"
    if rs:
        return rs, "razao_social"
    return "", "vazio"


def classificar_segmento(
    nome_fantasia: str | None,
    cnae_principal: str | None = None,
    cnaes_secundarios: str | None = None,
    *,
    razao_social: str | None = None,
) -> ClassificacaoSegmento:
    texto, fonte_txt = _texto_classificacao(nome_fantasia, razao_social)
    sec = _parse_cnaes(cnaes_secundarios)
    sinais: list[str] = []

    # ── PORTÃO CNAE PRINCIPAL (estágio 1) ──
    # Fora da família 931 = joio, descarta — mesmo com nome "fit" ou CNAE fitness
    # SECUNDÁRIO (clínica com anexo de musculação não é academia). Só barra quando
    # há CNAE principal; ausente cai no cascade de nome (defensivo contra gap de carga).
    principal = _cnae_digits(cnae_principal)
    if principal and principal not in _CNAE_FAMILIA_FITNESS:
        return ClassificacaoSegmento(
            segmento="fora_familia",
            confianca="alta",
            metodo="cnae_principal",
            sinais=[f"CNAE principal {principal} fora da família fitness (931)"],
            requer_validacao=False,
            incluir_no_parque=False,
        )

    def hit(seg: str, conf: str, metodo: str, *motivos: str) -> ClassificacaoSegmento:
        sig = list(motivos) or [metodo]
        incluir = seg != "saude_clinica"
        return ClassificacaoSegmento(
            segmento=seg,
            confianca=conf,
            metodo=metodo,
            sinais=sig,
            requer_validacao=conf == "baixa",
            incluir_no_parque=incluir,
        )

    # --- Fora do parque comercial ---
    if _contains_any(
        texto,
        (
            "fisioterap",
            "fisio ",
            " fisi",
            "clinica de",
            "clínica de",
            "quiroprax",
            "ortopedia",
            "reabilitacao",
            "reabilitação",
            "podolog",
            "consultorio",
            "consultório",
            "harmonizacao",
            "harmonização",
            "estetica facial",
            "estética facial",
            "spa medic",
            "nutrolog",
        ),
    ):
        return hit("saude_clinica", "alta", "heuristica_nome", "keyword saude/clinica")

    # --- Segmentos específicos ---
    if _contains_any(
        texto,
        ("crossfit", "cross fit", "cross-fit", " wod", " box ", "cf box"),
    ) or "crossfit" in texto.replace(" ", ""):
        return hit("crossfit_box", "alta", "heuristica_nome", "crossfit/box")

    if "pilates" in texto or bool(sec & _CNAE_PILATES):
        return hit("studio_pilates", "alta", "heuristica_nome", "pilates")

    if _contains_any(
        texto,
        (
            "funcional",
            "treino funcional",
            "training funcional",
            "hiit",
            "bootcamp",
            "ems ",
            " ems",
            "adaptro",
        ),
    ):
        return hit("studio_funcional", "alta", "heuristica_nome", "funcional/hiit")

    if _contains_any(
        texto,
        (
            "yoga",
            "ioga",
            "zumba",
            "danca",
            "dança",
            "ritmos",
            "ballet",
            "fitdance",
            "pole dance",
            "piloxing",
            "alongamento",
        ),
    ) or "academia de danca" in texto or "academia de dança" in texto:
        return hit("studio_bem_estar", "alta", "heuristica_nome", "yoga/danca")

    if _contains_any(
        texto,
        (
            "muay thai",
            "muaythai",
            "jiu jitsu",
            "jiu-jitsu",
            "jiujitsu",
            " mma ",
            "karate",
            "karatê",
            "boxe",
            "lutas",
            "capoeira",
            "krav maga",
        ),
    ) or bool(sec & _CNAE_LUTAS):
        return hit("lutas", "alta", "heuristica_nome", "lutas/mma")

    if _contains_any(
        texto,
        (
            "natacao",
            "natação",
            "aquatic",
            "aquatico",
            "aquático",
            "hidrogin",
            "hidro ",
            "tibum",
            "beach tennis",
            "beach tenni",
        ),
    ):
        return hit("aqua_fitness", "media", "heuristica_nome", "aquaticos")

    if _contains_any(
        texto,
        (
            "personal",
            "personal trainer",
            "treinador",
            "coaching",
            "assessoria esportiva",
            "consultoria esportiva",
        ),
    ) and not _contains_any(texto, ("academia", "fitness", "gym")):
        return hit("personal_studio", "media", "heuristica_nome", "personal/coaching")

    if _contains_any(
        texto,
        (
            "academia",
            "fitness",
            "smart fit",
            "bluefit",
            "bodytech",
            "pratique",
            " gym",
            "gym ",
            "musculacao",
            "musculação",
            "ironberg",
            "selfit",
            "4fit",
            "85fit",
            "affit",
            "alifit",
            "centro de treinamento",
            "ct ",
            " ct",
            "performance",
            "sports",
            "sport ",
        ),
    ) or _RE_ACADEMIA_TYPO.search(texto):
        conf = "alta" if _contains_any(texto, ("academia", "fitness", "gym")) else "media"
        return hit("academia", conf, "heuristica_nome", "academia/fitness")

    if _contains_any(texto, ("estudio", "estúdio", "studio")):
        if "pilates" in texto:
            return hit("studio_pilates", "alta", "heuristica_nome", "studio+pilates")
        if "funcional" in texto or "training" in texto:
            return hit("studio_funcional", "media", "heuristica_nome", "studio+funcional")
        return hit("studio_bem_estar", "media", "heuristica_nome", "studio generico")

    # CNAE 9313100: default mercado = academia tradicional
    metodo = "default_mercado" if fonte_txt == "vazio" else "heuristica_nome"
    if fonte_txt == "razao_social":
        metodo = "razao_social"
    sinais.append("sem keyword especifica; default CNAE 9313100")
    if fonte_txt == "vazio":
        return hit("academia", "baixa", metodo, *sinais)
    return hit("academia", "media", metodo, *sinais)


def classificar_segmento_cnpj(
    nome_fantasia: str | None,
    cnae_principal: str | None = None,
    cnaes_secundarios: str | None = None,
    *,
    razao_social: str | None = None,
) -> str:
    """API legada — retorna só o código do segmento."""
    return classificar_segmento(
        nome_fantasia, cnae_principal, cnaes_secundarios, razao_social=razao_social
    ).segmento


def segmento_label(segmento: str) -> str:
    return SEGMENTO_LABELS.get(segmento, segmento.replace("_", " ").title())


def agregar_por_segmento(
    segmentos: Iterable[str],
    *,
    apenas_parque_comercial: bool = True,
) -> dict[str, int]:
    keys = SEGMENTOS_PARQUE_COMERCIAL if apenas_parque_comercial else SEGMENTOS
    counts = {s: 0 for s in keys}
    for seg in segmentos:
        if seg == "saude_clinica" and apenas_parque_comercial:
            continue
        key = seg if seg in counts else "academia"
        counts[key] += 1
    return counts


def composicao_com_percentuais(
    counts: dict[str, int],
    *,
    segmentos_ordem: tuple[str, ...] | None = None,
) -> dict[str, dict[str, float | int]]:
    ordem = segmentos_ordem or SEGMENTOS_PARQUE_COMERCIAL
    total = sum(counts.values()) or 1
    out: dict[str, dict[str, float | int]] = {}
    for seg in ordem:
        n = counts.get(seg, 0)
        if n <= 0:
            continue
        out[seg] = {
            "count": n,
            "pct": round(100.0 * n / total, 1),
            "label": segmento_label(seg),
        }
    return out
