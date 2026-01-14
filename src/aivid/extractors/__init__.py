"""Metadata extractors for aivid."""

from aivid.extractors.base import BaseExtractor
from aivid.extractors.c2patool import C2PAToolExtractor, check_c2patool_available, sign_with_c2pa
from aivid.extractors.ffprobe import FFprobeExtractor
from aivid.extractors.heuristic import HeuristicDetector

# Try to import c2pa-python extractor
try:
    from aivid.extractors.c2pa import C2PAExtractor

    _HAS_C2PA_PYTHON = True
except ImportError:
    _HAS_C2PA_PYTHON = False
    C2PAExtractor = None  # type: ignore

# All available extractor classes (order doesn't matter, priority is used)
_EXTRACTORS: list[type[BaseExtractor]] = [
    FFprobeExtractor,
    C2PAToolExtractor,
    HeuristicDetector,
]

# Add c2pa-python extractor if available
if _HAS_C2PA_PYTHON and C2PAExtractor is not None:
    _EXTRACTORS.append(C2PAExtractor)


def get_available_extractors() -> list[BaseExtractor]:
    """Get list of available extractor instances, sorted by priority.

    Returns:
        List of extractor instances that are available on this system,
        sorted by priority (lowest first).
    """
    available = []
    for extractor_cls in _EXTRACTORS:
        try:
            if extractor_cls.is_available():
                available.append(extractor_cls())
        except Exception:
            # Skip extractors that fail to initialize
            pass

    # Sort by priority (lower = higher priority)
    available.sort(key=lambda x: x.priority)
    return available


def get_extractor_status() -> dict[str, bool]:
    """Get availability status of all extractors.

    Returns:
        Dict mapping extractor names to availability status.
    """
    status = {}
    for extractor_cls in _EXTRACTORS:
        try:
            status[extractor_cls.name] = extractor_cls.is_available()
        except Exception:
            status[extractor_cls.name] = False

    # Add c2pa-python status
    status["c2pa-python"] = _HAS_C2PA_PYTHON and (
        C2PAExtractor is not None and C2PAExtractor.is_available()
    )

    return status


def print_extractor_status() -> None:
    """Print extractor availability status."""
    status = get_extractor_status()

    print("aivid extractor status:")
    print("-" * 40)

    for name, available in sorted(status.items()):
        icon = "✓" if available else "✗"
        print(f"  {icon} {name}")


__all__ = [
    # Base class
    "BaseExtractor",
    # Extractors
    "FFprobeExtractor",
    "C2PAExtractor",
    "C2PAToolExtractor",
    "HeuristicDetector",
    # Functions
    "get_available_extractors",
    "get_extractor_status",
    "print_extractor_status",
    "check_c2patool_available",
    "sign_with_c2pa",
]
