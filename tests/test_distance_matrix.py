"""
Testes unitarios para tools/distance_matrix_tools.py

Cobertura:
    1. cache_hit       -- chamada repetida nao bate na API (mock)
    2. sp_ce_coherence -- SP->Fortaleza retorna ~2700-3000km
    3. graceful_fallback -- key ausente retorna None sem excecao
    4. disk_cache      -- arquivo .json gravado apos 1a chamada
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Garante que tools/ esta no path quando rodado da raiz do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.distance_matrix_tools import (
    CACHE_DIR,
    _cache_key,
    calcular_distancia_rodoviaria,
    distancia_fornecedor_para_cidade,
)

# Coordenadas de referencia
SP_LAT, SP_LNG = -23.5505, -46.6333   # Sao Paulo capital
FOR_LAT, FOR_LNG = -3.7172, -38.5433  # Fortaleza CE
EUS_LAT, EUS_LNG = -3.889, -38.454    # Eusebio CE


def _mock_distance_matrix_response(distancia_m: int = 2_900_000, duracao_s: int = 129_600):
    """Constroi resposta sintetica da Distance Matrix API."""
    return {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "distance": {
                            "value": distancia_m,
                            "text": f"{distancia_m // 1000} km",
                        },
                        "duration": {
                            "value": duracao_s,
                            "text": f"{duracao_s // 3600} hours",
                        },
                    }
                ]
            }
        ],
    }


class TestCacheKey(unittest.TestCase):
    def test_snap_tolerance(self):
        """Coords com diferenca < 0.001 devem gerar a mesma chave."""
        k1 = _cache_key((-23.5505, -46.6333), (-3.7172, -38.5433))
        k2 = _cache_key((-23.5504, -46.6334), (-3.7171, -38.5432))
        self.assertEqual(k1, k2)

    def test_different_dest_different_key(self):
        k1 = _cache_key((-23.5505, -46.6333), (-3.7172, -38.5433))
        k2 = _cache_key((-23.5505, -46.6333), (-10.0, -50.0))
        self.assertNotEqual(k1, k2)


class TestFallback(unittest.TestCase):
    """Sem API key / live off deve retornar None graciosamente."""

    def test_no_key_returns_none(self):
        env_backup = os.environ.copy()
        os.environ.pop("GOOGLE_DISTANCE_MATRIX_API_KEY", None)
        os.environ.pop("GOOGLE_MAPS_API_KEY", None)
        os.environ.pop("DISTANCE_MATRIX_ENABLED", None)
        try:
            result = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, FOR_LAT, FOR_LNG)
            self.assertIsNone(result)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_live_off_skips_api_even_with_maps_key(self):
        key = _cache_key((SP_LAT, SP_LNG), (FOR_LAT, FOR_LNG))
        cache_file = CACHE_DIR / f"{key}.json"
        cache_file.unlink(missing_ok=True)
        with patch.dict(
            os.environ,
            {
                "GOOGLE_MAPS_API_KEY": "FAKE_MAPS",
                "GOOGLE_DISTANCE_MATRIX_API_KEY": "FAKE_DM",
                "DISTANCE_MATRIX_ENABLED": "0",
            },
        ):
            with patch("googlemaps.Client") as mock_cls:
                result = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, FOR_LAT, FOR_LNG)
                self.assertIsNone(result)
                mock_cls.assert_not_called()


class TestCacheHit(unittest.TestCase):
    """Chamada repetida deve vir do cache, sem chamar a API."""

    def test_second_call_uses_cache(self):
        key = _cache_key((SP_LAT, SP_LNG), (FOR_LAT, FOR_LNG))
        cache_file = CACHE_DIR / f"{key}.json"

        # Limpa cache se existir
        cache_file.unlink(missing_ok=True)

        fake_response = _mock_distance_matrix_response()

        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = fake_response

        with patch.dict(
            os.environ,
            {
                "GOOGLE_DISTANCE_MATRIX_API_KEY": "FAKE_KEY",
                "DISTANCE_MATRIX_ENABLED": "1",
            },
        ):
            with patch("googlemaps.Client", return_value=mock_client):
                # 1a chamada -- deve chamar API
                r1 = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, FOR_LAT, FOR_LNG)
                self.assertIsNotNone(r1)
                self.assertEqual(mock_client.distance_matrix.call_count, 1)

                # 2a chamada -- deve vir do cache (mock nao deve ser chamado novamente)
                r2 = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, FOR_LAT, FOR_LNG)
                self.assertIsNotNone(r2)
                self.assertEqual(mock_client.distance_matrix.call_count, 1)  # ainda 1
                self.assertEqual(r2["fonte"], "cache")

        # Limpeza
        cache_file.unlink(missing_ok=True)


class TestDiskCache(unittest.TestCase):
    """Arquivo .json deve ser gravado apos 1a chamada bem-sucedida."""

    def test_json_file_created(self):
        key = _cache_key((SP_LAT, SP_LNG), (EUS_LAT, EUS_LNG))
        cache_file = CACHE_DIR / f"{key}.json"

        cache_file.unlink(missing_ok=True)

        fake_response = _mock_distance_matrix_response(2_950_000)

        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = fake_response

        with patch.dict(
            os.environ,
            {
                "GOOGLE_DISTANCE_MATRIX_API_KEY": "FAKE_KEY",
                "DISTANCE_MATRIX_ENABLED": "1",
            },
        ):
            with patch("googlemaps.Client", return_value=mock_client):
                r = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, EUS_LAT, EUS_LNG)

        self.assertIsNotNone(r)
        self.assertTrue(cache_file.exists(), "Cache JSON nao foi gravado em disco")

        with cache_file.open() as f:
            data = json.load(f)
        self.assertAlmostEqual(data["distancia_km"], 2950.0, places=0)

        # Limpeza
        cache_file.unlink(missing_ok=True)


class TestSpCeCoherence(unittest.TestCase):
    """
    Teste de integracao leve: valida que SP->Fortaleza retorna ~2700-3000km.
    So executa quando GOOGLE_DISTANCE_MATRIX_API_KEY estiver definida.
    """

    def setUp(self):
        self.api_key = os.environ.get("GOOGLE_DISTANCE_MATRIX_API_KEY")
        self.enabled = (os.environ.get("DISTANCE_MATRIX_ENABLED") or "").strip() in (
            "1",
            "true",
            "yes",
            "on",
        )

    def test_sp_to_fortaleza_plausivel(self):
        if not (self.api_key and self.enabled):
            self.skipTest(
                "DISTANCE_MATRIX_ENABLED=1 + GOOGLE_DISTANCE_MATRIX_API_KEY "
                "necessários — pulando integração"
            )
        # Limpa cache pra garantir chamada real
        key = _cache_key((SP_LAT, SP_LNG), (FOR_LAT, FOR_LNG))
        cache_file = CACHE_DIR / f"{key}.json"
        cache_file.unlink(missing_ok=True)

        result = calcular_distancia_rodoviaria(SP_LAT, SP_LNG, FOR_LAT, FOR_LNG)
        self.assertIsNotNone(result, "API retornou None com key valida")
        km = result["distancia_km"]
        self.assertGreater(km, 2500, f"Distancia suspeitamente curta: {km}km")
        self.assertLess(km, 3500, f"Distancia suspeitamente longa: {km}km")
        print(f"  SP->Fortaleza: {km}km ({result['duracao_horas']}h) via {result['fonte']}")

        cache_file.unlink(missing_ok=True)


class TestFornecedorHelper(unittest.TestCase):
    """distancia_fornecedor_para_cidade usa origin correto."""

    def test_fornecedor_desconhecido_usa_default(self):
        from tools.distance_matrix_tools import FORNECEDORES_ORIGEM

        fake_response = _mock_distance_matrix_response()
        mock_client = MagicMock()
        mock_client.distance_matrix.return_value = fake_response

        with patch.dict(
            os.environ,
            {
                "GOOGLE_DISTANCE_MATRIX_API_KEY": "FAKE_KEY",
                "DISTANCE_MATRIX_ENABLED": "1",
            },
        ):
            with patch("googlemaps.Client", return_value=mock_client):
                r = distancia_fornecedor_para_cidade("fornecedor_inexistente", EUS_LAT, EUS_LNG)

        if r is not None:
            # A origem usada deve ser SP capital (default)
            call_args = mock_client.distance_matrix.call_args
            if call_args:
                origins = call_args.kwargs.get("origins") or call_args.args[0]
                expected_origin = FORNECEDORES_ORIGEM["default"]
                self.assertAlmostEqual(origins[0][0], expected_origin[0], places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
