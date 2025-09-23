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

if __name__ == "__main__":
    app()
