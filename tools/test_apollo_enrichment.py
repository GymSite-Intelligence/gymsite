"""Testes Apollo — auth em header e montagem de query."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools.apollo_enrichment import (
    _extract_phone_from_person,
    _pick_person_by_qsa_name,
    _search_query_pairs,
    enriquecer_empresa_com_apollo,
    enriquecer_socio_qsa_com_apollo,
    limpar_razao_social,
)


class TestApolloHelpers(unittest.TestCase):
    def test_limpar_razao_social(self):
        self.assertEqual(
            limpar_razao_social("ACADEMIA FORTE LTDA"),
            "ACADEMIA FORTE",
        )

    def test_search_query_uses_seniorities_not_legacy_body(self):
        pairs = dict(_search_query_pairs("ACADEMIA FORTE", "Fortaleza"))
        self.assertEqual(pairs.get("q_keywords"), "ACADEMIA FORTE")
        self.assertIn("person_seniorities[]", pairs)
        self.assertNotIn("q_organization_name", pairs)

    @patch.dict("os.environ", {"APOLLO_API_KEY": "test-key"}, clear=False)
    @patch("tools.apollo_enrichment._people_match")
    @patch("tools.apollo_enrichment._search_people")
    def test_enriquecer_sem_api_key_na_url(self, mock_search, mock_match):
        mock_search.return_value = [
            {
                "id": "abc123",
                "first_name": "João",
                "last_name": "Silva",
                "title": "Owner",
            }
        ]
        mock_match.return_value = {
            "id": "abc123",
            "first_name": "João",
            "last_name": "Silva",
            "title": "Owner",
            "email": "joao@academia.com",
            "linkedin_url": "https://linkedin.com/in/joao",
            "organization": {"name": "Academia Forte"},
        }

        result = enriquecer_empresa_com_apollo("Academia Forte LTDA", cidade="Fortaleza")

        mock_search.assert_called()
        mock_match.assert_called()
        self.assertEqual(result["email_direto"], "joao@academia.com")

    def test_extract_phone_from_person(self):
        self.assertEqual(
            _extract_phone_from_person(
                {"phone_numbers": [{"sanitized_number": "+55 85 99999-1234"}]}
            ),
            "5585999991234",
        )

    def test_pick_person_by_qsa_name(self):
        people = [
            {"first_name": "Ana", "last_name": "Costa", "title": "Manager"},
            {"first_name": "Maria", "last_name": "Silva", "title": "Owner"},
        ]
        picked = _pick_person_by_qsa_name(people, "MARIA SILVA SANTOS")
        self.assertEqual(picked["first_name"], "Maria")

    @patch.dict("os.environ", {"APOLLO_API_KEY": "test-key"}, clear=False)
    @patch("tools.apollo_enrichment.enriquecer_socio_qsa_com_apollo")
    @patch("tools.apollo_enrichment._people_match")
    @patch("tools.apollo_enrichment._search_people")
    def test_fallback_qsa_quando_org_sem_contato(
        self, mock_search, mock_match, mock_qsa
    ):
        mock_search.return_value = []
        mock_match.return_value = None
        mock_qsa.return_value = {
            "nome": "Maria Silva",
            "email_direto": "maria@academia.com",
            "telefone_direto": "85999991234",
            "fonte_apollo": "apollo_qsa_match",
        }
        result = enriquecer_empresa_com_apollo(
            "Academia Forte LTDA",
            nome_socio_qsa="MARIA SILVA",
        )
        mock_qsa.assert_called_once()
        self.assertEqual(result["email_direto"], "maria@academia.com")

    @patch.dict("os.environ", {"APOLLO_API_KEY": "test-key"}, clear=False)
    @patch("tools.apollo_enrichment._people_match")
    def test_enriquecer_socio_qsa_match_direto(self, mock_match):
        mock_match.return_value = {
            "first_name": "Maria",
            "last_name": "Silva",
            "email": "maria@academia.com",
            "phone_numbers": [{"sanitized_number": "85999991234"}],
        }
        result = enriquecer_socio_qsa_com_apollo(
            "Academia Forte LTDA", "MARIA SILVA SANTOS"
        )
        self.assertEqual(result["email_direto"], "maria@academia.com")
        self.assertEqual(result["telefone_direto"], "85999991234")

    @patch("tools.apollo_enrichment.urllib.request.urlopen")
    @patch.dict("os.environ", {"APOLLO_API_KEY": "secret-key"}, clear=False)
    def test_apollo_post_uses_x_api_key_header(self, mock_urlopen):
        from tools.apollo_enrichment import _apollo_post

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"people": []}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        _apollo_post("/mixed_people/api_search", "secret-key", [("q_keywords", "GYM")])

        req = mock_urlopen.call_args[0][0]
        self.assertNotIn("api_key=", req.full_url)
        header_val = req.get_header("x-api-key") or req.get_header("X-api-key")
        self.assertEqual(header_val, "secret-key")
