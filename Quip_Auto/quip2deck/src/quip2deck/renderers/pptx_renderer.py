from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from quip2deck.models import SlidePlan
from quip2deck.theming.theme import DEFAULT_THEME
from quip2deck.utils.files import ensure_parent

def render_pptx(plan: SlidePlan, out_path: str) -> str:
    ensure_parent(out_path)
    prs = Presentation()  # default template
    theme = DEFAULT_THEME

    # Title slide
    first = True
    for s in plan.slides:
        if s.layout == "title":
            layout = prs.slide_layouts[0]  # title
            slide = prs.slides.add_slide(layout)
            slide.shapes.title.text = s.title or plan.meta.get("title","Deck")
            if slide.placeholders and len(slide.placeholders) > 1:
                slide.placeholders[1].text = plan.meta.get("subtitle","")
            first = False
        else:
            # Title & Content
            layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(layout)
            if slide.shapes.title:
                slide.shapes.title.text = s.title or ""
            body = slide.placeholders[1].text_frame
            body.clear()

            # paragraphs then bullets
            if s.paragraphs:
                for ptxt in s.paragraphs:
                    p = body.add_paragraph() if body.text else body.paragraphs[0]
                    p.text = ptxt
                    p.level = 0
            if s.bullets:
                for b in s.bullets:
                    p = body.add_paragraph()
                    p.text = b
                    p.level = 0

    prs.save(out_path)
    return out_path
