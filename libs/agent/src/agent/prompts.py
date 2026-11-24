from functools import cache
from pathlib import Path


@cache
def read_prompt(path: Path) -> str:
    """Read a Markdown prompt that lives next to the plugin it instructs."""
    return path.read_text(encoding="utf-8").strip()
