from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag


class LongSummaryParseError(ValueError):
    """Raised when a Long Summary section cannot be extracted."""


@dataclass(slots=True)
class ParsedChapter:
    title: str
    paragraphs: list[str]


def _clean_text(tag: Tag) -> str:
    clone = BeautifulSoup(str(tag), "html.parser")
    for removable in clone.select(
        "sup.reference, .mw-editsection, style, script, .portable-infobox, .navbox"
    ):
        removable.decompose()
    text = " ".join(clone.stripped_strings)
    return re.sub(r"\s+", " ", text).strip()


def _heading_level(tag: Tag) -> int | None:
    if tag.name and re.fullmatch(r"h[1-6]", tag.name):
        return int(tag.name[1])
    return None


def _normalized_heading_text(tag: Tag) -> str:
    text = " ".join(tag.stripped_strings)
    text = re.sub(r"\[edit\]", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" []\n\t").strip()


def extract_chapter_title(soup: BeautifulSoup, chapter_number: int) -> str:
    """Extract the story title shown near the top of a standard chapter page."""
    ignored = {
        "chapter info",
        "cover page",
        "short summary",
        "long summary",
        "quick reference",
        "author comment",
        "trivia",
        "site navigation",
    }

    for heading in soup.find_all(["h2", "h3"]):
        text = _normalized_heading_text(heading)
        normalized = text.casefold()
        if not text or normalized in ignored:
            continue
        if normalized.startswith("chapter "):
            continue
        return text

    return f"Chapter {chapter_number}"


def _find_long_summary_heading(soup: BeautifulSoup) -> Tag | None:
    marker = soup.find(id="Long_Summary")
    if isinstance(marker, Tag):
        heading = marker if _heading_level(marker) else marker.find_parent(re.compile(r"^h[1-6]$"))
        if isinstance(heading, Tag):
            return heading

    for heading in soup.find_all(re.compile(r"^h[1-6]$")):
        if _normalized_heading_text(heading).casefold() == "long summary":
            return heading

    return None


def parse_long_summary(html: str, chapter_number: int) -> ParsedChapter:
    """Extract only the Long Summary section from a One Piece Wiki chapter page."""
    soup = BeautifulSoup(html, "html.parser")
    summary_heading = _find_long_summary_heading(soup)
    if summary_heading is None:
        raise LongSummaryParseError("Long Summary section was not found on the wiki page.")

    summary_level = _heading_level(summary_heading) or 2
    paragraphs: list[str] = []

    for sibling in summary_heading.next_siblings:
        if isinstance(sibling, NavigableString):
            continue
        if not isinstance(sibling, Tag):
            continue

        level = _heading_level(sibling)
        if level is not None and level <= summary_level:
            break

        candidates = [sibling] if sibling.name == "p" else sibling.find_all("p")
        for paragraph in candidates:
            text = _clean_text(paragraph)
            if text:
                paragraphs.append(text)

    if not paragraphs:
        raise LongSummaryParseError(
            "Long Summary section was found, but it contained no readable text."
        )

    return ParsedChapter(
        title=extract_chapter_title(soup, chapter_number),
        paragraphs=paragraphs,
    )
