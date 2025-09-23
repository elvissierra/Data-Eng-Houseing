from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Dict, Any

Node = Dict[str, Any]

def parse_html_to_ast(html: str) -> List[Node]:
    """Very small HTML→AST for Quip-like docs: headings, paragraphs, lists."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.body or soup
    ast: List[Node] = []
    for el in body.find_all(recursive=False):
        ast.extend(_walk(el))
    return ast

def _walk(el) -> List[Node]:
    nodes: List[Node] = []
    if isinstance(el, NavigableString):
        text = el.strip()
        if text:
            nodes.append({"type": "paragraph", "text": text})
        return nodes
    if not isinstance(el, Tag):
        return nodes

    name = el.name.lower()
    if name in ["h1","h2","h3"]:
        level = int(name[1])
        nodes.append({"type":"heading","level":level,"text":el.get_text(strip=True)})
    elif name == "p":
        text = el.get_text(" ", strip=True)
        if text:
            nodes.append({"type":"paragraph","text":text})
    elif name in ["ul","ol"]:
        items = []
        for li in el.find_all("li", recursive=False):
            items.append(li.get_text(" ", strip=True))
        nodes.append({"type":"list","ordered": name=="ol","items":items})
    else:
        # Recurse into unknown containers
        for child in el.children:
            nodes.extend(_walk(child))
    return nodes
