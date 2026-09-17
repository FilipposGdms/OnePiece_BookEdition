from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.fandom import (
    MIN_CHAPTER,
    ChapterFetchError,
    ChapterNotFoundError,
    fetch_chapter,
    get_latest_chapter_number,
)

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="One Piece Book Edition",
    description="Read One Piece Wiki Long Summaries in a book-like format.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", include_in_schema=False)
async def home() -> RedirectResponse:
    return RedirectResponse(url="/chapter/1", status_code=302)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/chapters/{chapter_number}")
async def chapter_api(chapter_number: int) -> dict[str, object]:
    try:
        latest_chapter = await get_latest_chapter_number()
        if not MIN_CHAPTER <= chapter_number <= latest_chapter:
            raise HTTPException(
                status_code=404,
                detail=f"Chapter number must be between {MIN_CHAPTER} and {latest_chapter}.",
            )
        chapter = await fetch_chapter(chapter_number)
    except ChapterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChapterFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "chapter": chapter.number,
        "title": chapter.title,
        "paragraphs": chapter.paragraphs,
        "text": "\n\n".join(chapter.paragraphs),
        "source": chapter.source_url,
        "latest_chapter": latest_chapter,
    }


@app.get("/chapter/{chapter_number}", response_class=HTMLResponse)
async def chapter_reader(request: Request, chapter_number: int) -> HTMLResponse:
    try:
        latest_chapter = await get_latest_chapter_number()
    except ChapterFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not MIN_CHAPTER <= chapter_number <= latest_chapter:
        return templates.TemplateResponse(
            request=request,
            name="chapter_error.html",
            status_code=404,
            context={
                "requested_chapter": chapter_number,
                "min_chapter": MIN_CHAPTER,
                "latest_chapter": latest_chapter,
            },
        )

    try:
        chapter = await fetch_chapter(chapter_number)
    except ChapterNotFoundError:
        return templates.TemplateResponse(
            request=request,
            name="chapter_error.html",
            status_code=404,
            context={
                "requested_chapter": chapter_number,
                "min_chapter": MIN_CHAPTER,
                "latest_chapter": latest_chapter,
            },
        )
    except ChapterFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="reader.html",
        context={
            "chapter": chapter,
            "min_chapter": MIN_CHAPTER,
            "latest_chapter": latest_chapter,
            "previous_chapter": chapter.number - 1 if chapter.number > MIN_CHAPTER else None,
            "next_chapter": chapter.number + 1 if chapter.number < latest_chapter else None,
        },
    )
