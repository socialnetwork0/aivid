"""Dependency checking utilities."""

import shutil


def check_system_dependencies() -> dict[str, bool]:
    """Check availability of system dependencies (binaries).

    Returns:
        Dict mapping tool names to availability status.
    """
    tools = ["ffprobe", "ffmpeg", "exiftool", "mediainfo", "c2patool"]
    return {tool: shutil.which(tool) is not None for tool in tools}


def check_python_dependencies() -> dict[str, bool]:
    """Check availability of optional Python packages.

    Returns:
        Dict mapping package names to availability status.
    """
    packages = {}

    # c2pa-python
    try:
        import c2pa  # noqa: F401

        packages["c2pa-python"] = True
    except ImportError:
        packages["c2pa-python"] = False

    # pyexiftool
    try:
        import exiftool  # noqa: F401

        packages["pyexiftool"] = True
    except ImportError:
        packages["pyexiftool"] = False

    # pymediainfo
    try:
        import pymediainfo  # noqa: F401

        packages["pymediainfo"] = True
    except ImportError:
        packages["pymediainfo"] = False

    return packages


def check_all_dependencies() -> dict[str, dict[str, bool]]:
    """Check all dependencies.

    Returns:
        Dict with 'system' and 'python' keys containing availability dicts.
    """
    return {
        "system": check_system_dependencies(),
        "python": check_python_dependencies(),
    }


def print_dependency_status() -> None:
    """Print dependency status to stdout."""
    deps = check_all_dependencies()

    print("aivid dependency status:")
    print("=" * 40)

    print("\nSystem binaries:")
    for name, available in sorted(deps["system"].items()):
        icon = "✓" if available else "✗"
        print(f"  {icon} {name}")

    print("\nPython packages:")
    for name, available in sorted(deps["python"].items()):
        icon = "✓" if available else "✗"
        print(f"  {icon} {name}")

    # Summary
    system_count = sum(deps["system"].values())
    python_count = sum(deps["python"].values())
    print(
        f"\nSummary: {system_count}/{len(deps['system'])} system tools, "
        f"{python_count}/{len(deps['python'])} Python packages"
    )

    # Recommendations
    if not deps["system"]["ffprobe"]:
        print("\n⚠️  ffprobe is required. Install: brew install ffmpeg")
    if not deps["python"]["c2pa-python"]:
        print("\n💡 For better C2PA support: pip install c2pa-python")
