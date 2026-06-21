"""Extração de sugestões do texto do LLM — `_extrair_sugestoes` (Consultor V2).

Bug achado em prod (2026-06-21): o modelo emitiu o bloco de sugestões pretty-printed
e dentro de uma cerca ```json, então o regex antigo (`\\{"sugestoes"`, que exigia `{`
colado em `"sugestoes"`) não casava → o JSON cru VAZAVA pro usuário no chat. Agora
o regex tolera espaço/newline e a cerca markdown é removida do texto visível. Puro/offline.
"""
from services.consultor.consultor_engine import _extrair_sugestoes


def test_pretty_print_dentro_de_fence():
    texto = (
        "Com esses dados, posso iniciar a análise.\n\n"
        "```json\n"
        "{\n"
        ' "sugestoes": [\n'
        '  "Pesquisar pontos comerciais",\n'
        '  "Analisar a demografia do bairro",\n'
        '  "Estimar o investimento inicial"\n'
        " ]\n"
        "}\n"
        "```"
    )
    limpo, sug = _extrair_sugestoes(texto)
    assert sug == [
        "Pesquisar pontos comerciais",
        "Analisar a demografia do bairro",
        "Estimar o investimento inicial",
    ]
    assert "```" not in limpo
    assert "sugestoes" not in limpo
    assert limpo.endswith("a análise.")


def test_formato_compacto_legado():
    # o formato antigo (sem espaço, sem fence) continua funcionando
    texto = 'Resposta.\n{"sugestoes": ["A", "B"]}'
    limpo, sug = _extrair_sugestoes(texto)
    assert sug == ["A", "B"]
    assert limpo == "Resposta."


def test_sem_bloco_de_sugestoes():
    texto = "Só uma resposta conversacional, sem JSON."
    limpo, sug = _extrair_sugestoes(texto)
    assert sug == []
    assert limpo == texto


def test_json_malformado_nao_quebra():
    texto = 'Resp.\n```json\n{ "sugestoes": [não é json] }\n```'
    limpo, sug = _extrair_sugestoes(texto)
    assert sug == []  # não explode; degrada pra lista vazia
