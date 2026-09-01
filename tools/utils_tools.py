"""
Tools utilitárias compartilhadas pelo pipeline GymSite Intelligence.
"""
from datetime import datetime


def obter_data_atual() -> dict:
    """
    Retorna a data atual do sistema em múltiplos formatos.

    Use SEMPRE quando precisar carimbar um relatório com a data corrente —
    não confie no LLM "saber" a data, porque ele cai pro knowledge cutoff
    do treinamento (mid-2024 no caso do gemini-3.6-flash).

    Returns:
        dict com:
            data_iso: "2026-05-08"
            data_br:  "08/05/2026"
            ano:      2026
            mes:      5
            dia:      8
    """
    n = datetime.now()
    return {
        "data_iso": n.strftime("%Y-%m-%d"),
        "data_br": n.strftime("%d/%m/%Y"),
        "ano": n.year,
        "mes": n.month,
        "dia": n.day,
    }
