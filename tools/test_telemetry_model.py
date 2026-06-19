"""_resolve_model_name: extrai nome do modelo mesmo quando build_llm_agent embrulha
a string num objeto Gemini (senão gravava o repr inteiro no custo — bug 18/06)."""
from tools.token_telemetry import _resolve_model_name


class _Gemini:
    model = "gemini-2.5-flash"

    def __repr__(self):
        return "Gemini(model='gemini-2.5-flash' retry_options=...lixo...)"


class _Agent:
    def __init__(self, m):
        self.model = m


class _IC:
    def __init__(self, ag):
        self.agent = ag


class _Ctx:
    def __init__(self, ag):
        self._invocation_context = _IC(ag)


def test_objeto_gemini_extrai_nome_limpo():
    assert _resolve_model_name(_Ctx(_Agent(_Gemini()))) == "gemini-2.5-flash"


def test_model_string_simples_mantem():
    assert _resolve_model_name(_Ctx(_Agent("gemini-2.5-pro"))) == "gemini-2.5-pro"


def test_resposta_tem_prioridade():
    class _Resp:
        model = "gemini-2.5-flash-lite"
    # llm_response.model vence o agente
    assert _resolve_model_name(_Ctx(_Agent(_Gemini())), _Resp()) == "gemini-2.5-flash-lite"


def test_sem_modelo_retorna_interrogacao():
    class _Empty:
        _invocation_context = None
    assert _resolve_model_name(_Empty()) == "?"
