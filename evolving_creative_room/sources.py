from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        value = _normalize_space(data)
        if not value or self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(value)
            return
        if len(value) >= 2:
            self.text_parts.append(value)


def import_public_page(url: str, *, timeout: int = 12, max_chars: int = 5000) -> dict[str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("请输入完整的 http 或 https 链接。")
    request = Request(
        url,
        headers={
            "User-Agent": "EcRoom/0.1 (+local creative research)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read(max_chars * 8)
    html = raw.decode(charset, errors="replace")
    parser = PageTextParser()
    parser.feed(html)
    title = _normalize_space(" ".join(parser.title_parts)) or parsed.netloc
    content = _normalize_space(" ".join(parser.text_parts))
    if not content:
        content = _normalize_space(re.sub(r"<[^>]+>", " ", html))
    return {
        "title": title[:120],
        "content": content[:max_chars],
        "source": url,
    }


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
