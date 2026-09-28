"""Shared line-combining convention for OCR engines.

ocr_engine.py (PaddleOCR, primary) and ocr_fallback.py (EasyOCR,
secondary) both read a plate crop's text as separate per-line results
and need to turn that into one (text, confidence) pair anpr.py can treat
identically regardless of which engine produced it — per
ocr_fallback.py's own docstring, anpr.py relies on both engines being
interchangeable. That convention (top-to-bottom reading order, minimum
confidence across lines — a plate is only as trustworthy as its worst
line) used to be implemented twice, independently, one per engine; a fix
to either copy (e.g. PaddleOCR's documented shape-drift risk, or
tie-breaking on equal top_y) could silently diverge from the other
without any test catching it. Centralized here instead.
"""

from __future__ import annotations


def combine_ocr_lines(entries: list[tuple[float, str, float]]) -> tuple[str, float] | None:
    """entries: (top_y, text, confidence) per detected line, already
    filtered to non-empty text. Returns None for an empty list rather
    than making callers check first.
    """
    if not entries:
        return None

    entries = sorted(entries, key=lambda e: e[0])  # top-to-bottom reading order
    combined_text = "".join(text for _, text, _ in entries)
    min_conf = min(conf for _, _, conf in entries)
    return combined_text, min_conf
