import json
import typer
from pathlib import Path

from quip2deck.parsers.quip_html import parse_html_to_ast
from quip2deck.planner.outline import plan_slides
from quip2deck.renderers.pptx_renderer import render_pptx
from quip2deck.utils.files import default_output_path

app = typer.Typer()

@app.command()
def convert(html_path: str, out_path: str = typer.Argument(None)):
    html = Path(html_path).read_text(encoding="utf-8")
    ast = parse_html_to_ast(html)
    plan = plan_slides(ast)
    out = out_path or default_output_path(Path(html_path).stem + ".pptx")
    render_pptx(plan, out)
    typer.echo(f"Wrote {out} ({len(plan.slides)} slides)")

@app.command()
def proof2deck(proof_path: str, out_path: str = typer.Argument(None)):
    """Render a deck directly from a JSON 'proof' file (data proofs -> slides).

    proof schema (minimal):
    {
      "run_id": "...",
      "meta": {"source_doc": "analysis.xlsx", "generated_at": "..."},
      "sections": [
        {"id": "mismatch_severity", "title": "Mismatch Severity", "type": "category_counts", "data": [{"label": "High", "count": 62}, ...]},
        {"id": "brands", "title": "Brands Observed", "type": "top_list", "data": [{"label": "Dunkin", "count": 138}, ...]},
        {"id": "system_reverts", "title": "System Reverted Cols", "type": "events", "data": [{"entity_id": 16, "flag": "yes", "date": "2024-10-30"}]},
        {"id": "date_range", "title": "Observation Window", "type": "date_counts", "data": [{"date": "2023-07-10", "value": 1}], "summary": {"min": "2023-07-10", "max": "2025-05-10"}}
      ]
    }
    """
    proof = json.loads(Path(proof_path).read_text(encoding="utf-8"))
    # Late import to avoid circulars if renderer imports cli symbols elsewhere
    from quip2deck.renderers.pptx_renderer import render_proof_pptx
    out = out_path or default_output_path(Path(proof_path).stem + ".pptx")
    render_proof_pptx(proof, out)
    typer.echo(f"Wrote {out} (sections: {len(proof.get('sections', []))})")

if __name__ == "__main__":
    app()




from datetime import datetime
# === Proof -> PPTX renderer ====================================================

def render_proof_pptx(proof: dict, out_path: str) -> str:
    """Render a deck from a JSON-like proof object.
    Expected keys: run_id, meta{source_doc, generated_at}, sections[{id,title,type,data,...}]
    """
    ensure_parent(out_path)
    prs = Presentation()

    _proof_title_slide(prs, proof)

    for section in proof.get("sections", []):
        stype = section.get("type")
        if stype == "category_counts":
            _slide_category_counts(prs, section, proof)
        elif stype == "top_list":
            _slide_top_list(prs, section, proof)
        elif stype == "events":
            _slide_events_table(prs, section, proof)
        elif stype == "date_counts":
            _slide_date_counts(prs, section, proof)
        else:
            _slide_fallback(prs, section, proof)

    prs.save(out_path)
    return out_path


def _footnote_text(proof: dict) -> str:
    src = (proof.get("meta", {}) or {}).get("source_doc", "")
    run_id = proof.get("run_id") or (proof.get("meta", {}) or {}).get("generated_at", "")
    parts = []
    if src:
        parts.append(f"Source: {src}")
    if run_id:
        parts.append(f"Run: {run_id}")
    return " \u2022 ".join(parts)


def _proof_title_slide(prs: Presentation, proof: dict) -> None:
    layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1] if len(slide.placeholders) > 1 else None
    title.text = (proof.get("meta", {}) or {}).get("title", "Analysis Summary")
    subtxt = []
    if proof.get("meta", {}).get("source_doc"):
        subtxt.append(f"Source: {proof['meta']['source_doc']}")
    if proof.get("meta", {}).get("generated_at"):
        subtxt.append(f"Generated: {proof['meta']['generated_at']}")
    if proof.get("run_id"):
        subtxt.append(f"Run: {proof['run_id']}")
    if subtitle is not None:
        subtitle.text = " \u2022 ".join(subtxt)


def _new_title_content_slide(prs: Presentation, title_text: str):
    layout = prs.slide_layouts[1]  # Title & Content
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = title_text or ""
    body = slide.placeholders[1].text_frame
    body.clear()
    return slide, body


def _slide_category_counts(prs: Presentation, section: dict, proof: dict) -> None:
    # Render as bullets sorted desc by count
    slide, body = _new_title_content_slide(prs, section.get("title", "Category Counts"))
    data = section.get("data") or []
    data = [d for d in data if d is not None]
    data.sort(key=lambda x: x.get("count", 0), reverse=True)
    if not data:
        body.text = "No data"
    else:
        first = True
        for row in data:
            txt = f"{row.get('label','?')}: {row.get('count',0)}"
            if first:
                body.text = txt
                first = False
            else:
                p = body.add_paragraph()
                p.text = txt
                p.level = 0
    # footnote
    left = Inches(0.5)
    top = Inches(6.7)
    width = Inches(9)
    height = Inches(0.4)
    tx = slide.shapes.add_textbox(left, top, width, height).text_frame
    tx.text = _footnote_text(proof)
    tx.paragraphs[0].font.size = Pt(10)


def _slide_top_list(prs: Presentation, section: dict, proof: dict) -> None:
    slide, body = _new_title_content_slide(prs, section.get("title", "Top List"))
    data = section.get("data") or []
    data.sort(key=lambda x: x.get("count", 0), reverse=True)
    cap = 10
    shown = data[:cap]
    hidden = max(0, len(data) - cap)
    if not shown:
        body.text = "No data"
    else:
        first = True
        for row in shown:
            txt = f"{row.get('label','?')} — {row.get('count',0)}"
            if first:
                body.text = txt
                first = False
            else:
                p = body.add_paragraph(); p.text = txt; p.level = 0
        if hidden:
            p = body.add_paragraph(); p.text = f"… and {hidden} more"; p.level = 0
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(6.7), Inches(9), Inches(0.4)).text_frame
    tx.text = _footnote_text(proof); tx.paragraphs[0].font.size = Pt(10)


def _slide_events_table(prs: Presentation, section: dict, proof: dict) -> None:
    title = section.get("title", "Events")
    layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[1]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = title
    rows = (section.get("data") or [])
    # Build a simple 3-col table: ID | Flag | Date
    cols = 3
    row_count = max(1, len(rows) + 1)  # header + rows (at least header)
    table_shape = slide.shapes.add_table(row_count, cols, Inches(0.5), Inches(1.8), Inches(9), Inches(4)).table
    # headers
    table_shape.cell(0,0).text = "ID"
    table_shape.cell(0,1).text = "Flag"
    table_shape.cell(0,2).text = "Date"
    # rows
    for i, r in enumerate(rows, start=1):
        table_shape.cell(i,0).text = str(r.get("entity_id", r.get("id", "")))
        table_shape.cell(i,1).text = str(r.get("flag", ""))
        table_shape.cell(i,2).text = str(r.get("date", ""))
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(6.7), Inches(9), Inches(0.4)).text_frame
    tx.text = _footnote_text(proof); tx.paragraphs[0].font.size = Pt(10)


def _slide_date_counts(prs: Presentation, section: dict, proof: dict) -> None:
    slide, body = _new_title_content_slide(prs, section.get("title", "Date Counts"))
    data = section.get("data") or []
    if not data:
        body.text = "No data"
    else:
        # If sparse, show bullets; if dense, still bullets for now (charts can be added later)
        first = True
        for r in data[:20]:  # cap bullets to avoid overflow
            txt = f"{r.get('date','?')}: {r.get('value',0)}"
            if first:
                body.text = txt; first = False
            else:
                p = body.add_paragraph(); p.text = txt; p.level = 0
        if len(data) > 20:
            p = body.add_paragraph(); p.text = f"… and {len(data)-20} more"; p.level = 0
    # subtitle with range summary
    summary = section.get("summary") or {}
    min_d, max_d = summary.get("min"), summary.get("max")
    if min_d or max_d:
        sub = slide.placeholders[1]
        try:
            existing = sub.text_frame.paragraphs[0].text
        except Exception:
            existing = ""
        sub.text = (existing + ("\n" if existing else "") + f"Range: {min_d or '?'} → {max_d or '?'}").strip()
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(6.7), Inches(9), Inches(0.4)).text_frame
    tx.text = _footnote_text(proof); tx.paragraphs[0].font.size = Pt(10)


def _slide_fallback(prs: Presentation, section: dict, proof: dict) -> None:
    slide, body = _new_title_content_slide(prs, section.get("title", "Details"))
    import json as _json
    body.text = _json.dumps({k: v for k, v in section.items() if k != "data"}, indent=2)
    # Show up to first 5 data rows as bullets for safety
    for row in (section.get("data") or [])[:5]:
        p = body.add_paragraph(); p.text = str(row); p.level = 0
    tx = slide.shapes.add_textbox(Inches(0.5), Inches(6.7), Inches(9), Inches(0.4)).text_frame
    tx.text = _footnote_text(proof); tx.paragraphs[0].font.size = Pt(10)
