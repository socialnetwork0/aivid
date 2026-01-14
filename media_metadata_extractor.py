#!/usr/bin/env python3
"""
Media Metadata Extractor

Extract metadata from video/audio files with multiple output modes.

Modes:
  (default)    Basic metadata: file info, container, encoding, C2PA summary
  --full       Full details: all metadata including mediainfo, exiftool, streams
  --c2pa       C2PA focus: AI content detection with indicators and confidence
  -q/--quiet   Quick summary only

Examples:
  python media_metadata_extractor.py video.mp4              # Default mode
  python media_metadata_extractor.py --full video.mp4       # Full details
  python media_metadata_extractor.py --c2pa video.mp4       # C2PA/AI detection
  python media_metadata_extractor.py -o report.json *.mp4   # JSON export
  python media_metadata_extractor.py -q *.mp4               # Quick summary

Features:
- Basic file info (size, timestamps, format)
- Container structure (MP4 boxes/atoms)
- Stream information (video, audio, subtitles)
- Technical encoding details (codec, bitrate, resolution)
- C2PA/AI generation markers (Sora, Gemini, etc.)
- XMP metadata
- EXIF-like tags (via exiftool)
- Custom vendor tags
- GPS/Location data
- Mediainfo integration
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class MetadataReport:
    """Complete metadata report."""

    file_path: str = ""
    file_info: dict = field(default_factory=dict)
    container_info: dict = field(default_factory=dict)
    box_structure: list = field(default_factory=list)
    streams: list = field(default_factory=list)
    stream_details: list = field(default_factory=list)
    format_tags: dict = field(default_factory=dict)
    c2pa_info: dict = field(default_factory=dict)
    xmp_metadata: dict = field(default_factory=dict)
    creation_info: dict = field(default_factory=dict)
    encoding_info: dict = field(default_factory=dict)
    gps_info: dict = field(default_factory=dict)
    custom_tags: dict = field(default_factory=dict)
    raw_strings: list = field(default_factory=list)
    chapters: list = field(default_factory=list)
    programs: list = field(default_factory=list)
    ffprobe_raw: dict = field(default_factory=dict)
    mediainfo_raw: dict = field(default_factory=dict)
    exiftool_raw: dict = field(default_factory=dict)


def get_file_info(file_path: str) -> dict:
    """Get basic file information."""
    stat = os.stat(file_path)
    return {
        "filename": os.path.basename(file_path),
        "path": os.path.abspath(file_path),
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_birthtime).isoformat()
        if hasattr(stat, "st_birthtime")
        else None,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "extension": Path(file_path).suffix.lower(),
    }


def format_size(size: int) -> str:
    """Format size in human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def parse_mp4_boxes(file_path: str, max_depth: int = 5) -> list:
    """Parse MP4/MOV box structure."""
    boxes = []

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

    def parse_boxes(f, start: int, end: int, depth: int):
        f.seek(start)
        while f.tell() < end:
            pos = f.tell()
            header = f.read(8)
            if len(header) < 8:
                break

            size, box_type = struct.unpack(">I4s", header)
            try:
                box_type = box_type.decode("ascii")
            except UnicodeDecodeError:
                box_type = box_type.decode("latin-1", errors="replace")

            # Handle extended size
            if size == 1:
                ext_size = f.read(8)
                if len(ext_size) == 8:
                    size = struct.unpack(">Q", ext_size)[0]
            elif size == 0:
                size = end - pos

            if size < 8 or pos + size > end:
                break

            box_info = {
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


def get_ffprobe_metadata(file_path: str) -> dict:
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
        return json.loads(result.stdout) if result.stdout else {}
    except FileNotFoundError:
        return {"error": "ffprobe not found"}
    except Exception as e:
        return {"error": str(e)}


def extract_strings(file_path: str, min_length: int = 4) -> list:
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


def get_mediainfo_metadata(file_path: str) -> dict:
    """Get comprehensive metadata using mediainfo."""
    try:
        result = subprocess.run(
            ["mediainfo", "--Output=JSON", file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.loads(result.stdout) if result.stdout else {}
    except FileNotFoundError:
        return {"error": "mediainfo not found"}
    except Exception as e:
        return {"error": str(e)}


def get_exiftool_metadata(file_path: str) -> dict:
    """Get metadata using exiftool."""
    try:
        result = subprocess.run(
            ["exiftool", "-j", "-G", "-n", file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        data = json.loads(result.stdout) if result.stdout else []
        return data[0] if isinstance(data, list) and data else data
    except FileNotFoundError:
        return {"error": "exiftool not found"}
    except Exception as e:
        return {"error": str(e)}


def parse_c2pa_info(strings: list, file_path: str) -> dict:
    """Parse C2PA manifest information."""
    combined = "\n".join(strings)
    info = {}

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
    authorities = []
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


def parse_xmp_metadata(strings: list) -> dict:
    """Parse XMP metadata from strings."""
    combined = "\n".join(strings)
    xmp = {}

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


def parse_gps_info(strings: list) -> dict:
    """Parse GPS/location information."""
    combined = "\n".join(strings)
    gps = {}

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


def parse_creation_info(strings: list, ffprobe_data: dict) -> dict:
    """Parse creation and modification timestamps."""
    info = {}
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


def parse_encoding_info(ffprobe_data: dict, strings: list) -> dict:
    """Parse encoding information."""
    info = {}
    combined = "\n".join(strings)

    # From ffprobe streams
    for stream in ffprobe_data.get("streams", []):
        stream_type = stream.get("codec_type", "unknown")
        stream_info = {
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


def parse_custom_tags(strings: list, ffprobe_data: dict) -> dict:
    """Parse custom and vendor-specific tags."""
    tags = {}
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

    detected_software = []
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


def extract_stream_details(ffprobe_data: dict) -> list:
    """Extract detailed stream information for full reports."""
    details = []
    for stream in ffprobe_data.get("streams", []):
        detail = {
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


def extract_interesting_strings(strings: list) -> list:
    """Extract interesting/relevant strings."""
    interesting = []
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
    ext = report.file_info["extension"]
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
        report.format_tags = ffprobe_data["format"].get("tags", {})
        report.container_info.update(
            {
                "format": ffprobe_data["format"].get("format_long_name"),
                "format_short": ffprobe_data["format"].get("format_name"),
                "duration": ffprobe_data["format"].get("duration"),
                "bit_rate": ffprobe_data["format"].get("bit_rate"),
                "nb_streams": ffprobe_data["format"].get("nb_streams"),
                "size": ffprobe_data["format"].get("size"),
                "start_time": ffprobe_data["format"].get("start_time"),
                "probe_score": ffprobe_data["format"].get("probe_score"),
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


def format_c2pa_report(report: MetadataReport) -> str:
    """Format C2PA-focused report for AI content detection."""
    lines = []
    filename = report.file_info.get("filename", "Unknown")

    lines.append("=" * 70)
    lines.append("C2PA / AI CONTENT DETECTION REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Quick summary
    lines.append(f"File: {filename}")
    lines.append(f"Size: {report.file_info.get('size_human', 'N/A')}")
    lines.append("")

    # C2PA Detection Result
    has_c2pa = report.c2pa_info.get("has_c2pa", False)
    if has_c2pa:
        lines.append("[✓] C2PA METADATA DETECTED")
        lines.append("-" * 40)
        for key, value in report.c2pa_info.items():
            if value:
                if isinstance(value, list):
                    lines.append(f"  {key}: {', '.join(value)}")
                else:
                    lines.append(f"  {key}: {value}")
    else:
        lines.append("[✗] NO C2PA METADATA FOUND")

    lines.append("")

    # AI Generation Indicators (heuristics)
    lines.append("## AI GENERATION INDICATORS")
    lines.append("-" * 40)

    indicators = []

    # Check audio sample rate (96kHz is Sora signature)
    audio_info = report.encoding_info.get("audio", {})
    sample_rate = audio_info.get("sample_rate")
    if sample_rate:
        if sample_rate == "96000":
            indicators.append(("Audio 96kHz", "HIGH", "Sora signature"))
        lines.append(f"  Audio sample rate: {sample_rate} Hz")

    # Check encoder
    video_info = report.encoding_info.get("video", {})
    encoder = report.format_tags.get("encoder", "")
    if encoder:
        if encoder == "Google":
            indicators.append(("Encoder=Google", "HIGH", "Gemini/Veo signature"))
        lines.append(f"  Encoder: {encoder}")

    # Check handler name
    handler = video_info.get("handler", "")
    if handler:
        if "Google" in handler:
            indicators.append(("Google handler", "MEDIUM", "YouTube/Google origin"))
        if "Mainconcept" in handler:
            indicators.append(("Mainconcept", "MEDIUM", "Possible Luma"))
        lines.append(f"  Handler: {handler}")

    # Check detected software
    detected_sw = report.custom_tags.get("detected_software", [])
    if detected_sw:
        lines.append(f"  Detected software: {', '.join(detected_sw)}")

    # Check signing authorities from C2PA
    authorities = report.c2pa_info.get("signing_authorities", [])
    if authorities:
        for auth in authorities:
            if auth == "OpenAI":
                indicators.append(("OpenAI signed", "HIGH", "Sora/DALL-E"))
            elif auth == "Google":
                indicators.append(("Google signed", "HIGH", "Gemini/Veo"))

    lines.append("")

    # Summary of indicators
    if indicators:
        lines.append("## DETECTION SUMMARY")
        lines.append("-" * 40)
        for name, confidence, note in indicators:
            lines.append(f"  [{confidence}] {name} - {note}")
    else:
        lines.append("## DETECTION SUMMARY")
        lines.append("-" * 40)
        lines.append("  No strong AI generation indicators found")
        lines.append("  (This does NOT mean the video is not AI-generated)")

    lines.append("")

    # Video basic info for context
    lines.append("## VIDEO INFO")
    lines.append("-" * 40)
    lines.append(
        f"  Resolution: {video_info.get('width', 'N/A')}x{video_info.get('height', 'N/A')}"
    )
    lines.append(f"  Frame rate: {video_info.get('frame_rate', 'N/A')}")
    lines.append(f"  Duration: {report.container_info.get('duration', 'N/A')}s")
    lines.append(f"  Codec: {video_info.get('codec', 'N/A')} ({video_info.get('profile', '')})")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def format_report(report: MetadataReport, full: bool = False) -> str:
    """Format report as readable text (default mode)."""
    lines = []
    lines.append("=" * 70)
    lines.append("MEDIA METADATA REPORT")
    lines.append("=" * 70)
    lines.append("")

    # File Info
    lines.append("## FILE INFORMATION")
    for key, value in report.file_info.items():
        if value:
            lines.append(f"  {key}: {value}")
    lines.append("")

    # Container Info
    if report.container_info:
        lines.append("## CONTAINER INFORMATION")
        for key, value in report.container_info.items():
            if value:
                lines.append(f"  {key}: {value}")
        lines.append("")

    # Encoding Info
    if report.encoding_info:
        lines.append("## ENCODING INFORMATION")
        for stream_type, stream_info in report.encoding_info.items():
            if isinstance(stream_info, dict):
                lines.append(f"  [{stream_type.upper()}]")
                for key, value in stream_info.items():
                    if value:
                        lines.append(f"    {key}: {value}")
            else:
                lines.append(f"  {stream_type}: {str(stream_info)[:100]}")
        lines.append("")

    # C2PA Info (always show in default mode if present)
    if report.c2pa_info:
        lines.append("## C2PA / AI GENERATION INFO")
        for key, value in report.c2pa_info.items():
            if value:
                if isinstance(value, list):
                    lines.append(f"  {key}: {', '.join(value)}")
                else:
                    lines.append(f"  {key}: {value}")
        lines.append("")

    # Custom Tags (show detected software)
    if report.custom_tags.get("detected_software"):
        lines.append("## DETECTED SOFTWARE")
        lines.append(f"  {', '.join(report.custom_tags['detected_software'])}")
        lines.append("")

    # === FULL MODE: Show everything below ===
    if full:
        # Creation Info
        if report.creation_info:
            lines.append("## CREATION INFORMATION")
            for key, value in report.creation_info.items():
                if value:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # XMP Metadata
        if report.xmp_metadata:
            lines.append("## XMP METADATA")
            for key, value in report.xmp_metadata.items():
                if value:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # GPS Info
        if report.gps_info:
            lines.append("## GPS / LOCATION")
            for key, value in report.gps_info.items():
                if value:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # All Custom Tags
        if report.custom_tags:
            lines.append("## CUSTOM / VENDOR TAGS")
            for key, value in report.custom_tags.items():
                if value:
                    if isinstance(value, list):
                        lines.append(f"  {key}: {', '.join(str(v) for v in value)}")
                    else:
                        lines.append(f"  {key}: {value}")
            lines.append("")

        # Format Tags
        if report.format_tags:
            lines.append("## FORMAT TAGS")
            for key, value in report.format_tags.items():
                if value:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # Mediainfo summary
        if report.mediainfo_raw and not report.mediainfo_raw.get("error"):
            lines.append("## MEDIAINFO")
            media = report.mediainfo_raw.get("media", {})
            tracks = media.get("track", [])
            lines.append(f"  tracks: {len(tracks)}")
            for track in tracks:
                track_type = track.get("@type", "Unknown")
                lines.append(f"  [{track_type}]")
                important_keys = [
                    "Format",
                    "CodecID",
                    "Duration",
                    "BitRate",
                    "Width",
                    "Height",
                    "FrameRate",
                    "SamplingRate",
                    "Channels",
                    "Encoded_Library",
                ]
                for k in important_keys:
                    if k in track:
                        lines.append(f"    {k}: {track[k]}")
            lines.append("")

        # Exiftool summary
        if report.exiftool_raw and not report.exiftool_raw.get("error"):
            lines.append("## EXIFTOOL")
            lines.append(f"  Total tags: {len(report.exiftool_raw.keys())}")
            # Show interesting tags
            interesting_prefixes = ["QuickTime:", "XMP:", "Composite:"]
            for key, value in report.exiftool_raw.items():
                if any(key.startswith(p) for p in interesting_prefixes):
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # Stream Details
        if report.stream_details:
            lines.append("## STREAM DETAILS")
            for stream in report.stream_details:
                lines.append(f"  [STREAM {stream.get('index')}]")
                for key, value in stream.items():
                    if key == "index" or value in [None, "", [], {}]:
                        continue
                    if isinstance(value, dict):
                        lines.append(f"    {key}:")
                        for sub_key, sub_val in value.items():
                            if sub_val not in [None, "", [], {}]:
                                lines.append(f"      {sub_key}: {sub_val}")
                    elif isinstance(value, list):
                        lines.append(f"    {key}:")
                        for item in value[:20]:
                            lines.append(f"      {str(item)[:200]}")
                        if len(value) > 20:
                            lines.append(f"      ... and {len(value) - 20} more")
                    else:
                        lines.append(f"    {key}: {str(value)[:200]}")
            lines.append("")

        # Chapters
        if report.chapters:
            lines.append("## CHAPTERS")
            for chapter in report.chapters[:50]:
                lines.append(f"  {str(chapter)[:400]}")
            if len(report.chapters) > 50:
                lines.append(f"  ... and {len(report.chapters) - 50} more")
            lines.append("")

        # Programs
        if report.programs:
            lines.append("## PROGRAMS")
            for program in report.programs[:50]:
                lines.append(f"  {str(program)[:400]}")
            if len(report.programs) > 50:
                lines.append(f"  ... and {len(report.programs) - 50} more")
            lines.append("")

        # Box Structure
        if report.box_structure:
            lines.append("## MP4 BOX STRUCTURE")
            for box in report.box_structure[:50]:
                indent = "  " * box.get("depth", 0)
                lines.append(
                    f"  {indent}{box['type']:8s} size={box['size']:>12,}  offset={box['offset']}"
                )
            if len(report.box_structure) > 50:
                lines.append(f"  ... and {len(report.box_structure) - 50} more boxes")
            lines.append("")

        # Interesting Strings
        if report.raw_strings:
            lines.append("## INTERESTING STRINGS")
            for s in report.raw_strings[:30]:
                lines.append(f"  {s[:150]}")
            if len(report.raw_strings) > 30:
                lines.append(f"  ... and {len(report.raw_strings) - 30} more")
            lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def report_to_dict(report: MetadataReport) -> dict:
    """Convert report to dictionary for JSON export."""
    return {
        "file_path": report.file_path,
        "file_info": report.file_info,
        "container_info": report.container_info,
        "box_structure": report.box_structure,
        "streams": report.streams,
        "stream_details": report.stream_details,
        "format_tags": report.format_tags,
        "c2pa_info": report.c2pa_info,
        "xmp_metadata": report.xmp_metadata,
        "creation_info": report.creation_info,
        "encoding_info": report.encoding_info,
        "gps_info": report.gps_info,
        "custom_tags": report.custom_tags,
        "raw_strings": report.raw_strings,
        "chapters": report.chapters,
        "programs": report.programs,
        "ffprobe_raw": report.ffprobe_raw,
        "mediainfo_raw": report.mediainfo_raw,
        "exiftool_raw": report.exiftool_raw,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract metadata from video/audio files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (default)    Basic metadata: file info, container, encoding, C2PA summary
  --full       Full details: all metadata including mediainfo, exiftool, streams
  --c2pa       C2PA focus: AI content detection with indicators and confidence

Examples:
  python media_metadata_extractor.py video.mp4              # Default mode
  python media_metadata_extractor.py --full video.mp4       # Full details
  python media_metadata_extractor.py --c2pa video.mp4       # C2PA/AI detection
  python media_metadata_extractor.py -o report.json *.mp4   # JSON export
  python media_metadata_extractor.py -q *.mp4               # Quick summary
        """,
    )
    parser.add_argument("files", nargs="+", help="Media file(s) to analyze")
    parser.add_argument("-o", "--output", help="Save report to JSON file")

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Full mode: show all metadata details",
    )
    mode_group.add_argument(
        "--c2pa",
        action="store_true",
        help="C2PA mode: focus on AI content detection",
    )
    mode_group.add_argument("-q", "--quiet", action="store_true", help="Quick summary only")

    args = parser.parse_args()

    all_reports = []

    for file_path in args.files:
        try:
            print(f"Analyzing: {file_path}")
            report = analyze_file(file_path)
            all_reports.append(report)

            if args.quiet:
                # Quick summary
                c2pa = "C2PA" if report.c2pa_info.get("has_c2pa") else ""
                gen = report.c2pa_info.get("generator", "")
                sw = ", ".join(report.custom_tags.get("detected_software", []))
                print(f"  Format: {report.container_info.get('format', 'Unknown')}")
                print(f"  Duration: {report.container_info.get('duration', 'N/A')}s")
                if c2pa:
                    print(f"  AI Content: {c2pa} - {gen}")
                if sw:
                    print(f"  Software: {sw}")
            elif args.c2pa:
                # C2PA mode
                print(format_c2pa_report(report))
            else:
                # Default or full mode
                print(format_report(report, full=args.full))

            print()

        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    # JSON export
    if args.output and all_reports:
        output_data = [report_to_dict(r) for r in all_reports]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
