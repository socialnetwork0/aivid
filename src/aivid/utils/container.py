"""Container format parsing utilities."""

import struct
from typing import BinaryIO

from aivid.models import BoxInfo

# MP4/MOV container boxes that can contain child boxes
CONTAINER_BOXES = [
    "moov",
    "trak",
    "mdia",
    "minf",
    "stbl",
    "udta",
    "meta",
    "ilst",
    "edts",
    "dinf",
    "sinf",
    "schi",
    "tref",
    "gmhd",
    "wave",
]

# MP4/MOV file extensions
MP4_EXTENSIONS = [".mp4", ".m4v", ".m4a", ".mov", ".3gp", ".3g2"]


def parse_mp4_boxes(file_path: str, max_depth: int = 5) -> list[BoxInfo]:
    """Parse MP4/MOV box structure.

    Args:
        file_path: Path to the video file
        max_depth: Maximum depth to recurse into container boxes

    Returns:
        List of BoxInfo objects representing the box structure
    """
    boxes: list[BoxInfo] = []

    def parse_boxes(f: BinaryIO, start: int, end: int, depth: int) -> None:
        f.seek(start)
        while f.tell() < end:
            pos = f.tell()
            header = f.read(8)
            if len(header) < 8:
                break

            size, box_type_bytes = struct.unpack(">I4s", header)
            try:
                box_type = box_type_bytes.decode("ascii")
            except UnicodeDecodeError:
                box_type = box_type_bytes.decode("latin-1", errors="replace")

            # Handle extended size
            if size == 1:
                ext_size = f.read(8)
                if len(ext_size) == 8:
                    size = struct.unpack(">Q", ext_size)[0]
            elif size == 0:
                size = end - pos

            if size < 8 or pos + size > end:
                break

            box_info = BoxInfo(
                type=box_type,
                size=size,
                offset=pos,
                depth=depth,
            )

            # Read box data for certain types
            if box_type in ["ftyp", "hdlr", "mvhd", "tkhd", "mdhd"]:
                data_size = min(size - 8, 256)
                box_info.data_preview = f.read(data_size).hex()[:100]

            boxes.append(box_info)

            # Recurse into container boxes
            if box_type in CONTAINER_BOXES and depth < max_depth:
                data_start = f.tell()
                if box_type == "meta":
                    f.read(4)  # skip version/flags
                    data_start = f.tell()
                parse_boxes(f, data_start, pos + size, depth + 1)

            f.seek(pos + size)

    try:
        with open(file_path, "rb") as f:
            f.seek(0, 2)
            file_size = f.tell()
            parse_boxes(f, 0, file_size, 0)
    except Exception as e:
        boxes.append(BoxInfo(type="error", size=0, offset=0, depth=0, data_preview=str(e)))

    return boxes


def extract_strings(file_path: str, min_length: int = 4) -> list[str]:
    """Extract printable strings from a binary file.

    Args:
        file_path: Path to the file
        min_length: Minimum string length to extract

    Returns:
        List of extracted strings
    """
    import subprocess

    try:
        result = subprocess.run(
            ["strings", "-n", str(min_length), file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def filter_interesting_strings(strings: list[str]) -> list[str]:
    """Filter strings for metadata-relevant content.

    Args:
        strings: List of raw strings

    Returns:
        List of potentially interesting strings
    """
    # Keywords to look for
    keywords = [
        "copyright",
        "author",
        "creator",
        "c2pa",
        "contentauth",
        "jumbf",
        "xmp",
        "sora",
        "openai",
        "google",
        "adobe",
        "gemini",
        "veo",
        "runway",
        "pika",
        "midjourney",
        "stability",
        "luma",
        "kling",
        "trained",
        "generated",
        "synthetic",
        "ai-generated",
        "ffmpeg",
        "davinci",
        "premiere",
        "encoder",
        "handler",
        "software",
        "manifest",
        "signature",
        "certificate",
        "truepic",
        "http://",
        "https://",
        "urn:",
        "uuid:",
    ]

    interesting = []
    for s in strings:
        s_lower = s.lower()
        # Skip very short or very long strings
        if any(kw in s_lower for kw in keywords) and 4 <= len(s) <= 500:
            interesting.append(s)

    return interesting[:100]  # Limit to first 100
