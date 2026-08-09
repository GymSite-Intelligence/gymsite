from tools.explorar_leitura import carimbos_explorar, html_resumo_explorar, leituras_absorcao


def test_leituras_sem_proxy_de_codigo():
    absb = {
        "teto_unidade": 2100,
        "capacidade_parque_estimada": 15545,
        "pool_primario": 8400,
        "pool_secundario": 138,
        "margem_fresca": -7145,
        "rotulo": "roubo",
        "area_candidato_m2": 1150,
        "faixas_secundario": ["15-24", "60+"],
        "faixas_primario": ["25-39", "40-59"],
    }
    out = leituras_absorcao(absb)
    blob = " ".join(out.values()).lower()
    assert "pool_primario" not in blob
    assert "cap_parque" not in blob
    assert "matr_m2" not in blob
    assert "derivada" not in blob
    assert "n/a" not in blob
    assert "faltam" not in out["conclusao"].lower()
    assert "população ativa" in out["conclusao"].lower()
    assert "15–24" in out["pool_secundario"] or "15-24" in out["pool_secundario"]
    assert "60" in out["pool_secundario"]
    assert "ibge" not in out["pool_primario"].lower()
    assert "2.100" in out["teto_unidade"]


def test_carimbos_explorar_sem_proxy_centralizado():
    fontes = carimbos_explorar(
        label="Recorte do bairro Cocó · IBGE Censo 2022",
    )
    blob = " ".join(fontes).lower()
    assert "ibge censo 2022" in blob
    assert "searchapi" in blob or "google maps" in blob
    assert "pool_primario" not in blob
    assert "matr_m2" not in blob
    assert "derivada" not in blob


def test_html_resumo_sem_preco():
    html = html_resumo_explorar(
        cidade="Fortaleza",
        bairro="Cocó",
        label="Raio 1 km a partir do centro do bairro · IBGE Censo 2022",
        leituras=leituras_absorcao(
            {
                "teto_unidade": 2100,
                "capacidade_parque_estimada": 8000,
                "pool_primario": 9000,
                "pool_secundario": 100,
                "margem_fresca": 1000,
                "rotulo": "fresco",
            }
        ),
        rivais=[{"nome": "Academia VS Club", "dist_m": 500}],
    )
    low = html.lower()
    assert "preço" not in low and "plano" not in low
    assert "cocó" in low
    assert "vs club" in low
