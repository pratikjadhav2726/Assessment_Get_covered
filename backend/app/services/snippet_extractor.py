from bs4 import Tag

from app.core.config import settings


class SnippetExtractor:
    @staticmethod
    def extract(container: Tag | None) -> str | None:
        if container is None:
            return None
        snippet = str(container)
        if len(snippet) > settings.max_snippet_chars:
            return snippet[: settings.max_snippet_chars] + "\n<!-- snippet truncated -->"
        return snippet
