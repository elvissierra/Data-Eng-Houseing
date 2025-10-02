from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union, Dict


class ImageSpec(BaseModel):
    path: str
    alt: Optional[str] = None

class TableSpec(BaseModel):
    rows: List[List[str]]


class ChartSpec(BaseModel):
    type: Literal["bar", "column", "line", "pie"] = "bar"
    data: List[tuple[str, float]]  # (label, value)

class Slide(BaseModel):
    layout: Literal["title", "content"] = "content"
    title: Optional[str] = None
    subtitle: Optional[str] = None
    bullets: Optional[List[str]] = None
    paragraphs: Optional[List[str]] = None
    image: Optional[ImageSpec] = None
    images: Optional[List[ImageSpec]] = None
    table: Optional[TableSpec] = None
    notes: Optional[str] = None
    chart: Optional[ChartSpec] = None
    charts: Optional[List[ChartSpec]] = None

from typing import Any
class SlidePlan(BaseModel):
    meta: Dict[str, Any] = Field(default_factory=dict)
    slides: List[Slide]

class ConvertRequest(BaseModel):
    html: str
    out_path: Optional[str] = None
    theme: Optional[str] = "Default"
