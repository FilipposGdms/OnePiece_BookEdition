from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from app.parser import LongSummaryParseError, parse_long_summary

WIKI_BASE_URL = "https://onepiece.fandom.com"
API_URL = f"{WIKI_BASE_URL}/api.php"
MIN_CHAPTER = 1
MAX_REASONABLE_CHAPTER = 5000
CACHE_TTL_SECONDS = 60 * 60
EXISTENCE_CACHE_TTL_SECONDS = 15 * 60
LATEST_CHAPTER_CACHE_TTL_SECONDS = 60 * 60
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT = "OnePieceBookEdition/1.0 (personal reader; chapter summaries from One Piece Wiki)"


class ChapterFetchError(RuntimeError):
    """Raised when the upstream wiki cannot be reached or parsed."""


class ChapterNotFoundError(ChapterFetchError):
    """Raised when a requested numbered chapter does not exist."""


@dataclass(slots=True)
class Chapter:
    number: int
    title: str
    paragraphs: list[str]
    source_url: str


_chapter_cache: dict[int, tuple[float, Chapter]] = {}
_existence_cache: dict[int, tuple[float, bool]] = {}
_latest_chapter_cache: tuple[float, int] | None = None
_cache_lock = asyncio.Lock()


def chapter_source_url(chapter_number: int) -> str:
    return f"{WIKI_BASE_URL}/wiki/Chapter_{chapter_number}"


def _validate_chapter_number(chapter_number: int) -> None:
    if not MIN_CHAPTER <= chapter_number <= MAX_REASONABLE_CHAPTER:
        raise ChapterNotFoundError(
            f"Chapter number must be between {MIN_CHAPTER} and {MAX_REASONABLE_CHAPTER}."
        )


def _fresh(timestamp: float, ttl: int) -> bool:
    return time.monotonic() - timestamp < ttl


async def get_latest_chapter_number() -> int:
    """Return the highest numbered chapter page currently present on One Piece Wiki."""
    global _latest_chapter_cache

    async with _cache_lock:
        cached = _latest_chapter_cache
        if cached and _fresh(cached[0], LATEST_CHAPTER_CACHE_TTL_SECONDS):
            return cached[1]
        stale_latest = cached[1] if cached else None

    params: dict[str, str] = {
        "action": "query",
        "list": "allpages",
        "apprefix": "Chapter ",
        "apnamespace": "0",
        "aplimit": "max",
        "format": "json",
        "formatversion": "2",
    }
    latest = 0

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            while True:
                response = await client.get(API_URL, params=params)
                response.raise_for_status()
                payload = response.json()

                for page in payload.get("query", {}).get("allpages", []):
                    title = str(page.get("title", ""))
                    match = re.fullmatch(r"Chapter[ _](\d+)", title)
                    if match:
                        latest = max(latest, int(match.group(1)))

                continuation = payload.get("continue")
                if not isinstance(continuation, dict) or "apcontinue" not in continuation:
                    break
                params["apcontinue"] = str(continuation["apcontinue"])
                params["continue"] = str(continuation.get("continue", "-||"))
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        if stale_latest is not None:
            return stale_latest
        raise ChapterFetchError("Could not determine the latest chapter from One Piece Wiki.") from exc

    if latest < MIN_CHAPTER:
        if stale_latest is not None:
            return stale_latest
        raise ChapterFetchError("Could not determine the latest chapter from One Piece Wiki.")

    async with _cache_lock:
        _latest_chapter_cache = (time.monotonic(), latest)

    return latest


async def fetch_chapter(chapter_number: int) -> Chapter:
    _validate_chapter_number(chapter_number)

    async with _cache_lock:
        cached = _chapter_cache.get(chapter_number)
        if cached and _fresh(cached[0], CACHE_TTL_SECONDS):
            return cached[1]

    params = {
        "action": "parse",
        "page": f"Chapter_{chapter_number}",
        "prop": "text",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ChapterFetchError("Could not retrieve the chapter from One Piece Wiki.") from exc

    if "error" in payload:
        error_code = str(payload["error"].get("code", ""))
        if error_code in {"missingtitle", "invalidtitle"}:
            raise ChapterNotFoundError(f"Chapter {chapter_number} was not found.")
        raise ChapterFetchError(
            str(payload["error"].get("info", "One Piece Wiki returned an error."))
        )

    html = payload.get("parse", {}).get("text")
    if not isinstance(html, str) or not html.strip():
        raise ChapterNotFoundError(f"Chapter {chapter_number} was not found.")

    try:
        parsed = parse_long_summary(html, chapter_number)
    except LongSummaryParseError as exc:
        raise ChapterFetchError(str(exc)) from exc

    chapter = Chapter(
        number=chapter_number,
        title=parsed.title,
        paragraphs=parsed.paragraphs,
        source_url=chapter_source_url(chapter_number),
    )

    async with _cache_lock:
        _chapter_cache[chapter_number] = (time.monotonic(), chapter)
        _existence_cache[chapter_number] = (time.monotonic(), True)

    return chapter


async def chapter_exists(chapter_number: int) -> bool:
    if not MIN_CHAPTER <= chapter_number <= MAX_REASONABLE_CHAPTER:
        return False

    async with _cache_lock:
        cached = _existence_cache.get(chapter_number)
        if cached and _fresh(cached[0], EXISTENCE_CACHE_TTL_SECONDS):
            return cached[1]
        chapter_cached = _chapter_cache.get(chapter_number)
        if chapter_cached and _fresh(chapter_cached[0], CACHE_TTL_SECONDS):
            return True

    params = {
        "action": "query",
        "titles": f"Chapter_{chapter_number}",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return True

    pages = payload.get("query", {}).get("pages", [])
    exists = bool(pages) and "missing" not in pages[0]

    async with _cache_lock:
        _existence_cache[chapter_number] = (time.monotonic(), exists)

    return exists
