"""Textos humanos do Explorar — número da tool, prosa sem proxy de código."""
from __future__ import annotations

from typing import Any


_FAIXA_LABEL = {
    "15-24": "15–24 anos",
    "25-39": "25–39 anos",
    "40-59": "40–59 anos",
    "60+": "60 anos ou mais",
}


def _pt(n: int | float) -> str:
    return f"{int(round(float(n))):,}".replace(",", ".")


def _juntar_faixas(faixas: list[Any] | None) -> str:
    labs = [_FAIXA_LABEL.get(str(f), str(f)) for f in (faixas or []) if f]
    if not labs:
        return ""
    if len(labs) == 1:
        return labs[0]
    if len(labs) == 2:
        return f"{labs[0]} e {labs[1]}"
    return f"{', '.join(labs[:-1])} e {labs[-1]}"


def leituras_absorcao(absorcao: dict[str, Any]) -> dict[str, str]:
    teto = int(absorcao.get("teto_unidade") or 0)
    parque = int(absorcao.get("capacidade_parque_estimada") or 0)
    pool = int(absorcao.get("pool_primario") or absorcao.get("pool_demografico") or 0)
    sec = int(absorcao.get("pool_secundario") or 0)
    margem = absorcao.get("margem_fresca")
    area = absorcao.get("area_candidato_m2")
    area_txt = f" ({_pt(area)} m²)" if area else ""
    faixas_sec = _juntar_faixas(absorcao.get("faixas_secundario"))
    faixas_pri = _juntar_faixas(absorcao.get("faixas_primario"))

    if margem is None:
        conclusao = "Ainda não dá para fechar se há folga ou disputa neste recorte."
    elif float(margem) >= 0:
        conclusao = (
            "O parque ainda não cobre toda a estimativa de população ativa do recorte. "
            "Há espaço para aluno novo sem tirar da academia vizinha."
        )
    else:
        conclusao = (
            "O parque já cobre a estimativa de população ativa para o bairro. "
            "Entrar aqui é disputar aluno da academia vizinha."
        )

    if faixas_sec:
        sec_txt = (
            f"Nas faixas {faixas_sec} ainda há cerca de {_pt(sec)} pessoas. "
            "Dá para puxar horário mais vazio (manhã/tarde) com oferta para essa faixa "
            "— sem brigar pelo público principal."
        )
    else:
        sec_txt = (
            f"Nas outras idades ainda há cerca de {_pt(sec)} pessoas. "
            "Dá para puxar horário mais vazio com outro produto."
        )

    if faixas_pri:
        pool_txt = (
            f"No público {faixas_pri} há cerca de {_pt(pool)} pessoas que ainda podem se matricular."
        )
    else:
        pool_txt = (
            f"No público escolhido há cerca de {_pt(pool)} pessoas que ainda podem se matricular."
        )

    return {
        "teto_unidade": (
            f"Com a área prevista{area_txt}, sua unidade comporta cerca de {_pt(teto)} alunos."
        ),
        "capacidade_parque": (
            f"As academias neste recorte somam cerca de {_pt(parque)} vagas estimadas."
        ),
        "pool_primario": pool_txt,
        "pool_secundario": sec_txt,
        "conclusao": conclusao,
    }


def carimbos_explorar(*, label: str | None = None) -> list[str]:
    fontes = []
    lab = (label or "").strip()
    if lab:
        fontes.append(lab)
    if "IBGE" not in (lab or "").upper():
        fontes.append("População por faixa etária · IBGE Censo 2022")
    else:
        fontes.append("População por faixa etária no recorte · IBGE Censo 2022")
    fontes.append("Academias no recorte · SearchAPI Google Maps")
    fontes.append("Capacidade da unidade a partir da área informada")
    return fontes


def html_resumo_explorar(
    *,
    cidade: str | None,
    bairro: str | None,
    label: str | None,
    leituras: dict[str, str] | None,
    rivais: list[dict[str, Any]] | None,
) -> str:
    lugar = ", ".join(p for p in (bairro, cidade) if p) or "o recorte que você olhou"
    leit = leituras or {}
    nomes = [str(r.get("nome") or "").strip() for r in (rivais or []) if r.get("nome")]
    nomes = [n for n in nomes if n][:5]
    lista = "".join(f"<li>{n}</li>" for n in nomes)
    conc = (leit.get("conclusao") or "").strip()
    pool = (leit.get("pool_primario") or "").strip()
    partes = [
        "<p>Olá,</p>",
        f"<p>Segue o resumo da leitura de <strong>{lugar}</strong> no mapa GymSite.</p>",
    ]
    if label:
        partes.append(f"<p>{label}</p>")
    if conc:
        partes.append(f"<p><strong>Leitura:</strong> {conc}</p>")
    if pool:
        partes.append(f"<p>{pool}</p>")
    if lista:
        partes.append(f"<p>Academias no recorte:</p><ul>{lista}</ul>")
    partes.append(
        "<p>Vamos te mandar por aqui as próximas leituras desse recorte — sem compromisso de compra.</p>"
        "<p>Abraço,<br/>GymSite</p>"
    )
    return "".join(partes)
