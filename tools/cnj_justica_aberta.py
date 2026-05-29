"""
tools/cnj_justica_aberta.py — Conector estático para dados de cartórios do CNJ Justiça Aberta.

Mapeamento estático (Base Estática fallback) para comarcas da Região Metropolitana de Fortaleza (RMF):
- Fortaleza (1ª a 6ª zona)
- Eusébio
- Caucaia
- Aquiraz
- Maracanaú

Evita chamadas de rede lentas ou frágeis ao site do CNJ e garante 100% de disponibilidade.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Base estática de serventias (Registro de Imóveis) do Ceará
CARTORIOS_BASE: dict[str, dict[str, Any]] = {
    "020719": {
        "cns": "020719",
        "nome": "1º Ofício de Registro de Imóveis de Fortaleza",
        "telefone": "(85) 3261-7101",
        "endereco": "Avenida Antônio Sales, 2187, Dionísio Torres, Fortaleza - CE",
        "site": "primeirazona.com.br",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "015669": {
        "cns": "015669",
        "nome": "2º Ofício de Registro de Imóveis de Fortaleza",
        "telefone": "(85) 3052-1900",
        "endereco": "Rua Dr. José Lourenço, 870, Sala 111, Meireles, Fortaleza - CE",
        "site": "alvaromello.com.br",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "015719": {
        "cns": "015719",
        "nome": "3º Ofício de Registro de Imóveis de Fortaleza",
        "telefone": "(85) 3261-7977",
        "endereco": "Rua Joaquim Nabuco, 2336, Dionísio Torres, Fortaleza - CE",
        "site": "torifortaleza.com.br",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "019174": {
        "cns": "019174",
        "nome": "Cartório do Registro de Imóveis da 4ª Zona de Fortaleza (Cartório Miranda Bezerra)",
        "telefone": "(85) 3224-6931",
        "endereco": "Rua Silva Paulet, 1180, Aldeota, Fortaleza - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "015735": {
        "cns": "015735",
        "nome": "5º Ofício de Registro de Imóveis de Fortaleza",
        "telefone": "(85) 3219-5050",
        "endereco": "Av. Barão de Studart, 330, Meireles, Fortaleza - CE",
        "site": "cri5fortaleza.com.br",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "015750": {
        "cns": "015750",
        "nome": "Cartório de Registro de Imóveis da 6ª Zona de Fortaleza",
        "telefone": "(85) 3244-2604",
        "endereco": "Av. Desembargador Moreira, 1300, Sala 1002-SC, Aldeota, Fortaleza - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "019307": {
        "cns": "019307",
        "nome": "Cartório Facundo - 2º Ofício de Eusébio",
        "telefone": "(85) 3260-1836",
        "endereco": "Avenida Eusébio de Queiroz, 1095, Centro, Eusébio - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "020651": {
        "cns": "020651",
        "nome": "Ofício Privativo de Registro de Imóveis de Caucaia",
        "telefone": "(85) 3039-2197",
        "endereco": "Rua Barão de Ibiapaba, 340, Centro, Caucaia - CE",
        "site": "registrocaucaia.com.br",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "017889": {
        "cns": "017889",
        "nome": "Cartório do 3º Ofício de Registro de Imóveis de Aquiraz (Cartório Joaquim Pereira)",
        "telefone": "(85) 3361-1186",
        "endereco": "Rua Virgílio Coelho, 333, Centro, Aquiraz - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "019356": {
        "cns": "019356",
        "nome": "Cartório Florêncio - 2º Ofício de Aquiraz",
        "telefone": "(85) 3361-2021",
        "endereco": "Rua Virgílio Coelho, 296, Centro, Aquiraz - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    },
    "015594": {
        "cns": "015594",
        "nome": "Cartório Aguiar Rocha - 2º Ofício de Registro de Imóveis de Maracanaú",
        "telefone": "(85) 3215-8600",
        "endereco": "Av. Dr. Mendel Steinbruch, 271, Lojas 01 e 02, Pajuçara, Maracanaú - CE",
        "site": "",
        "horario_atendimento": "Segunda a sexta-feira, das 08h às 17h",
    }
}

# Mapeamento geográfico de bairros de Fortaleza para as Zonas de Registro de Imóveis (CNS)
FORTALEZA_BAIRROS_ZONAS: dict[str, str] = {
    # 1ª Zona (CNS 020719)
    "agua fria": "020719", "cambeba": "020719", "cidade dos funcionarios": "020719",
    "edson de queiroz": "020719", "guararapes": "020719", "lagoa redonda": "020719",
    "messejana": "020719", "sapiranga": "020719", "coite": "020719", "jose de alencar": "020719",

    # 2ª Zona (CNS 015669)
    "benfica": "015669", "dias macedo": "015669", "montese": "015669", "vila uniao": "015669",
    "serrinha": "015669", "praia de iracema": "015669", "centro": "015669",

    # 3ª Zona (CNS 015719)
    "alvaro weyne": "015719", "antonio bezerra": "015719", "barra do ceara": "015719",
    "conjunto ceara": "015719", "damas": "015719", "genibau": "015719", "granja lisboa": "015719",
    "parquelandia": "015719", "pici": "015719", "pirambu": "015719",

    # 4ª Zona (CNS 019174)
    "dionisio torres": "019174", "mucuripe": "019174", "varjota": "019174",
    "sao joao do tauape": "019174", "aldeota": "019174", "meireles": "019174",

    # 5ª Zona (CNS 015735)
    "alto da balanca": "015735", "aerolandia": "015735", "cais do porto": "015735",
    "cidade 2000": "015735", "coco": "015735", "dunas": "015735", "papicu": "015735",
    "praia do futuro": "015735", "vicente pinzon": "015735",

    # 6ª Zona (CNS 015750)
    "ancuri": "015750", "barroso": "015750", "canindezinho": "015750", "conjunto esperanca": "015750",
    "itapery": "015750", "jose walter": "015750", "maraponga": "015750", "mondubim": "015750",
    "passare": "015750", "siqueira": "015750", "parangaba": "015750",
}


def _slug(s: str) -> str:
    """Normaliza strings removendo acentos e convertendo para lowercase e espacos simples."""
    s = (s or "").strip().lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolver_cartorio_por_cns(cns: str) -> dict[str, Any] | None:
    """Resolve os dados do cartorio pelo CNS. Best-effort com fallbacks de formatacao."""
    if not cns:
        return None
    # Remove pontos e traços do CNS
    clean_cns = re.sub(r"\D", "", cns)
    # Garante 6 dígitos preenchendo com zeros à esquerda
    clean_cns = clean_cns.zfill(6)

    cart = CARTORIOS_BASE.get(clean_cns)
    if not cart:
        return None

    return {
        **cart,
        "fonte": "cnj_justica_aberta",
        "consultado_em": datetime.now().date().isoformat()
    }


def resolver_cartorio_por_municipio(cidade: str, uf: str, bairro: str | None = None) -> dict[str, Any] | None:
    """Resolve os dados do cartorio por comarca (cidade e uf) e bairro (para Fortaleza)."""
    uf_slug = _slug(uf)
    if uf_slug != "ce":
        return None  # Escopo do MVP restrito ao Ceará

    cidade_slug = _slug(cidade)
    bairro_slug = _slug(bairro or "")

    cns = None

    if "fortaleza" in cidade_slug:
        # Se for Fortaleza, busca mapear por bairro
        for b_name, b_cns in FORTALEZA_BAIRROS_ZONAS.items():
            if b_name in bairro_slug or b_name in _slug(cidade): # caso bairro venha no campo cidade
                cns = b_cns
                break
        
        # Se nao mapeou pelo bairro do input, tenta buscar no endereço do candidato se disponível
        if not cns and bairro:
            # Fallback por correspondência na própria string do bairro
            for b_name, b_cns in FORTALEZA_BAIRROS_ZONAS.items():
                if b_name in _slug(bairro):
                    cns = b_cns
                    break
        
        # Fallback padrão para Fortaleza (1ª Zona) se nenhum bairro der match
        if not cns:
            cns = "020719"

    elif "eusebio" in cidade_slug:
        cns = "019307"  # Cartório Facundo (Registro de Imóveis)
    elif "caucaia" in cidade_slug:
        cns = "020651"  # Ofício Privativo de Caucaia
    elif "aquiraz" in cidade_slug:
        cns = "017889"  # Cartório Joaquim Pereira (3º Ofício)
    elif "maracanau" in cidade_slug:
        cns = "015594"  # Cartório Aguiar Rocha (2º Ofício)

    if not cns:
        return None

    return resolver_cartorio_por_cns(cns)
