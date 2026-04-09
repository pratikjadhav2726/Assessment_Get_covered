from dataclasses import dataclass
from bs4 import Tag


AUTH_BUTTON_TERMS = ("login", "log in", "sign in", "signin", "continue")
USER_FIELD_TERMS = ("email", "username", "user", "phone")
FEDERATED_TERMS = ("continue with google", "continue with apple", "continue with email", "google", "apple", "oauth")
AUTH_TEXT_TERMS = (
    "sign in to your account",
    "welcome back",
    "password",
    "forgot password",
    "remember me",
    "continue with",
    "one-time code",
    "one-time link",
    "email me a link",
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

        password_inputs = node.find_all(
            "input",
            attrs={"type": lambda value: value in {"password", "current-password", "new-password"} if value else False},
        )
        if password_inputs:
            score += 0.45
            signals.append("password_input_present")

        user_inputs = node.find_all(
            "input",
            attrs={"type": lambda value: value in {"text", "email", "tel"} if value else False},  # type: ignore[arg-type]
        )
        user_match = False
        for user_input in user_inputs:
            attrs_text = " ".join(
                [
                    user_input.get("name", ""),
                    user_input.get("id", ""),
                    user_input.get("placeholder", ""),
                    user_input.get("autocomplete", ""),
                    user_input.get("aria-label", ""),
                    user_input.get("data-testid", ""),
                ]
            ).lower()
            if any(t in attrs_text for t in USER_FIELD_TERMS):
                user_match = True
                break
        if user_match:
            score += 0.2
            signals.append("username_or_email_input_present")

        if password_inputs and user_inputs:
            score += 0.15
            signals.append("password_and_user_inputs_nearby")

        if node.name == "form":
            score += 0.1
            signals.append("form_container_present")

        buttons_text = " ".join(
            btn.get_text(" ", strip=True).lower() for btn in node.find_all(["button", "a", "span", "div"])
        )
        if any(term in buttons_text for term in AUTH_BUTTON_TERMS):
            score += 0.15
            signals.append("auth_button_present")
        if any(term in buttons_text for term in FEDERATED_TERMS):
            score += 0.2
            signals.append("federated_auth_option_present")

        nearby_text = node.get_text(" ", strip=True).lower()[:5000]
        if any(term in nearby_text for term in AUTH_TEXT_TERMS):
            score += 0.1
            signals.append("auth_related_text_present")
        if any(term in nearby_text for term in ("continue with", "one-time", "magic link", "use email")):
            score += 0.15
            signals.append("passwordless_auth_flow_present")

        return score, signals
