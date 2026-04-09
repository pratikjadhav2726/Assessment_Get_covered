from app.services.auth_detector import AuthDetector
from app.services.dom_service import DOMService
from app.services.snippet_extractor import SnippetExtractor


def test_pipeline_finds_login_form_from_fixture_html() -> None:
    html = """
    <html><body>
      <section class="auth-wrapper">
        <form>
          <label>Email</label>
          <input type="email" name="email" />
          <label>Password</label>
          <input type="password" name="password" />
          <button type="submit">Log in</button>
        </form>
      </section>
    </body></html>
    """
    soup = DOMService.parse(html)
    candidates = DOMService.iter_candidate_containers(soup)
    detection = AuthDetector().score(candidates)
    snippet = SnippetExtractor.extract(detection.container)
    assert detection.container is not None
    assert detection.confidence >= 0.5
    assert snippet is not None
    assert "password" in snippet.lower()


def test_pipeline_returns_low_confidence_for_non_auth_fixture() -> None:
    html = """
    <html><body>
      <form>
        <label>Search</label>
        <input type="text" name="query" />
        <button type="submit">Submit</button>
      </form>
    </body></html>
    """
    soup = DOMService.parse(html)
    candidates = DOMService.iter_candidate_containers(soup)
    detection = AuthDetector().score(candidates)
    assert detection.confidence < 0.5
