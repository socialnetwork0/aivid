"""Output formatters for aivid."""

import json

from aivid.models import MetadataReport


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
        lines.append("[+] C2PA METADATA DETECTED")
        lines.append("-" * 40)
        for key, value in report.c2pa_info.items():
            if value:
                if isinstance(value, list):
                    lines.append(f"  {key}: {', '.join(value)}")
                else:
                    lines.append(f"  {key}: {value}")
    else:
        lines.append("[-] NO C2PA METADATA FOUND")

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


def report_to_dict(report: MetadataReport) -> dict[str, object]:
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


def report_to_json(report: MetadataReport, indent: int = 2) -> str:
    """Convert report to JSON string."""
    return json.dumps(report_to_dict(report), indent=indent, ensure_ascii=False, default=str)
