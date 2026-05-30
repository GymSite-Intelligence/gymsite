"""
Testes unitários para o módulo de prospecção (webhook e alteração de status).
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Garante que a raiz está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prospecting.webhook import send_opportunity_webhook
from prospecting.engine import update_status, OportunidadeNotFoundError, WebhookDeliveryError


class TestWebhookAndStatus(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.oportunidade = {
            "id": "test-uuid-123",
            "cnpj": "12.345.678/0001-99",
            "cno": "12345",
            "razao_social": "ACADEMIA FORTE LTDA",
            "cidade": "Fortaleza",
            "uf": "CE",
            "score_match": 0.85,
            "prioridade": "alta",
            "webhook_url": "https://fake-url.com/webhook",
        }

    @patch("requests.post")
    def test_send_webhook_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Success"
        mock_post.return_value = mock_resp

        # Mock ja_enviado_com_sucesso para retornar False
        with patch("prospecting.webhook._ja_enviado_com_sucesso", return_value=False):
            result = send_opportunity_webhook(self.oportunidade, client=self.mock_client)

        self.assertEqual(result["status"], "entregue")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["tentativas"], 1)

        # Verifica se as tabelas corretas do Supabase foram chamadas para persistência/log
        self.mock_client.table.assert_any_call("oportunidades_prospeccao")
        self.mock_client.table.assert_any_call("webhook_claw_log")

    @patch("requests.post")
    @patch("time.sleep")  # acelera execução dos retries
    def test_send_webhook_retry_and_fail(self, mock_sleep, mock_post):
        mock_post.side_effect = Exception("Connection Timeout")

        with patch("prospecting.webhook._ja_enviado_com_sucesso", return_value=False):
            result = send_opportunity_webhook(self.oportunidade, client=self.mock_client)

        self.assertEqual(result["status"], "falhou")
        self.assertEqual(result["tentativas"], 3)  # default max_retries é 3
        self.assertEqual(mock_post.call_count, 3)

    def test_send_webhook_idempotency(self):
        with patch("prospecting.webhook._ja_enviado_com_sucesso", return_value=True):
            result = send_opportunity_webhook(self.oportunidade, client=self.mock_client)

        self.assertEqual(result["status"], "idempotente")
        self.assertEqual(result["motivo"], "Webhook já entregue com sucesso")

    @patch("prospecting.engine.get_oportunidade")
    @patch("prospecting.engine.send_opportunity_webhook")
    def test_update_status_webhook_enviado_success(self, mock_send, mock_get):
        mock_get.return_value = self.oportunidade
        mock_send.return_value = {"status": "entregue", "http_status": 200}

        # Mock do supabase client
        with patch("prospecting.engine._get_client", return_value=self.mock_client):
            ok = update_status("test-uuid-123", "webhook_enviado")
            self.assertTrue(ok)
            mock_send.assert_called_once_with(self.oportunidade, client=self.mock_client)

    @patch("prospecting.engine.get_oportunidade")
    @patch("prospecting.engine.send_opportunity_webhook")
    def test_update_status_webhook_enviado_failure(self, mock_send, mock_get):
        mock_get.return_value = self.oportunidade
        mock_send.return_value = {"status": "falhou", "motivo": "HTTP 500"}

        with patch("prospecting.engine._get_client", return_value=self.mock_client):
            with self.assertRaises(WebhookDeliveryError):
                update_status("test-uuid-123", "webhook_enviado")

    @patch("prospecting.engine.get_oportunidade")
    def test_update_status_not_found(self, mock_get):
        mock_get.return_value = None

        with patch("prospecting.engine._get_client", return_value=self.mock_client):
            with self.assertRaises(OportunidadeNotFoundError):
                update_status("invalid-uuid", "qualificado")


if __name__ == "__main__":
    unittest.main(verbosity=2)
