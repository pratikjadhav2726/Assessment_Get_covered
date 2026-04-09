from bs4 import BeautifulSoup

from app.services.auth_detector import AuthDetector
from app.services.dom_service import DOMService


def test_auth_detector_scores_login_form_high() -> None:
    html = """
    <html><body>
      <form id="login-form">
        <input type="email" name="email" placeholder="Email" />
        <input type="password" name="password" placeholder="Password" />
        <button type="submit">Sign in</button>
      </form>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    candidates = DOMService.iter_candidate_containers(soup)
    result = AuthDetector().score(candidates)
    assert result.container is not None
    assert result.confidence >= 0.5
    assert "password_input_present" in result.signals
