
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_DATA_LABEL_POSITION, XL_LEGEND_POSITION
from quip2deck.models import SlidePlan
from quip2deck.utils.files import ensure_parent

from typing import List, Tuple


# Textual index helper for chart data
def _add_chart_index_box(slide, items: List[Tuple[str, float]], left, top, width, height, show_pct: bool = True):
    if not items:
        return None
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    total = sum(v for (_l, v) in items)
    for i, (lbl, val) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        pct_txt = f" ({val/total:.0%})" if (show_pct and total > 0) else ""
        p.text = f"{lbl} — {int(val) if float(val).is_integer() else val}{pct_txt}"
        p.level = 0
        try:
            for r in p.runs:
                r.font.size = Pt(12)
        except Exception:
            pass
    return box



def render_pptx(plan: SlidePlan, out_path: str) -> str:
    """Minimal PPTX renderer: Title & Content layout, bullets left, chart right."""
    ensure_parent(out_path)
    prs = Presentation()
    # Normalize to 16:9 so charts aren’t off-canvas in Keynote
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for s in plan.slides:
        if s.layout == "title":
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            if slide.shapes.title:
                slide.shapes.title.text = s.title or plan.meta.get("title", "Deck")
                # slightly larger title
                try:
                    for p in slide.shapes.title.text_frame.paragraphs:
                        for r in p.runs:
                            r.font.size = Pt(60)
                except Exception:
                    pass
            if len(slide.placeholders) > 1 and s.subtitle:
                slide.placeholders[1].text = s.subtitle
            continue

        # Content slide
        slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title & Content
        if slide.shapes.title:
            slide.shapes.title.text = s.title or ""
            try:
                for p in slide.shapes.title.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(56)
            except Exception:
                pass

        # Optional subtitle: use the body placeholder's first paragraph prefix
        body = slide.placeholders[1].text_frame
        body.clear()
        if s.subtitle:
            body.text = s.subtitle
            body.paragraphs[0].font.size = Pt(24)
            # add a spacer paragraph
            body.add_paragraph().text = ""

        # Paragraphs then bullets
        first = (len(body.paragraphs) == 0) or (body.paragraphs[0].text == "")
        if s.paragraphs:
            for ptxt in s.paragraphs:
                p = body.paragraphs[0] if first else body.add_paragraph(); first = False
                p.text = ptxt; p.level = 0
        if s.bullets:
            for b in s.bullets:
                p = body.paragraphs[0] if first else body.add_paragraph(); first = False
                p.text = b; p.level = 0
                # bump list font size a bit
                try:
                    for r in p.runs: r.font.size = Pt(34)
                except Exception:
                    pass

        # Optional chart on the right
        if getattr(s, "chart", None) and s.chart and s.chart.data:
            cdata = CategoryChartData()
            cdata.categories = [lbl for (lbl, _v) in s.chart.data]
            cdata.add_series("", [v for (_lbl, v) in s.chart.data])
            # right-side placement tuned to 16:9
            slide_w = prs.slide_width
            slide_h = prs.slide_height
            margin = Inches(0.6)
            chart_size = min(Inches(4.2), slide_h - Inches(3.0))  # safe square
            left = slide_w - chart_size - margin
            if left < Inches(0.5):
                # shrink chart to preserve a 0.5" left margin (prevents off-canvas after Keynote reflow)
                overflow = Inches(0.5) - left
                chart_size = max(Inches(3.2), chart_size - overflow)
                left = slide_w - chart_size - margin
                width = chart_size
                height = chart_size
            top = Inches(2.1)
            width = chart_size
            height = chart_size
            ctype = XL_CHART_TYPE.COLUMN_CLUSTERED
            if s.chart.type == "bar":
                ctype = XL_CHART_TYPE.BAR_CLUSTERED
            elif s.chart.type == "line":
                ctype = XL_CHART_TYPE.LINE
            elif s.chart.type == "pie":
                ctype = XL_CHART_TYPE.PIE
            chart = slide.shapes.add_chart(ctype, left, top, width, height, cdata).chart

            try:
                if s.chart.type == "pie":
                    chart.has_legend = False
                    plot = chart.plots[0]
                    plot.has_data_labels = True
                    d = plot.data_labels
                    d.show_percentage = True
                    d.number_format = "0%"
                    try:
                        d.position = XL_DATA_LABEL_POSITION.OUTSIDE_END
                    except Exception:
                        pass
                else:
                    for series in chart.series:
                        series.has_data_labels = True
                        series.data_labels.show_value = True
                        series.data_labels.font.size = Pt(12)
            except Exception:
                pass

            # Textual index listing counts (and % for pies)
            try:
                idx_left = left
                idx_top = top + height + Inches(0.1)
                idx_width = width
                idx_height = Inches(1.0)
                _add_chart_index_box(
                    slide,
                    s.chart.data,
                    idx_left,
                    idx_top,
                    idx_width,
                    idx_height,
                    show_pct=(s.chart.type == "pie"),
                )
            except Exception:
                pass

    prs.save(out_path)
    return out_path
