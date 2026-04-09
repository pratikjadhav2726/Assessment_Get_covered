from pydantic import BaseModel, Field, HttpUrl
from typing import Literal


ResultState = Literal[
    "found",
    "not_found",
    "protected_or_blocked",
    "invalid_input",
    "timeout",
    "scan_error",
]


class ScanRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL to scan for auth markup")


class ScanResponse(BaseModel):
    input_url: str
    state: ResultState
    found: bool
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    detection_signals: list[str]
    html_snippet: str | None = None
    message: str
