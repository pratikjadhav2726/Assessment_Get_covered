from bs4 import BeautifulSoup, Tag


class DOMService:
    @staticmethod
    def parse(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def iter_candidate_containers(soup: BeautifulSoup) -> list[Tag]:
        candidates: list[Tag] = []
        seen: set[int] = set()
        for tag in soup.find_all(["form", "div", "section", "article", "main", "aside", "dialog"]):
            if not isinstance(tag, Tag):
                continue
            key = id(tag)
            if key in seen:
                continue
            classes = " ".join(tag.get("class", []))
            marker_text = f"{tag.get('id', '')} {classes}".lower()
            contains_password = tag.find("input", attrs={"type": "password"}) is not None
            contains_user_inputs = tag.find(
                "input", attrs={"type": lambda value: value in {"email", "text", "tel"} if value else False}
            ) is not None
            has_auth_button = tag.find(["button", "a"], string=lambda text: bool(text and "sign" in text.lower())) is not None
            auth_marker = any(
                token in marker_text
                for token in ("login", "signin", "sign-in", "auth", "password", "account", "session")
            )
            if tag.name == "form" or contains_password or contains_user_inputs or has_auth_button or auth_marker:
                candidates.append(tag)
                seen.add(key)
        return candidates
