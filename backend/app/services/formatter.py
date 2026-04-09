from app.api.schemas import ScanResponse


class ResponseFormatter:
    @staticmethod
    def found(
        input_url: str,
        source: str,
        confidence: float,
        detection_signals: list[str],
        html_snippet: str | None,
    ) -> ScanResponse:
        return ScanResponse(
            input_url=input_url,
            state="found",
            found=True,
            confidence=confidence,
            source=source,
            detection_signals=detection_signals,
            html_snippet=html_snippet,
            message="Authentication markup detected.",
        )

    @staticmethod
    def not_found(input_url: str, source: str) -> ScanResponse:
        return ScanResponse(
            input_url=input_url,
            state="not_found",
            found=False,
            confidence=0.0,
            source=source,
            detection_signals=[],
            html_snippet=None,
            message="No authentication component was detected.",
        )

    @staticmethod
    def failure(input_url: str, state: str, message: str) -> ScanResponse:
        return ScanResponse(
            input_url=input_url,
            state=state,  # type: ignore[arg-type]
            found=False,
            confidence=0.0,
            source="backend_scan_pipeline",
            detection_signals=[],
            html_snippet=None,
            message=message,
        )
