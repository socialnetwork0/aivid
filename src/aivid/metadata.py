"""
Media metadata extraction module.

Extract metadata from video/audio files using ffprobe, mediainfo, and exiftool.
"""

import json
import os
import re
import struct
import subprocess
from typing import Any, BinaryIO

from aivid.models import MetadataReport
from aivid.utils import get_file_info


def parse_mp4_boxes(file_path: str, max_depth: int = 5) -> list[dict[str, Any]]:
    """Parse MP4/MOV box structure."""
    boxes: list[dict[str, Any]] = []

    container_boxes = [
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

            box_info: dict[str, Any] = {
                "type": box_type,
                "size": size,
                "offset": pos,
                "depth": depth,
            }

            # Read box data for certain types
            if box_type in ["ftyp", "hdlr", "mvhd", "tkhd", "mdhd"]:
                data_size = min(size - 8, 256)
                box_info["data_preview"] = f.read(data_size).hex()[:100]

            boxes.append(box_info)

            # Recurse into container boxes
            if box_type in container_boxes and depth < max_depth:
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
        boxes.append({"error": str(e)})

    return boxes


def get_ffprobe_metadata(file_path: str) -> dict[str, Any]:
    """Get comprehensive metadata using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                "-show_programs",
                "-show_private_data",
                "-show_error",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        data: dict[str, Any] = json.loads(result.stdout) if result.stdout else {}
        return data
    except FileNotFoundError:
        return {"error": "ffprobe not found"}
    except Exception as e:
        return {"error": str(e)}


def extract_strings(file_path: str, min_length: int = 4) -> list[str]:
    """Extract readable strings from file."""
    try:
        result = subprocess.run(
            ["strings", "-n", str(min_length), file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.split("\n")
    except Exception:
        return []


def get_mediainfo_metadata(file_path: str) -> dict[str, Any]:
    """Get comprehensive metadata using mediainfo."""
    try:
        result = subprocess.run(
            ["mediainfo", "--Output=JSON", file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        data: dict[str, Any] = json.loads(result.stdout) if result.stdout else {}
        return data
    except FileNotFoundError:
        return {"error": "mediainfo not found"}
    except Exception as e:
        return {"error": str(e)}


def get_exiftool_metadata(file_path: str) -> dict[str, Any]:
    """Get metadata using exiftool."""
    try:
        result = subprocess.run(
            ["exiftool", "-j", "-G", "-n", file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        data = json.loads(result.stdout) if result.stdout else []
        if isinstance(data, list) and data:
            result_dict: dict[str, Any] = data[0]
            return result_dict
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        return {"error": "exiftool not found"}
    except Exception as e:
        return {"error": str(e)}


def parse_c2pa_info(strings: list[str], file_path: str) -> dict[str, Any]:
    """Parse C2PA manifest information."""
    _ = file_path  # unused but kept for API consistency
    combined = "\n".join(strings)
    info: dict[str, Any] = {}

    if "c2pa" not in combined.lower():
        return info

    info["has_c2pa"] = True

    # Manifest ID
    match = re.search(r"urn:c2pa:([a-f0-9\-]+)", combined)
    if match:
        info["manifest_id"] = f"urn:c2pa:{match.group(1)}"

    # Generator
    generators = {
        "Sora": "OpenAI Sora",
        "DALL-E": "OpenAI DALL-E",
        "Midjourney": "Midjourney",
        "Stable Diffusion": "Stability AI",
        "Adobe Firefly": "Adobe Firefly",
        "Runway": "Runway ML",
        "Pika": "Pika Labs",
        "Kling": "Kuaishou Kling",
        "Luma": "Luma AI",
    }
    for key, value in generators.items():
        if key.lower() in combined.lower():
            info["generator"] = value
            break

    # Digital source type
    match = re.search(r"digitalsourcetype/(\w+)", combined, re.IGNORECASE)
    if match:
        info["digital_source_type"] = match.group(1)

    # Signing authority
    authorities: list[str] = []
    for auth in ["OpenAI", "Adobe", "Microsoft", "Google", "Meta"]:
        if auth in combined:
            authorities.append(auth)
    if authorities:
        info["signing_authorities"] = authorities

    # C2PA version
    match = re.search(r"c2pa[_\-]?rs[^\d]*(\d+\.\d+\.\d+)", combined)
    if match:
        info["c2pa_library_version"] = match.group(1)

    # Instance ID
    match = re.search(r"xmp:iid:([a-f0-9\-]+)", combined)
    if match:
        info["instance_id"] = match.group(1)

    return info


def parse_xmp_metadata(strings: list[str]) -> dict[str, Any]:
    """Parse XMP metadata from strings."""
    combined = "\n".join(strings)
    xmp: dict[str, Any] = {}

    patterns = {
        "creator": r"<dc:creator[^>]*>([^<]+)",
        "title": r"<dc:title[^>]*>([^<]+)",
        "description": r"<dc:description[^>]*>([^<]+)",
        "rights": r"<dc:rights[^>]*>([^<]+)",
        "create_date": r"xmp:CreateDate>([^<]+)",
        "modify_date": r"xmp:ModifyDate>([^<]+)",
        "creator_tool": r"xmp:CreatorTool>([^<]+)",
        "metadata_date": r"xmp:MetadataDate>([^<]+)",
        "rating": r"xmp:Rating>([^<]+)",
        "label": r"xmp:Label>([^<]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            xmp[key] = match.group(1).strip()

    return xmp


def parse_gps_info(strings: list[str]) -> dict[str, Any]:
    """Parse GPS/location information."""
    combined = "\n".join(strings)
    gps: dict[str, Any] = {}

    # GPS coordinates
    lat_match = re.search(r"GPS[Ll]atitude[^\d\-]*(-?\d+\.?\d*)", combined)
    lon_match = re.search(r"GPS[Ll]ongitude[^\d\-]*(-?\d+\.?\d*)", combined)
    if lat_match:
        gps["latitude"] = float(lat_match.group(1))
    if lon_match:
        gps["longitude"] = float(lon_match.group(1))

    # Location name
    loc_match = re.search(
        r"(?:location|place|city|country)[^\w]*[:\s]+(\w[\w\s,]+)", combined, re.IGNORECASE
    )
    if loc_match:
        gps["location_name"] = loc_match.group(1).strip()

    return gps


def parse_creation_info(strings: list[str], ffprobe_data: dict[str, Any]) -> dict[str, Any]:
    """Parse creation and modification timestamps."""
    info: dict[str, Any] = {}
    combined = "\n".join(strings)

    # From ffprobe
    if "format" in ffprobe_data and "tags" in ffprobe_data["format"]:
        tags = ffprobe_data["format"]["tags"]
        if "creation_time" in tags:
            info["creation_time"] = tags["creation_time"]
        if "encoder" in tags:
            info["encoder"] = tags["encoder"]

    # From strings
    date_patterns = [
        (r"creation[_\s]*time[:\s]*([0-9T:\-Z+]+)", "creation_time"),
        (r"date[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})", "date"),
        (r"com\.apple\.quicktime\.creationdate[:\s]*([^\s]+)", "apple_creation_date"),
    ]

    for pattern, key in date_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match and key not in info:
            info[key] = match.group(1)

    return info


def parse_encoding_info(ffprobe_data: dict[str, Any], strings: list[str]) -> dict[str, Any]:
    """Parse encoding information."""
    info: dict[str, Any] = {}
    combined = "\n".join(strings)

    # From ffprobe streams
    for stream in ffprobe_data.get("streams", []):
        stream_type = stream.get("codec_type", "unknown")
        stream_info: dict[str, Any] = {
            "codec": stream.get("codec_name"),
            "codec_long": stream.get("codec_long_name"),
            "profile": stream.get("profile"),
            "bit_rate": stream.get("bit_rate"),
            "codec_tag": stream.get("codec_tag_string"),
            "time_base": stream.get("time_base"),
            "start_time": stream.get("start_time"),
            "duration": stream.get("duration"),
            "duration_ts": stream.get("duration_ts"),
            "nb_frames": stream.get("nb_frames"),
        }

        if stream_type == "video":
            stream_info.update(
                {
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "frame_rate": stream.get("r_frame_rate"),
                    "avg_frame_rate": stream.get("avg_frame_rate"),
                    "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
                    "display_aspect_ratio": stream.get("display_aspect_ratio"),
                    "pix_fmt": stream.get("pix_fmt"),
                    "color_space": stream.get("color_space"),
                    "color_transfer": stream.get("color_transfer"),
                    "color_primaries": stream.get("color_primaries"),
                    "color_range": stream.get("color_range"),
                    "chroma_location": stream.get("chroma_location"),
                    "level": stream.get("level"),
                    "field_order": stream.get("field_order"),
                }
            )
            if "tags" in stream:
                if "encoder" in stream["tags"]:
                    stream_info["encoder"] = stream["tags"]["encoder"]
                if "handler_name" in stream["tags"]:
                    stream_info["handler"] = stream["tags"]["handler_name"]
                if "rotate" in stream["tags"]:
                    stream_info["rotate"] = stream["tags"]["rotate"]
            for side_data in stream.get("side_data_list", []):
                if "rotation" in side_data and "rotate" not in stream_info:
                    stream_info["rotate"] = side_data.get("rotation")
                if "mastering_display_metadata" in side_data:
                    stream_info["mastering_display_metadata"] = side_data.get(
                        "mastering_display_metadata"
                    )
                if "content_light_level" in side_data:
                    stream_info["content_light_level"] = side_data.get("content_light_level")
            info["video"] = stream_info

        elif stream_type == "audio":
            stream_info.update(
                {
                    "sample_rate": stream.get("sample_rate"),
                    "sample_fmt": stream.get("sample_fmt"),
                    "channels": stream.get("channels"),
                    "channel_layout": stream.get("channel_layout"),
                    "bits_per_sample": stream.get("bits_per_sample"),
                }
            )
            if "tags" in stream and "handler_name" in stream["tags"]:
                stream_info["handler"] = stream["tags"]["handler_name"]
            info["audio"] = stream_info

    # x264/x265 encoding options from strings
    x264_match = re.search(r"x264[^\n]*options:[^\n]+", combined)
    if x264_match:
        info["x264_options"] = x264_match.group(0)[:500]

    return info


def parse_custom_tags(strings: list[str], ffprobe_data: dict[str, Any]) -> dict[str, Any]:
    """Parse custom and vendor-specific tags."""
    tags: dict[str, Any] = {}
    combined = "\n".join(strings)

    # Handler names (often indicate source)
    handler_patterns = [
        (r"handler[_\s]*name[:\s]*([^\n]+)", "handler_name"),
        (r"vendor[_\s]*id[:\s]*([^\n]+)", "vendor_id"),
    ]

    for pattern, key in handler_patterns:
        matches = re.findall(pattern, combined, re.IGNORECASE)
        if matches:
            unique = list({m.strip() for m in matches if m.strip()})
            if unique:
                tags[key] = unique

    # Known software signatures
    software_patterns = {
        "Google": r"Google|YouTube",
        "Apple": r"Apple|QuickTime|iPhone|iPad|Mac",
        "Adobe": r"Adobe|Premiere|After Effects",
        "DaVinci": r"DaVinci|Blackmagic",
        "FFmpeg": r"Lavf|Lavc|FFmpeg",
        "HandBrake": r"HandBrake",
        "OBS": r"OBS Studio|obs-output",
        "VLC": r"VLC media player",
    }

    detected_software: list[str] = []
    for name, pattern in software_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            detected_software.append(name)
    if detected_software:
        tags["detected_software"] = detected_software

    # From ffprobe format tags
    if "format" in ffprobe_data and "tags" in ffprobe_data["format"]:
        fmt_tags = ffprobe_data["format"]["tags"]
        for key, value in fmt_tags.items():
            if key not in ["major_brand", "minor_version", "compatible_brands"]:
                tags[f"format_{key}"] = value

    return tags


def extract_stream_details(ffprobe_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract detailed stream information for full reports."""
    details: list[dict[str, Any]] = []
    for stream in ffprobe_data.get("streams", []):
        detail: dict[str, Any] = {
            "index": stream.get("index"),
            "codec_type": stream.get("codec_type"),
            "codec_name": stream.get("codec_name"),
            "codec_long_name": stream.get("codec_long_name"),
            "profile": stream.get("profile"),
            "level": stream.get("level"),
            "codec_tag": stream.get("codec_tag_string"),
            "bit_rate": stream.get("bit_rate"),
            "time_base": stream.get("time_base"),
            "start_time": stream.get("start_time"),
            "duration": stream.get("duration"),
            "duration_ts": stream.get("duration_ts"),
            "nb_frames": stream.get("nb_frames"),
            "disposition": stream.get("disposition", {}),
            "tags": stream.get("tags", {}),
            "side_data_list": stream.get("side_data_list", []),
        }
        if stream.get("codec_type") == "video":
            detail.update(
                {
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "r_frame_rate": stream.get("r_frame_rate"),
                    "avg_frame_rate": stream.get("avg_frame_rate"),
                    "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
                    "display_aspect_ratio": stream.get("display_aspect_ratio"),
                    "pix_fmt": stream.get("pix_fmt"),
                    "color_space": stream.get("color_space"),
                    "color_transfer": stream.get("color_transfer"),
                    "color_primaries": stream.get("color_primaries"),
                    "color_range": stream.get("color_range"),
                    "chroma_location": stream.get("chroma_location"),
                    "field_order": stream.get("field_order"),
                }
            )
        elif stream.get("codec_type") == "audio":
            detail.update(
                {
                    "sample_rate": stream.get("sample_rate"),
                    "sample_fmt": stream.get("sample_fmt"),
                    "channels": stream.get("channels"),
                    "channel_layout": stream.get("channel_layout"),
                    "bits_per_sample": stream.get("bits_per_sample"),
                }
            )
        details.append(detail)
    return details


def extract_interesting_strings(strings: list[str]) -> list[str]:
    """Extract interesting/relevant strings."""
    interesting: list[str] = []
    keywords = [
        "copyright",
        "author",
        "creator",
        "title",
        "description",
        "comment",
        "artist",
        "album",
        "genre",
        "date",
        "year",
        "encoder",
        "software",
        "tool",
        "http",
        "https",
        "www",
        "c2pa",
        "xmp",
        "sora",
        "openai",
        "adobe",
        "google",
        "apple",
        "microsoft",
        "ai",
        "generated",
        "synthetic",
        "manifest",
        "signature",
        "certificate",
        "license",
        "gps",
        "location",
        "latitude",
        "longitude",
    ]

    for s in strings:
        s_lower = s.lower()
        if 5 < len(s) < 500 and any(kw in s_lower for kw in keywords) and s not in interesting:
            interesting.append(s)

    return interesting[:50]


def analyze_file(file_path: str) -> MetadataReport:
    """Analyze media file and extract all metadata."""
    report = MetadataReport(file_path=file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Basic file info
    report.file_info = get_file_info(file_path)

    # Container box structure
    ext = str(report.file_info["extension"])
    if ext in [".mp4", ".m4v", ".m4a", ".mov", ".3gp", ".3g2"]:
        report.box_structure = parse_mp4_boxes(file_path)
        report.container_info = {
            "type": "MP4/MOV",
            "total_boxes": len(report.box_structure),
        }

    # FFprobe metadata
    ffprobe_data = get_ffprobe_metadata(file_path)
    report.ffprobe_raw = ffprobe_data
    if "format" in ffprobe_data:
        fmt = ffprobe_data["format"]
        report.format_tags = fmt.get("tags", {})
        report.container_info.update(
            {
                "format": fmt.get("format_long_name"),
                "format_short": fmt.get("format_name"),
                "duration": fmt.get("duration"),
                "bit_rate": fmt.get("bit_rate"),
                "nb_streams": fmt.get("nb_streams"),
                "size": fmt.get("size"),
                "start_time": fmt.get("start_time"),
                "probe_score": fmt.get("probe_score"),
            }
        )

    report.streams = ffprobe_data.get("streams", [])
    report.stream_details = extract_stream_details(ffprobe_data)
    report.chapters = ffprobe_data.get("chapters", [])
    report.programs = ffprobe_data.get("programs", [])

    # Mediainfo/ExifTool metadata
    report.mediainfo_raw = get_mediainfo_metadata(file_path)
    report.exiftool_raw = get_exiftool_metadata(file_path)

    # Extract strings
    strings = extract_strings(file_path)

    # Parse various metadata types
    report.c2pa_info = parse_c2pa_info(strings, file_path)
    report.xmp_metadata = parse_xmp_metadata(strings)
    report.creation_info = parse_creation_info(strings, ffprobe_data)
    report.encoding_info = parse_encoding_info(ffprobe_data, strings)
    report.gps_info = parse_gps_info(strings)
    report.custom_tags = parse_custom_tags(strings, ffprobe_data)
    report.raw_strings = extract_interesting_strings(strings)

    return report
