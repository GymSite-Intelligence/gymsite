"""
tools/apollo_enrichment.py

Módulo de integração com a API do Apollo.io para enriquecer leads B2B
(novos entrantes de CNPJ) com dados de contato de tomadores de decisão.
"""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
import json
from typing import Any, Optional


def limpar_razao_social(nome: str) -> str:
    """
    Remove sufixos corporativos e de natureza jurídica comuns no Brasil
    para otimizar a pesquisa textual no banco de dados do Apollo.io.
    """
    if not nome:
        return ""
    
    # Converte para maiúsculas e remove acentuações/pontuações simples
    n = nome.upper().strip()
    
    # Expressão regular para termos jurídicos e societários comuns
    pattern = r"\b(LTDA|ME|EPP|EIRELI|S/?A|S\.A\.|LIMITADA|SOCIEDADE|IND[UÚ]STRIA|COM[EÉ]RCIO|SERVI[CÇ]OS?|EIPLI)\b"
    n = re.sub(pattern, "", n)
    
    # Remove caracteres especiais excedentes e múltiplos espaços
    n = re.sub(r"[^\w\s-]", "", n)
    n = re.sub(r"\s+", " ", n).strip(" -")
    
    return n


def enriquecer_empresa_com_apollo(
    organization_name: str, 
    cidade: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """
    Faz a busca na API do Apollo.io para localizar sócios/decisores da empresa.
    
    Parâmetros:
        organization_name: Razão Social ou Nome Fantasia da empresa.
        cidade: Opcional, filtra a localização das pessoas.
        
    Retorna:
        dict contendo nome, cargo, e-mail direto e linkedin_url se houver match.
    """
    api_key = os.getenv("APOLLO_API_KEY", "").strip()
    if not api_key:
        # Silencioso se não configurado
        return None

    # 1. Limpar e preparar o nome para busca
    query_org = limpar_razao_social(organization_name)
    if not query_org or len(query_org) < 3:
        return None

    try:
        # Construir filtros
        # Endpoint recomendado: mixed_people/api_search (POST)
        url = f"https://api.apollo.io/api/v1/mixed_people/api_search?api_key={api_key}"
        
        # Filtros de cargos
        titles = ["owner", "founder", "director", "partner", "sócio", "proprietário", "gerente", "ceo"]
        
        # Corpo da requisição
        payload = {
            "q_organization_name": query_org,
            "person_locations": ["Brazil"],
            "person_titles": titles,
            "page": 1,
            "per_page": 5
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            },
            method="POST"
        )
        
        # Executar chamada de busca
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
        people = res_data.get("people") or []
        if not people:
            # Se falhar pelo nome limpo da razão social, tenta com o nome original (caso seja fantasia simples)
            if query_org != organization_name.strip():
                payload["q_organization_name"] = organization_name.strip()
                req_retry = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req_retry, timeout=10) as response_retry:
                    res_data_retry = json.loads(response_retry.read().decode("utf-8"))
                people = res_data_retry.get("people") or []
                
        if not people:
            return None

        # 2. Escolher a melhor pessoa correspondente (preferindo títulos mais altos)
        # Títulos de prioridade
        priority_map = {"owner": 1, "founder": 1, "ceo": 1, "sócio": 2, "partner": 2, "proprietário": 2, "director": 3, "gerente": 4}
        
        best_person = None
        best_score = 99
        
        for p in people:
            title = (p.get("title") or "").lower()
            score = 10  # default
            for t_key, val in priority_map.items():
                if t_key in title:
                    score = min(score, val)
            
            if score < best_score:
                best_score = score
                best_person = p
                
        if not best_person:
            best_person = people[0]

        person_id = best_person.get("id")
        nome_completo = f"{best_person.get('first_name', '')} {best_person.get('last_name', '')}".strip()
        cargo = best_person.get("title")
        email = best_person.get("email")
        linkedin = best_person.get("linkedin_url")

        # 3. Revelar contatos (Bulk Match) se e-mail estiver oculto/ausente e tivermos o ID
        if person_id and (not email or "@" not in email):
            try:
                match_url = f"https://api.apollo.io/api/v1/people/bulk_match?api_key={api_key}"
                match_payload = {
                    "details": [{"id": person_id}]
                }
                match_req = urllib.request.Request(
                    match_url,
                    data=json.dumps(match_payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Cache-Control": "no-cache"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(match_req, timeout=10) as match_response:
                    match_data = json.loads(match_response.read().decode("utf-8"))
                    
                matches = match_data.get("matches") or []
                if matches and isinstance(matches[0], dict):
                    matched_person = matches[0]
                    email = matched_person.get("email") or email
                    linkedin = matched_person.get("linkedin_url") or linkedin
            except Exception:
                pass  # match falhou, prossegue com os dados parciais da busca

        return {
            "nome": nome_completo or "Não especificado",
            "cargo": cargo or "Sócio / Proprietário",
            "email_direto": email or None,
            "linkedin_url": linkedin or None,
            "empresa_match": best_person.get("organization", {}).get("name")
        }

    except Exception as e:
        # Silencioso em caso de erro no pipeline do adk
        print(f"[Apollo Enrichment Engine] Erro ao buscar: {e}")
        return None
