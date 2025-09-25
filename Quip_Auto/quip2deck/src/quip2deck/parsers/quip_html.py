from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any

Node = Dict[str, Any]

BR_MARK = {"type": "_br"}


def parse_html_to_ast(html: str) -> List[Node]:
    """Small HTML→AST for Quip-like docs:
    - headings (h1/h2/h3)
    - paragraphs (including bare text separated by <br/>)
    - lists (ul/ol)
    - images (<img>)
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.body or soup

    raw_nodes: List[Node] = []
    for child in body.children:  # include NavigableString and tags in order
        raw_nodes.extend(_walk(child))

    # Collapse BR-separated text runs into separate paragraph nodes
    ast: List[Node] = []
    buf: List[str] = []
    def flush_buf():
        nonlocal buf
        if buf:
            text = " ".join([t for t in buf if t])
            text = text.strip()
            if text:
                ast.append({"type": "paragraph", "text": text})
            buf = []

    for n in raw_nodes:
        if n.get("type") == "_text":
            t = (n.get("text") or "").strip()
            if t:
                buf.append(t)
        elif n.get("type") == "_br":
            flush_buf()
        else:
            flush_buf()
            ast.append(n)
    flush_buf()

    return ast


def _walk(el) -> List[Node]:
    nodes: List[Node] = []
    if isinstance(el, NavigableString):
        text = str(el)
        if text and text.strip():
            nodes.append({"type": "_text", "text": text})
        return nodes
    if not isinstance(el, Tag):
        return nodes

    name = el.name.lower()
    if name in ["br"]:
        nodes.append(BR_MARK)
        return nodes

    if name in ["h1", "h2", "h3"]:
        level = int(name[1])
        nodes.append({"type": "heading", "level": level, "text": el.get_text(strip=True)})
        return nodes

    if name == "p":
        # Capture text as a paragraph, but also surface any inline images
        text = el.get_text(" ", strip=True)
        if text:
            nodes.append({"type": "paragraph", "text": text})
        for img in el.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or None
            nodes.append({"type": "image", "src": src, "alt": alt})
        return nodes

    if name in ["ul", "ol"]:
        items = []
        images = []
        for li in el.find_all("li", recursive=False):
            items.append(li.get_text(" ", strip=True))
            for img in li.find_all("img"):
                src = img.get("src") or ""
                alt = img.get("alt") or None
                images.append({"type": "image", "src": src, "alt": alt})
        nodes.append({"type": "list", "ordered": name == "ol", "items": items})
        # Append images found in list items after the list so they stay with this section
        nodes.extend(images)
        return nodes

    if name == "img":
        src = el.get("src") or ""
        alt = el.get("alt") or None
        nodes.append({"type": "image", "src": src, "alt": alt})
        return nodes

    # Generic container: walk children in order, preserving text/BRs
    for child in el.children:
        nodes.extend(_walk(child))
    return nodes
