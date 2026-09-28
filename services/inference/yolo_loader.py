"""Shared "load a local YOLO weights file, or don't" mechanics for every
YOLO-based model in this service (plate detector, manufacturer/model
classifiers) — see plate_detector.py's and vehicle_classifier.py's
docstrings for why none of them ship with weights. This existed as three
near-identical copies of the same load/disable scaffolding; a fix to one
(e.g. an exception-handling gap) could silently miss the others.

Deliberately does NOT log anything itself and doesn't swallow a load
failure — each caller's own downstream effect when a model is missing is
different and worth its own message (plate detection missing means ANPR
reports no reads; a classifier missing means a vehicle reports
"Unknown"), and `log.exception()` needs the real traceback, not a
pre-swallowed one. Only the mechanical load step (file check, the local
`ultralytics` import, device placement) is actually identical; callers
keep their own try/except around this and their own logging.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ultralytics import YOLO


def load_yolo_model(model_path: str, device: str) -> "YOLO":
    """Raises FileNotFoundError if `model_path` doesn't exist (callers
    distinguish this from a real load failure — missing weights is
    expected/silent-ish, a load exception on a file that IS present is
    worth `log.exception`'s full traceback). Any other exception from
    ultralytics/torch propagates as-is.
    """
    if not Path(model_path).exists():
        raise FileNotFoundError(model_path)

    from ultralytics import YOLO  # local import: skip it entirely when disabled

    model = YOLO(model_path)
    model.to(device)
    return model
