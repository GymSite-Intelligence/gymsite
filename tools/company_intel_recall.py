"""Normalize company names for golden recall scoring."""
from __future__ import annotations

import re
import unicodedata


def normalize_importer_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # RFB / exports oscillate between "S A", "S/A", "SA"
    s = re.sub(r"\bS A\b", "SA", s)
    return s


def recall_at_k(
    golden_names: list[str],
    candidate_names: list[str],
    k: int | None = None,
) -> dict:
    """Fraction of golden importers found in the first k candidates (by order)."""
    gold = {normalize_importer_name(n) for n in golden_names if n}
    gold.discard("")
    cands = [normalize_importer_name(n) for n in candidate_names if n]
    if k is not None:
        cands = cands[:k]
    cand_set = set(cands)
    hits = sorted(gold & cand_set)
    misses = sorted(gold - cand_set)
    denom = len(gold) or 1
    return {
        "n_golden": len(gold),
        "n_candidates_scored": len(cands),
        "k": k,
        "hits": hits,
        "misses": misses,
        "recall": len(hits) / denom,
    }
