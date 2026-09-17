# One Piece Book Edition

A small FastAPI application that retrieves the **Long Summary** section of numbered One Piece manga chapter pages from the One Piece Wiki on Fandom and presents it in a clean book-like reader.

The app fetches chapters only when requested. Because One Piece is ongoing, there is no hard-coded final chapter: the reader checks whether the next numbered chapter exists before showing the Next link.

## Features

- Long Summary reader at `/chapter/{number}`
- Previous/next chapter navigation
- Left/right arrow-key navigation
- Chapter number picker
- JSON API at `/api/chapters/{number}`
- On-demand Fandom/MediaWiki fetching
- In-memory caching
- Parser that stops at the end of **Long Summary**
- FastAPI docs at `/docs`
- One-command Windows startup
- Docker and Render deployment configuration

## Run locally

### Windows — one command

After cloning the repository, run:

```bat
run.bat
```

The script creates `.venv` when necessary, installs/updates dependencies, and starts Uvicorn. Then open <http://127.0.0.1:8000>.

Press `CTRL+C` to stop the server.

### Manual Python setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

```text
GET /api/chapters/1
GET /api/chapters/500
GET /api/chapters/1000
```

Response shape:

```json
{
  "chapter": 1,
  "title": "Romance Dawn —The Dawn of the Adventure—",
  "paragraphs": ["..."],
  "text": "...",
  "source": "https://onepiece.fandom.com/wiki/Chapter_1"
}
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Deploy on Render

The repository includes `render.yaml`. Create a new Render Blueprint/Web Service from this repository. Render installs the dependencies and starts the application with Uvicorn.

## How extraction works

The backend requests `Chapter_N` through Fandom's MediaWiki API, parses the rendered article HTML, locates the **Long Summary** heading, and collects its prose until the next top-level section. It therefore excludes the separate Short Summary, Quick Reference, trivia, and other page content.

## Attribution

Long Summary text is retrieved from the [One Piece Wiki on Fandom](https://onepiece.fandom.com/). The reader links every chapter back to its source article. Wiki text remains subject to the applicable Fandom community licensing and attribution requirements.

One Piece and related names and characters are property of their respective rights holders. This project is an independent reader and is not affiliated with One Piece, Shueisha, or Fandom.
