from dataclasses import dataclass
from bs4 import Tag


AUTH_BUTTON_TERMS = ("login", "log in", "sign in", "signin", "continue")
USER_FIELD_TERMS = ("email", "username", "user", "phone")
AUTH_TEXT_TERMS = (
    "sign in to your account",
    "welcome back",
    "password",
    "forgot password",
    "remember me",
)


@dataclass(frozen=True)
class DetectionResult:
    container: Tag | None
    confidence: float
    signals: list[str]


class AuthDetector:
    def score(self, candidates: list[Tag]) -> DetectionResult:
        best_container: Tag | None = None
        best_score = 0.0
        best_signals: list[str] = []

        for candidate in candidates:
            score, signals = self._score_candidate(candidate)
            if score > best_score:
                best_container = candidate
                best_score = score
                best_signals = signals

        return DetectionResult(container=best_container, confidence=min(best_score, 1.0), signals=best_signals)

    def _score_candidate(self, node: Tag) -> tuple[float, list[str]]:
        score = 0.0
        signals: list[str] = []

        password_inputs = node.find_all("input", attrs={"type": "password"})
        if password_inputs:
            score += 0.55
            signals.append("password_input_present")

        username_input = node.find(
            "input",
            attrs={
                "type": lambda value: value in {"text", "email", "tel"} if value else False,  # type: ignore[arg-type]
            },
        )
        if username_input:
            attrs_text = " ".join(
                [
                    username_input.get("name", ""),
                    username_input.get("id", ""),
                    username_input.get("placeholder", ""),
                    username_input.get("autocomplete", ""),
                ]
            ).lower()
            if any(t in attrs_text for t in USER_FIELD_TERMS):
                score += 0.2
                signals.append("username_or_email_input_present")

        if node.name == "form":
            score += 0.1
            signals.append("form_container_present")

        buttons_text = " ".join(btn.get_text(" ", strip=True).lower() for btn in node.find_all(["button", "a"]))
        if any(term in buttons_text for term in AUTH_BUTTON_TERMS):
            score += 0.1
            signals.append("auth_button_present")

        nearby_text = node.get_text(" ", strip=True).lower()[:2000]
        if any(term in nearby_text for term in AUTH_TEXT_TERMS):
            score += 0.1
            signals.append("auth_related_text_present")

        return score, signals
