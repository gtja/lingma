from __future__ import annotations


def build_test_case_title(description: str | None, fallback_title: str, max_length: int = 200) -> str:
    """Use case description as title; fallback only when description is empty."""
    normalized = (description or "").strip()
    if not normalized:
        normalized = fallback_title.strip()
    return normalized[:max_length]
