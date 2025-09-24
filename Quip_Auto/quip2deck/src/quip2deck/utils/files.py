import os
from pathlib import Path

def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def _repo_root_from_utils() -> Path:
    """Resolve repo root as the directory above src/. Falls back to CWD if it fails."""
    try:
        here = Path(__file__).resolve()
        # utils.py -> utils -> quip2deck -> src -> REPO_ROOT
        return here.parents[3]
    except Exception:
        return Path.cwd()

def default_output_path(name: str = 'deck.pptx') -> str:
    # Always write to <repo-root>/out/ regardless of current working directory
    root = _repo_root_from_utils()
    out_dir = root / 'out'
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / name)