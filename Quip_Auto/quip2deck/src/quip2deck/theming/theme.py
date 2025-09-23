from dataclasses import dataclass

@dataclass
class Theme:
    name: str = "Default"
    heading_font: str = "Calibri"
    body_font: str = "Calibri"

DEFAULT_THEME = Theme()
