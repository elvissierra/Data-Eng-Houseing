from typing import List, Dict, Any
from quip2deck.models import Slide, SlidePlan, ChartSpec
import re

#
# Numeric KV: "Label - 123", "Label: 45.6", or "Label\t789"
_KV_NUM = [
    re.compile(r"^\s*([^\-:\t]+)\s*[-:]\s*([+-]?(?:\d+(?:\.\d+)?))\s*$"),
    re.compile(r"^\s*([^\t]+)\t([+-]?(?:\d+(?:\.\d+)?))\s*$"),
]

# Any KV: captured as bullets only
_KV_ANY = [
    re.compile(r"^\s*([^\-:\t]+)\s*[-:]\s*(.+?)\s*$"),
    re.compile(r"^\s*([^\t]+)\t(.+?)\s*$"),
]

_TOTAL_SAMPLE = re.compile(r"^\s*total\s+sample\s*:\s*(\d+)\s*$", re.IGNORECASE)

# User-selectable chart preference
_CHART_PREF = re.compile(r"^\s*(?:\[chart=(bar|pie|line|column)\]|:::\s*chart\s*=\s*(bar|pie|line|column)|\((bar|pie|line|column)\))\s*$", re.IGNORECASE)
_CHART_MAP = {"bar":"bar","pie":"pie","line":"line","column":"column"}

_SUBHEAD = re.compile(r"^[A-Za-z0-9].{0,40}$")  # short label used as subhead like 'Ticket source'


def _kv_numeric(line: str):
    for pat in _KV_NUM:
        m = pat.match(line)
        if m:
            return m.group(1).strip(), float(m.group(2))
    return None


def _kv_any(line: str):
    for pat in _KV_ANY:
        m = pat.match(line)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None



def plan_slides(ast: List[dict]) -> SlidePlan:
    slides: List[Slide] = []
    deck_title = None

    # Current section state
    cur: Dict[str, Any] = {
        "title": None,
        "subtitle": None,
        "bullets": [],
        "paragraphs": [],
        "chart_points": [],
        "chart_pref": None,
        "pending_subhead": None,
    }

    def _emit_slide_from_cur():
        nonlocal slides, cur
        if not (cur["title"] or cur["bullets"] or cur["paragraphs"] or cur["chart_points"] or cur["subtitle"]):
            return
        chart = None
        if cur["chart_points"]:
            ctype = cur["chart_pref"] if cur["chart_pref"] in ("bar","pie","line","column") else ("pie" if 2 <= len(cur["chart_points"]) <= 6 else "bar")
            chart = ChartSpec(type=ctype, data=cur["chart_points"])
        slides.append(Slide(
            layout="content",
            title=cur["title"],
            subtitle=cur["subtitle"],
            bullets=(cur["bullets"] or None),
            paragraphs=(cur["paragraphs"] or None),
            chart=chart,
        ))
        cur.update({
            "title": None,
            "subtitle": None,
            "bullets": [],
            "paragraphs": [],
            "chart_points": [],
            "chart_pref": None,
            "pending_subhead": None,
        })

    # Walk AST
    for node in ast:
        t = node.get("type")
        if t == "heading":
            level = node.get("level", 2)
            text = (node.get("text") or "").strip()
            if deck_title is None and level <= 2:
                deck_title = text
                slides.append(Slide(layout="title", title=deck_title))
            else:
                _emit_slide_from_cur()
                cur["title"] = text
                cur["chart_pref"] = None
                cur["pending_subhead"] = None
        elif t == "list":
            for item in node.get("items", []):
                s = (item or "").strip()
                if not s:
                    continue
                # Detect chart preference
                pref = _CHART_PREF.match(s)
                if pref:
                    chosen = next(g for g in pref.groups() if g)
                    cur["chart_pref"] = _CHART_MAP.get(chosen.lower())
                    continue
                # Numeric?
                kvn = _kv_numeric(s)
                if kvn:
                    cur["chart_points"].append(kvn)
                    val = kvn[1]; bullet_val = int(val) if float(val).is_integer() else val
                    cur["bullets"].append(f"{kvn[0]}: {bullet_val}")
                    continue
                # Non-numeric KV → bullet
                kva = _kv_any(s)
                if kva:
                    cur["bullets"].append(f"{kva[0]}: {kva[1]}")
                else:
                    # treat a short line as a possible subhead (labels like 'Ticket source')
                    if _SUBHEAD.match(s):
                        cur["pending_subhead"] = s
                    else:
                        cur["paragraphs"].append(s)
        elif t == "paragraph":
            line = (node.get("text") or "").strip()
            if not line:
                continue
            # Subtitle capture
            ms = _TOTAL_SAMPLE.match(line)
            if ms:
                cur["subtitle"] = f"Total sample: {ms.group(1)}"
                continue
            # Split into pseudo-lines
            for sub in re.split(r"\s*\n+|\s*•\s*|\s*;\s*|\s*\|\s*", line):
                s = sub.strip()
                if not s:
                    continue
                # Detect chart preference
                pref = _CHART_PREF.match(s)
                if pref:
                    chosen = next(g for g in pref.groups() if g)
                    cur["chart_pref"] = _CHART_MAP.get(chosen.lower())
                    continue
                # Numeric KV → chart
                kvn = _kv_numeric(s)
                if kvn:
                    cur["chart_points"].append(kvn)
                    val = kvn[1]; bullet_val = int(val) if float(val).is_integer() else val
                    cur["bullets"].append(f"{kvn[0]}: {bullet_val}")
                    continue
                # Non-numeric KV or text
                kva = _kv_any(s)
                if kva:
                    cur["bullets"].append(f"{kva[0]}: {kva[1]}")
                else:
                    # possible subhead label
                    if _SUBHEAD.match(s):
                        cur["pending_subhead"] = s
                    else:
                        cur["paragraphs"].append(s)
        # ignore other node types

    _emit_slide_from_cur()
    return SlidePlan(meta={"title": deck_title or "Deck"}, slides=slides)
