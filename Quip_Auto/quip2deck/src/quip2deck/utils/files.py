import os
from pathlib import Path

def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def default_output_path(name: str = 'deck.pptx') -> str:
    out_dir = Path('out')
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / name)
