from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone


class AuditLogger:
    def __init__(self, verbose: bool = False) -> None:
        level = logging.DEBUG if verbose else logging.INFO
        self._log = logging.getLogger("security_audit")
        self._log.setLevel(level)
        self._log.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        self._log.addHandler(handler)

    def info(self, msg: str) -> None:
        self._log.info(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)

    def critical(self, msg: str) -> None:
        self._log.critical(msg)

    def debug(self, msg: str) -> None:
        self._log.debug(msg)

    @staticmethod
    def ts() -> str:
        return datetime.now(timezone.utc).isoformat()
