from agents_site.tools_eros import (
    consultar_eros_arquiteto,
    consultar_eros_engenharia,
    consultar_eros_mercado,
    consultar_eros_tecnico,
)
from agents_site.tools_l2_rag import consultar_catalogo_equipamentos

cases = [
    ("tecnico_eros", consultar_eros_tecnico, "linha RRF Total Health"),
    ("tecnico_cascade", consultar_catalogo_equipamentos, "linha RRF Total Health"),
    ("tecnico_preco", consultar_eros_tecnico, "quanto custa o kit Total Health"),
    ("engenharia", consultar_eros_engenharia, "carga de laje academia NBR 6120"),
    ("arquiteto", consultar_eros_arquiteto, "carga de laje academia NBR 6120"),
    ("mercado", consultar_eros_mercado, "metodologia saturacao mercado fitness"),
]
for name, fn, q in cases:
    r = fn(q)
    t = (r.get("texto_rag") or "")[:400].replace("\n", " ")
    print(f"== {name} ==")
    print("fonte=", r.get("fonte"), "n_docs=", r.get("n_docs"), "erro=", r.get("erro", ""))
    print("txt=", t)
    print()
