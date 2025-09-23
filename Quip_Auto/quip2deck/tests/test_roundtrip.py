from quip2deck.parsers.quip_html import parse_html_to_ast
from quip2deck.planner.outline import plan_slides

def test_parse_plan():
    html = '<h1>Title</h1><p>hello</p><ul><li>a</li></ul><h2>Next</h2>'
    ast = parse_html_to_ast(html)
    plan = plan_slides(ast)
    assert len(plan.slides) >= 2
