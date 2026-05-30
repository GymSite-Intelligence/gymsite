"""Configurações do módulo de prospecção."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "gymsite_intelligence" / ".env", override=False)


class Config:
    """Settings carregadas de variáveis de ambiente."""

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    # Webhook do Claw / Vectra
    CLAW_WEBHOOK_URL: str = os.getenv("CLAW_WEBHOOK_URL", "").strip()
    CLAW_WEBHOOK_SECRET: str = os.getenv("CLAW_WEBHOOK_SECRET", "").strip()

    # Diretório de dados CNO (CSV local)
    CNO_DATA_DIR: str = os.getenv("CNO_DATA_DIR", "").strip()
    CNO_DATA_DIR_HOST: str = os.getenv("CNO_DATA_DIR_HOST", "").strip()

    # Thresholds
    SCORE_MATCH_MIN: float = float(os.getenv("PROSPECCAO_SCORE_MIN", "0.5"))
    WEBHOOK_MAX_RETRIES: int = int(os.getenv("PROSPECCAO_WEBHOOK_RETRIES", "3"))
    WEBHOOK_TIMEOUT_SECONDS: int = int(os.getenv("PROSPECCAO_WEBHOOK_TIMEOUT", "10"))

    @classmethod
    def resolve_cno_dir(cls) -> Path | None:
        for d in (cls.CNO_DATA_DIR, cls.CNO_DATA_DIR_HOST):
            if d:
                p = Path(d)
                if p.is_dir():
                    return p
        return None
