"""Normalizes raw OCR text into an Indian plate string, per the project
brief: "Normalize plate strings: uppercase, strip spaces, map Indian state
codes to standard 2-letter codes."

Standard format: SS DD L[LL] DDDD (state code, RTO district code, one-to-
three series letters, four-digit number) — e.g. "GJ01AB1234". Two-line
plates commonly OCR with the wrong split or missing characters, so this
also tries a small, bounded set of single-character corrections for
characters ANPR/OCR confuses visually (0/O, 1/I, 8/B, 5/S, 2/Z) — but only
ever accepts a correction if applying it makes an otherwise-invalid string
match the valid format; it never "corrects" an already-valid plate.
"""

from __future__ import annotations

import re

# Real Indian state/UT RTO codes — used to validate the region prefix
# rather than trust whatever two letters OCR produced.
_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
    "HR", "HP", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TS", "TR", "UK", "UP", "WB",
}

_PLATE_RE = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})$")

_CONFUSABLES: dict[str, list[str]] = {
    "0": ["O"], "O": ["0"],
    "1": ["I"], "I": ["1"],
    "8": ["B"], "B": ["8"],
    "5": ["S"], "S": ["5"],
    "2": ["Z"], "Z": ["2"],
}


def _clean(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


def _is_valid(plate: str) -> bool:
    match = _PLATE_RE.match(plate)
    return bool(match) and match.group(1) in _STATE_CODES


def _try_single_char_corrections(plate: str) -> str | None:
    for i, ch in enumerate(plate):
        for alt in _CONFUSABLES.get(ch, []):
            candidate = plate[:i] + alt + plate[i + 1 :]
            if _is_valid(candidate):
                return candidate
    return None


def normalize(raw_text: str) -> tuple[str, str] | None:
    """Returns (normalized_plate, region) if `raw_text` is or can be
    corrected into a valid-format Indian plate, else None. `region` is the
    2-letter state code, guaranteed to be a real one if returned.
    """
    cleaned = _clean(raw_text)
    if not cleaned:
        return None

    if _is_valid(cleaned):
        return cleaned, cleaned[:2]

    corrected = _try_single_char_corrections(cleaned)
    if corrected is not None:
        return corrected, corrected[:2]

    return None
