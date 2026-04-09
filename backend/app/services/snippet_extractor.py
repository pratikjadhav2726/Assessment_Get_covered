from bs4 import Tag

from app.core.config import settings


class SnippetExtractor:
    @staticmethod
    def extract(container: Tag | None) -> str | None:
        if container is None:
            return None
        target = SnippetExtractor._best_auth_container(container)
        snippet = str(target)
        if len(snippet) > settings.max_snippet_chars:
            return snippet[: settings.max_snippet_chars] + "\n<!-- snippet truncated -->"
        return snippet

    @staticmethod
    def _best_auth_container(container: Tag) -> Tag:
        password_input = container.find("input", attrs={"type": "password"})
        if password_input is None:
            form_candidate = container.find("form")
            if isinstance(form_candidate, Tag):
                return form_candidate
            auth_marked = container.find(
                ["div", "section", "article", "main", "dialog", "slot"],
                string=lambda value: bool(value and any(t in value.lower() for t in ("sign in", "continue with", "one-time", "email"))),
            )
            if isinstance(auth_marked, Tag):
                return auth_marked
            return container

        current: Tag | None = password_input if isinstance(password_input, Tag) else container
        best: Tag = container
        while current is not None and isinstance(current, Tag):
            if current.name in {"form", "section", "div", "article", "main", "dialog"}:
                candidate_html = str(current)
                if len(candidate_html) <= settings.max_snippet_chars:
                    best = current
            parent = current.parent
            if not isinstance(parent, Tag):
                break
            current = parent

        return best
