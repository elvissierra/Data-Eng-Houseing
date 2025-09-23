from fastapi import FastAPI, HTTPException
from quip2deck.models import ConvertRequest
from quip2deck.parsers.quip_html import parse_html_to_ast
from quip2deck.planner.outline import plan_slides
from quip2deck.renderers.pptx_renderer import render_pptx
from quip2deck.utils.files import default_output_path
import uuid

app = FastAPI(title="quip2deck")

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/convert")
def convert(req: ConvertRequest):
    try:
        ast = parse_html_to_ast(req.html)
        plan = plan_slides(ast)
        out_path = req.out_path or default_output_path(f"deck-{uuid.uuid4().hex[:8]}.pptx")
        render_pptx(plan, out_path)
        return {"out_path": out_path, "slides": len(plan.slides), "title": plan.meta.get("title")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
