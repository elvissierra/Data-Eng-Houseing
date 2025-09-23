from typing import List, Dict, Any
from quip2deck.models import Slide, SlidePlan

def plan_slides(ast: List[dict]) -> SlidePlan:
    slides: List[Slide] = []
    title = None
    cur: Dict[str, Any] = {"title": None, "bullets": [], "paragraphs": []}

    def flush_current():
        nonlocal slides, cur
        if cur["title"] is None and (cur["bullets"] or cur["paragraphs"]):
            # orphan content → put on a content slide with no title
            slides.append(Slide(layout="content", title=None,
                                bullets=cur["bullets"] or None,
                                paragraphs=cur["paragraphs"] or None))
        elif cur["title"] is not None:
            layout = "content"
            slides.append(Slide(layout=layout, title=cur["title"],
                                bullets=cur["bullets"] or None,
                                paragraphs=cur["paragraphs"] or None))
        cur = {"title": None, "bullets": [], "paragraphs": []}

    for node in ast:
        t = node.get("type")
        if t == "heading":
            level = node.get("level", 2)
            text = node.get("text", "")
            if title is None and level <= 2:
                # first heading → deck title slide
                title = text
                slides.append(Slide(layout="title", title=title))
            else:
                # new section → start a new slide
                flush_current()
                cur["title"] = text
        elif t == "list":
            cur["bullets"].extend(node.get("items", []))
        elif t == "paragraph":
            cur["paragraphs"].append(node.get("text",""))

    flush_current()
    return SlidePlan(meta={"title": title or "Deck"}, slides=slides)
