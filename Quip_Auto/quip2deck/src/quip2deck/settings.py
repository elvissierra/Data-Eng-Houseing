from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple

@dataclass
class RendererSettings:
    # Slide geometry (inches)
    slide_width: float = 13.333
    slide_height: float = 7.5
    margin: float = 0.6         # right margin used for right-column visuals
    top_box: float = 2.1        # top offset of right-column visual area
    chart_box_max: float = 4.2  # max square for right-column chart or image box
    gap: float = 0.15           # gap between chart and thumbnails/grid below
    bottom_margin: float = 0.5

    # Theme
    bg_rgb: Tuple[int, int, int] = (0, 0, 0)
    fg_rgb: Tuple[int, int, int] = (255, 255, 255)
    font_name: str = "Helvetica Neue"

    # Background
    bg_image_path: str | None = None

    # Font sizes (points)
    title_title_pt: int = 56
    title_content_pt: int = 48
    subtitle_pt: int = 24
    body_pt: int = 30
    sub_bullet_pt: int = 24

    # Chart defaults
    pie_show_legend: bool = True
    legend_position: str = "bottom"  # bottom|right|left|top
    pie_labels_outside: bool = True
    show_percentages: bool = True

    # Image grids
    grid_cols_no_chart: int = 2
    grid_cols_with_chart: int = 2
    thumb_max_h: float = 1.6

    @staticmethod
    def from_meta(meta: Dict[str, Any] | None) -> "RendererSettings":
        if not meta:
            return RendererSettings()
        raw = (meta or {}).get("settings_override") or {}
        if not isinstance(raw, dict):
            return RendererSettings()
        base = RendererSettings()
        for k, v in raw.items():
            if hasattr(base, k):
                setattr(base, k, v)
        return base