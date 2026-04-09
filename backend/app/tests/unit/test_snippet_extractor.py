from bs4 import BeautifulSoup

from app.services.snippet_extractor import SnippetExtractor


def test_extract_returns_container_markup() -> None:
    soup = BeautifulSoup("<form><input type='password' /></form>", "lxml")
    form = soup.find("form")
    snippet = SnippetExtractor.extract(form)
    assert snippet is not None
    assert "<input" in snippet
