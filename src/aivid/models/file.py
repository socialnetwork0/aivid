"""File information models."""

from datetime import datetime

from pydantic import BaseModel


def format_size(size_bytes: int | float) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 0:
        return "N/A"
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} EB"


class FileInfo(BaseModel):
    """Basic file information."""

    path: str
    filename: str
    extension: str
    size_bytes: int
    created: datetime | None = None
    modified: datetime | None = None
    accessed: datetime | None = None

    @property
    def size_human(self) -> str:
        """Return human-readable file size."""
        return format_size(self.size_bytes)
