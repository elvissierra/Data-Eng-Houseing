
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_DATA_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.dml.color import RGBColor
from quip2deck.models import SlidePlan
from quip2deck.utils.files import ensure_parent

from typing import List, Tuple

# --- Theme colors ---
BG_DARK = RGBColor(0, 0, 0)
FG_LIGHT = RGBColor(255, 255, 255)

# --- Keynote style constants ---
KEY_FONT = "Helvetica Neue"
TITLE_SIZE_TITLE = Pt(56)   # title slide title
TITLE_SIZE_CONTENT = Pt(48) # content slide title
SUBTITLE_SIZE = Pt(24)
BODY_SIZE = Pt(30)          # body/bullets
SUB_BULLET_SIZE = Pt(24)


def _set_paragraph_text(p, text: str, bold_key_before_colon: bool = True):
    """Set paragraph text with optional bolding of the part before ':'"""
    # Clear any existing simple text
    try:
        p.text = ""
    except Exception:
        pass
    if bold_key_before_colon and ":" in text:
        key, val = text.split(":", 1)
        r1 = p.add_run(); r1.text = key.strip() + ": "
        r1.font.bold = True; r1.font.name = KEY_FONT; r1.font.size = BODY_SIZE
        r2 = p.add_run(); r2.text = val.strip()
        r2.font.bold = False; r2.font.name = KEY_FONT; r2.font.size = BODY_SIZE
    else:
        r = p.add_run(); r.text = text
        r.font.name = KEY_FONT; r.font.size = BODY_SIZE


def _apply_font_paragraph(p, size):
    for r in getattr(p, "runs", []) or []:
        r.font.name = KEY_FONT
        r.font.size = size
        try:
            r.font.color.rgb = FG_LIGHT
        except Exception:
            pass


# --- Dark theme background and text helpers ---
def _apply_dark_background(slide):
    try:
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = BG_DARK
    except Exception:
        pass


def _colorize_textframe(tf, rgb):
    try:
        for p in tf.paragraphs:
            for r in getattr(p, 'runs', []) or []:
                if r.font is not None:
                    r.font.color.rgb = rgb
    except Exception:
        pass


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
                try:
                    r.font.color.rgb = FG_LIGHT
                except Exception:
                    pass
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
            _apply_dark_background(slide)
            if slide.shapes.title:
                slide.shapes.title.text = s.title or plan.meta.get("title", "Deck")
                # slightly larger title
                try:
                    for p in slide.shapes.title.text_frame.paragraphs:
                        for r in p.runs:
                            r.font.name = KEY_FONT
                            r.font.size = TITLE_SIZE_TITLE
                except Exception:
                    pass
                _colorize_textframe(slide.shapes.title.text_frame, FG_LIGHT)
            if len(slide.placeholders) > 1 and s.subtitle:
                slide.placeholders[1].text = s.subtitle
                _colorize_textframe(slide.placeholders[1].text_frame, FG_LIGHT)
            continue

        # Content slide
        slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title & Content
        _apply_dark_background(slide)
        if slide.shapes.title:
            slide.shapes.title.text = s.title or ""
            try:
                for p in slide.shapes.title.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.name = KEY_FONT
                        r.font.size = TITLE_SIZE_CONTENT
            except Exception:
                pass
            _colorize_textframe(slide.shapes.title.text_frame, FG_LIGHT)

        # Optional subtitle: use the body placeholder's first paragraph prefix
        body = slide.placeholders[1].text_frame
        body.clear()
        if s.subtitle:
            body.text = s.subtitle
            try:
                body.paragraphs[0].font.name = KEY_FONT
                body.paragraphs[0].font.size = SUBTITLE_SIZE
            except Exception:
                pass
            # add a spacer paragraph
            body.add_paragraph().text = ""
            try:
                _colorize_textframe(body, FG_LIGHT)
            except Exception:
                pass

        # Paragraphs then bullets (Helvetica Neue), bold key before ':'
        first = (len(body.paragraphs) == 0) or (body.paragraphs[0].text == "")
        if s.paragraphs:
            for ptxt in s.paragraphs:
                p = body.paragraphs[0] if first else body.add_paragraph(); first = False
                p.level = 0
                _set_paragraph_text(p, ptxt, bold_key_before_colon=False)
                _apply_font_paragraph(p, BODY_SIZE)
        if s.bullets:
            for b in s.bullets:
                p = body.paragraphs[0] if first else body.add_paragraph(); first = False
                p.level = 0
                _set_paragraph_text(p, b, bold_key_before_colon=True)
                _apply_font_paragraph(p, BODY_SIZE)

        # Make sure all body text is white
        _colorize_textframe(body, FG_LIGHT)

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
                    # Show native legend (color index) and keep percentage labels
                    chart.has_legend = True
                    try:
                        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
                    except Exception:
                        pass
                    plot = chart.plots[0]
                    plot.has_data_labels = True
                    d = plot.data_labels
                    d.show_percentage = True
                    d.number_format = "0%"
                    try:
                        d.position = XL_DATA_LABEL_POSITION.OUTSIDE_END
                    except Exception:
                        pass
                    # White labels/legend for dark background
                    try:
                        d.font.color.rgb = FG_LIGHT
                    except Exception:
                        pass
                    try:
                        chart.legend.font.color.rgb = FG_LIGHT
                    except Exception:
                        pass
                else:
                    for series in chart.series:
                        series.has_data_labels = True
                        series.data_labels.show_value = True
                        series.data_labels.font.size = Pt(12)
                    # Axes/legend tick labels in white
                    try:
                        if chart.has_legend and chart.legend is not None:
                            chart.legend.font.color.rgb = FG_LIGHT
                        if hasattr(chart, 'category_axis') and chart.category_axis is not None:
                            chart.category_axis.tick_labels.font.color.rgb = FG_LIGHT
                        if hasattr(chart, 'value_axis') and chart.value_axis is not None:
                            chart.value_axis.tick_labels.font.color.rgb = FG_LIGHT
                    except Exception:
                        pass
            except Exception:
                pass



    prs.save(out_path)
    return out_path
