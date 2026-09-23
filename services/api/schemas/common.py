from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """The shape every error response takes (see main.py exception handlers)."""

    detail: str
    code: str
