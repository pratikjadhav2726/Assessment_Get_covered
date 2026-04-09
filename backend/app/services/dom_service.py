from bs4 import BeautifulSoup, Tag


class DOMService:
    @staticmethod
    def parse(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def iter_candidate_containers(soup: BeautifulSoup) -> list[Tag]:
        candidates: list[Tag] = []
        for tag in soup.find_all(["form", "div", "section", "article"]):
            if not isinstance(tag, Tag):
                continue
            classes = " ".join(tag.get("class", []))
            marker_text = f"{tag.get('id', '')} {classes}".lower()
            contains_password = tag.find("input", attrs={"type": "password"}) is not None
            auth_marker = any(
                token in marker_text
                for token in ("login", "signin", "sign-in", "auth", "password", "account")
            )
            if tag.name == "form" or contains_password or auth_marker:
                candidates.append(tag)
        return candidates
