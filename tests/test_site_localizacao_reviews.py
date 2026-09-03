"""Degustação Mercado: localização (unaccent + hints) e tool de reviews."""
from __future__ import annotations

from agents_site.localizacao import (
    injetar_contexto_localizacao,
    mesmos_lugares,
    parse_localizacao_mensagem,
    resolver_localizacao,
)
from tools.bairro_normalize import fold_texto, normalizar_bairro


def test_fold_parangaba_com_sem_acento():
    assert fold_texto("Parangabá") == fold_texto("Parangaba")
    assert normalizar_bairro("Parangabá") == normalizar_bairro("Parangaba")
    assert mesmos_lugares("Parangabá", "Parangaba")
    assert mesmos_lugares("São Paulo", "Sao Paulo")
    assert mesmos_lugares("Cocó", "Coco")
    assert fold_texto("ALDEOTA") == "aldeota"
    assert fold_texto("São Paulo") == "sao paulo"


def test_parse_bairro_em_cidade_uf_na_pergunta():
    loc = parse_localizacao_mensagem(
        "Quantas academias tem no bairro Parangaba em Fortaleza CE"
    )
    assert loc.completa
    assert mesmos_lugares(loc.bairro, "Parangaba")
    assert mesmos_lugares(loc.cidade, "Fortaleza")
    assert loc.uf == "CE"
    assert loc.tipo_negocio == "academia"


def test_parse_parangaba_com_acento_tres_tokens():
    loc = parse_localizacao_mensagem("Parangabá Fortaleza CE")
    assert loc.completa
    assert mesmos_lugares(loc.bairro, "Parangaba")
    assert mesmos_lugares(loc.cidade, "Fortaleza")
    assert loc.uf == "CE"


def test_parse_virgula_uf():
    loc = parse_localizacao_mensagem("Parangaba, Fortaleza - CE")
    assert loc.completa
    assert mesmos_lugares(loc.bairro, "Parangaba")
    assert loc.uf == "CE"


def test_parse_no_coco_fortaleza():
    loc = parse_localizacao_mensagem("no Cocó, Fortaleza?")
    assert loc.completa
    assert mesmos_lugares(loc.bairro, "Coco")
    assert mesmos_lugares(loc.cidade, "Fortaleza")


def test_hint_json_preferido_sobre_mensagem_ambigua():
    loc = resolver_localizacao(
        "e as academias perto?",
        hint={"bairro": "Parangaba", "cidade": "Fortaleza", "uf": "ce"},
    )
    assert loc.completa
    assert loc.origem == "hint_json"
    assert loc.uf == "CE"


def test_bloco_contexto_localizacao():
    msg = (
        "[contexto_localizacao: bairro=Parangabá; bairro_ascii=parangaba; "
        "cidade=Fortaleza; uf=CE] Quais são os reviews dessas academias?"
    )
    loc = resolver_localizacao(msg)
    assert loc.completa
    assert loc.origem == "contexto"
    assert mesmos_lugares(loc.bairro, "Parangaba")
    inj = injetar_contexto_localizacao(msg, loc)
    assert "[localizacao_resolvida:" in inj
    assert "reviews" in inj.lower()
    assert "[contexto_localizacao:" not in inj


def test_resolver_nao_repergunta_quando_completa():
    loc = resolver_localizacao(
        "Quantas academias tem no bairro Parangaba em Fortaleza CE"
    )
    assert loc.completa
    assert not loc.confirme
    inj = injetar_contexto_localizacao(
        "Quantas academias tem no bairro Parangaba em Fortaleza CE", loc
    )
    assert "bairro=Parangaba" in inj or "bairro=Parangába" in inj or "Parangaba" in inj
    assert "cidade=Fortaleza" in inj
    assert "tipo_negocio=academia" in inj


def test_mercado_tem_tool_e_prompt_de_reviews():
    import agents_site.tools as tools_mod
    from agents_site import agent as agent_mod

    assert hasattr(tools_mod, "analisar_reviews_e_dores")
    assert tools_mod.analisar_reviews_e_dores in (agent_mod.mercado.tools or [])
    assert tools_mod.buscar_concorrentes in (agent_mod.mercado.tools or [])
    instr = agent_mod.mercado.instruction or ""
    assert "analisar_reviews_e_dores" in instr
    assert "review" in instr.lower()
    assert "localizacao_resolvida" in instr


def test_analisar_reviews_e_dores_retorna_temas_e_quotes(monkeypatch):
    import agents_site.tools as tools_mod

    def fake_buscar(bairro, cidade, raio, uf, tipo):
        return {
            "concorrentes": [
                {
                    "nome": "Smart Fit Parangaba",
                    "place_id": "ChIJ_test_1",
                    "distancia_m": 200,
                    "rating": 4.2,
                    "num_avaliacoes": 800,
                },
                {
                    "nome": "Arena Champions",
                    "place_id": "ChIJ_test_2",
                    "distancia_m": 400,
                    "rating": 3.8,
                    "num_avaliacoes": 120,
                },
            ]
        }

    def fake_reviews(place_id, nome=""):
        if place_id.endswith("1"):
            return {
                "reviews": [
                    {
                        "rating": 2,
                        "quote_curta": "Sempre lotada no horário de pico",
                        "categoria_dor": "lotacao",
                        "sinal": "negativo",
                    },
                    {
                        "rating": 5,
                        "quote_curta": "Equipamentos novos",
                        "categoria_dor": "outra",
                        "sinal": "positivo",
                    },
                ]
            }
        return {
            "reviews": [
                {
                    "rating": 1,
                    "quote_curta": "Atendimento péssimo na recepção",
                    "categoria_dor": "atendimento_ruim",
                    "sinal": "negativo",
                }
            ]
        }

    def fake_classificar(concs):
        for c in concs:
            temas = {}
            for r in c.get("reviews") or []:
                cat = r.get("categoria_dor")
                if cat and cat != "outra":
                    temas[cat] = temas.get(cat, 0) + 1
            c["temas_insatisfacao"] = [
                {"categoria_dor": k, "mencoes": v, "keyword": k} for k, v in temas.items()
            ]
        return concs

    monkeypatch.setattr(
        "tools.competitor_tools.buscar_academias", fake_buscar
    )
    monkeypatch.setattr(
        "tools.competitor_tools.buscar_reviews_academia", fake_reviews
    )
    monkeypatch.setattr(
        "tools.competitor_tools.classificar_dores_reviews_deterministico",
        fake_classificar,
    )

    out = tools_mod.analisar_reviews_e_dores("Fortaleza", "Parangaba", "CE")
    assert out["ferramenta"] == "analisar_reviews_e_dores"
    assert out.get("erro") in (None, "")
    assert out["rating_medio"] is not None
    assert out["volume_avaliacoes"] == 920
    assert out["temas"], "deve trazer temas de dor"
    assert out["quotes"], "deve trazer quotes"
    assert all("autor" not in q for q in out["quotes"])
    assert "lotacao" in {t["tema"] for t in out["temas"]} or "atendimento_ruim" in {
        t["tema"] for t in out["temas"]
    }


def test_analisar_reviews_nomeia_ferramenta_em_falha(monkeypatch):
    import agents_site.tools as tools_mod

    def boom(*_a, **_k):
        raise RuntimeError("searchapi down")

    monkeypatch.setattr("tools.competitor_tools.buscar_academias", boom)
    out = tools_mod.analisar_reviews_e_dores("Fortaleza", "Parangaba", "CE")
    assert out["ferramenta"] == "analisar_reviews_e_dores"
    assert "analisar_reviews_e_dores" in (out.get("erro") or "")


def test_conversar_input_aceita_localizacao():
    from backend.routers.site_agent import ConversarSiteInput

    body = ConversarSiteInput(
        mensagem="Quais os reviews?",
        localizacao={"bairro": "Parangabá", "cidade": "Fortaleza", "uf": "ce"},
    )
    assert body.localizacao["uf"] == "CE"
    assert body.localizacao["bairro"] == "Parangabá"


_PID_ULTIMA = (
    "Para a Lanchonete a lista informada tem itens que devo manter registro "
    "atualizado no local para apreciação da vigilancia, poderia me indicar quais são eles?"
)


def test_parse_nao_trata_frase_sanitaria_como_bairro_cidade():
    loc = parse_localizacao_mensagem(_PID_ULTIMA)
    assert not loc.completa
    assert "vigilanc" not in (loc.bairro or "").lower()
    assert "poderia" not in (loc.cidade or "").lower()
    assert loc.uf != "ME"


def test_parse_cidade_e_navegantes_sc():
    loc = parse_localizacao_mensagem("Cidade é Navegantes - SC")
    assert mesmos_lugares(loc.cidade, "Navegantes")
    assert loc.uf == "SC"
    assert "cidade" not in (loc.bairro or "").lower()
    assert loc.cidade != "-"


def test_resolver_preserva_previa_quando_frase_nao_e_lugar():
    loc = resolver_localizacao(
        _PID_ULTIMA,
        previa={"bairro": "Centro", "cidade": "Navegantes", "uf": "SC"},
    )
    assert mesmos_lugares(loc.bairro, "Centro")
    assert mesmos_lugares(loc.cidade, "Navegantes")
    assert loc.uf == "SC"
    assert loc.origem == "previa"
