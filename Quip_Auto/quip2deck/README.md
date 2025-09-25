# quip2deck (starter)

A minimal, end-to-end starter to convert a **Quip-like HTML** document into a **Keynote-ready deck**.
For cross-platform portability, this starter renders **.pptx** via `python-pptx` (so you can import the PPTX into Keynote).

> Thin slice implemented: HTML → AST → SlidePlan → PPTX renderer + FastAPI service.

---

## Features (MVP)
- Parse a Quip-exported (or Quip-like) HTML file
- Simple slide planning: H1/H2 start a new slide; paragraphs and lists become body content
- Creates `.pptx` with a title slide + content slides
- FastAPI: `POST /convert` accepts HTML and returns a `.pptx` artifact on disk

## Roadmap
- Quip API connector (OAuth/Token) (stubbed)
- Two-column/media/table layouts
- Speaker notes from callouts/comments
- Theming packs
- macOS Keynote Agent for native `.key` rendering (provided as a stub file)

---

## Quickstart

1) Create a venv and install deps:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Run the API:
```bash
uvicorn quip2deck.main:app --reload
```

3) Convert an example (CLI helper):
```bash
python -m quip2deck.cli examples/sample_quip.html out/apollo.pptx
```

### Feeding a real Quip

**Option A — Paste/export HTML (already works):**
Export your Quip doc to HTML and run:

```bash
python -m quip2deck.cli path/to/exported.html out/mydeck.pptx
```

**Option B — Use a Quip share/export URL:**
```bash
python -m quip2deck.cli --url "https://<quip-export-or-share-url>" out/mydeck.pptx
```

**Option C — Use the Quip API (token + base URL):**
```bash
python -m quip2deck.cli \
  --quip-thread-id "THREAD_ID" \
  --quip-token "$QUIP_TOKEN" \
  --quip-base-url "https://platform.quip.com" \
  out/mydeck.pptx
  # run in terminal
  #python3 -m quip2deck.cli convert examples/sample_quipx.html out/apollox.pptx \
  #  --img-bearer 'VWNEOU1BWGVSblI=|1790354983|pUyurqv4CwUzS3IdsGXeMfQfUu6HGPZD0ou5Q9MCITQ='
```

**API endpoint equivalents:**
POST `/convert` with a JSON body containing one of the following:
- `{ "html": "<html>..." }`
- `{ "url": "https://..." }`
- `{ "quip_thread_id": "...", "quip_token": "...", "quip_base_url": "https://platform.quip.com" }`

---

## Layout & Rules (current MVP)
- New slide at each `<h1>` or `<h2>`
- First heading becomes the deck title (Title slide)
- Subsequent sections become "Title & Content" slides
- `<p>` becomes paragraph lines; `<ul>/<ol>` become bullets

---

## Project Structure

```
src/quip2deck/
  __init__.py
  cli.py                # CLI convenience wrapper
  main.py               # FastAPI service
  models.py             # Pydantic models for SlidePlan, requests
  connectors/quip.py    # (stub) Quip API connector
  parsers/quip_html.py  # HTML → AST nodes
  planner/outline.py    # AST → SlidePlan
  theming/theme.py      # Theme dataclass (MVP, constants)
  renderers/pptx_renderer.py   # PPTX writer
  renderers/keynote_agent.py   # (stub) client to macOS agent
  utils/files.py        # paths, temp dirs
examples/
  sample_quip.html
  sample_request.json
tests/
  test_roundtrip.py
requirements.txt
```

---

## Notes
- This is a **starter**—kept intentionally minimal and readable.
- Extend the parser/planner to support callouts, images, tables, charts, notes, and layout hints like `:::slide`.
- For Keynote-native output, create a macOS agent that receives the SlidePlan JSON and uses AppleScript/JXA to create a `.key`. This repo includes a stub only.
