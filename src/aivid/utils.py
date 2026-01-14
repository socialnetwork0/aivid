"""Utility functions for aivid."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any


def format_size(size: int) -> str:
    """Format size in human readable format."""
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024
    return f"{size_float:.2f} PB"


def get_file_info(file_path: str) -> dict[str, Any]:
    """Get basic file information."""
    stat = os.stat(file_path)

    # st_birthtime is only available on macOS/BSD
    created: str | None = None
    if hasattr(stat, "st_birthtime"):
        created = datetime.fromtimestamp(getattr(stat, "st_birthtime")).isoformat()

    return {
        "filename": os.path.basename(file_path),
        "path": os.path.abspath(file_path),
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "created": created,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "extension": Path(file_path).suffix.lower(),
    }
