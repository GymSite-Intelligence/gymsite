"""
Telemetry — OpenTelemetry helpers para spans manuais.

Uso:
    from tools.telemetry import get_tracer, span

    with span("prospeccao.executar", cidade="Fortaleza"):
        run_prospeccao(...)

O TracerProvider já é configurado automaticamente pelo opentelemetry-distro
(via env vars OTEL_*). Não chamar configure() aqui.
"""
from __future__ import annotations

import functools
from typing import Any, Callable

from opentelemetry import trace

from tools.sanitize import safe_span_attribute


def get_tracer(name: str = "gymsite") -> trace.Tracer:
    """Retorna tracer nomeado."""
    return trace.get_tracer(name)


class span:
    """Context manager / decorator para criar spans OpenTelemetry.

    Como context manager:
        with span("prospeccao.match", cidade=cidade):
            match_opportunities(...)

    Como decorator:
        @span("prospeccao.enriquecer")
        def enrich_opportunity(opp: dict) -> None:
            ...
    """

    def __init__(self, name: str, **attributes: Any) -> None:
        self.name = name
        self.attributes = attributes
        self._span: trace.Span | None = None

    def __enter__(self) -> trace.Span:
        tracer = get_tracer()
        self._span = tracer.start_span(self.name)
        for key, value in self.attributes.items():
            safe = safe_span_attribute(key, value)
            if safe:
                self._span.set_attribute(safe[0], safe[1])
            elif isinstance(value, (str, int, float, bool)):
                self._span.set_attribute(key, value)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._span:
            if exc_val:
                self._span.set_attribute("error", True)
                self._span.set_attribute("error.message", str(exc_val))
            self._span.end()

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with span(self.name, **self.attributes):
                return func(*args, **kwargs)
        return wrapper
