"""Merge CI secrets into audit-config for security-audit workflow."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "security_audit" / "audit-config.gymsite.json"
OUT = ROOT / "artifacts" / "security" / "audit-config.ci.json"


def main() -> None:
    cfg = json.loads(SRC.read_text(encoding="utf-8"))
    rel_a = (os.getenv("SECURITY_AUDIT_RELATORIO_USER_A") or "").strip()
    rel_b = (os.getenv("SECURITY_AUDIT_RELATORIO_USER_B") or "").strip()
    if rel_a:
        cfg["user_a_id"] = rel_a
    if rel_b:
        cfg["user_b_id"] = rel_b
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
