"""
Command-line interface for aivid.

Usage:
  aivid video.mp4                    # Default mode
  aivid --full video.mp4             # Full details
  aivid --c2pa video.mp4             # C2PA/AI detection focus
  aivid -o report.json *.mp4         # JSON export
  aivid -q *.mp4                     # Quick summary
  aivid --sign manifest.json -o out.mp4 video.mp4  # Sign with C2PA
  aivid --url "https://youtube.com/watch?v=xxx"    # Analyze from URL
"""

from __future__ import annotations

import argparse
import os
import sys

from aivid._version import __version__
from aivid.analyze import analyze_file
from aivid.extractors import (
    check_c2patool_available,
    get_extractor_status,
    sign_with_c2pa,
)
from aivid.formatters import (
    format_c2pa,
    format_default,
    format_full,
    format_json_list,
    format_quiet,
)


def main() -> int:
    """Main entry point for aivid CLI."""
    parser = argparse.ArgumentParser(
        prog="aivid",
        description="AI video toolkit - detect, analyze, and work with AI-generated videos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (default)    Basic metadata: file info, container, encoding, C2PA summary
  --full       Full details: all metadata including mediainfo, exiftool, streams
  --c2pa       C2PA focus: AI content detection with indicators and confidence
  -q/--quiet   Quick summary only

URL Analysis:
  --url        Analyze video from URL (YouTube, TikTok, Sora)
  --keep       Keep downloaded file after analysis (with --url)

Signing (requires c2patool):
  --sign       Sign file with C2PA manifest (requires -o for output)

Detection Control:
  --no-watermark  Skip watermark detection (faster)

Utilities:
  --status     Show extractor availability status

Examples:
  aivid video.mp4                    # Default mode
  aivid --full video.mp4             # Full details
  aivid --c2pa video.mp4             # C2PA/AI detection
  aivid -o report.json *.mp4         # JSON export
  aivid -q *.mp4                     # Quick summary
  aivid --sign manifest.json -o signed.mp4 video.mp4  # Sign with C2PA
  aivid --url "https://youtube.com/watch?v=xxx"       # Analyze from URL
  aivid --url "https://tiktok.com/@u/video/123" --keep # Keep downloaded file
        """,
    )
    parser.add_argument("files", nargs="*", help="Media file(s) to analyze")
    parser.add_argument("-o", "--output", help="Save report to JSON file")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    # URL analysis options
    parser.add_argument(
        "--url",
        "-u",
        metavar="URL",
        help="Analyze video from URL (YouTube, TikTok, Sora)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep downloaded file after analysis (with --url)",
    )

    # Detection control
    parser.add_argument(
        "--no-watermark",
        action="store_true",
        help="Skip watermark detection (faster)",
    )

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
    mode_group.add_argument(
        "--sign",
        metavar="MANIFEST",
        help="Sign file with C2PA manifest JSON (requires c2patool and -o)",
    )
    mode_group.add_argument(
        "--status",
        action="store_true",
        help="Show extractor availability status",
    )

    args = parser.parse_args()

    # Handle --status mode (no files required)
    if args.status:
        print("aivid status:")
        print("=" * 50)

        # Extractors
        print("\nExtractors:")
        print("-" * 50)
        status = get_extractor_status()
        for name, available in sorted(status.items()):
            icon = "✓" if available else "✗"
            print(f"  {icon} {name}")

        # Downloaders
        print("\nDownloaders:")
        print("-" * 50)
        try:
            from aivid.downloaders import get_available_downloaders

            downloaders = get_available_downloaders()
            for name in ["youtube", "tiktok", "sora"]:
                icon = "✓" if name in downloaders else "✗"
                print(f"  {icon} {name}")
        except ImportError:
            print("  (downloaders module not available)")

        # Watermark detectors
        print("\nWatermark Detectors:")
        print("-" * 50)
        try:
            from aivid.detectors import get_detector_status

            detector_status = get_detector_status()
            for name, available in sorted(detector_status.items()):
                icon = "✓" if available else "✗"
                print(f"  {icon} {name}")
        except ImportError:
            print("  (detectors module not available)")

        print("-" * 50)
        print("\nTimestamp sources (priority order):")
        print("  1. C2PA Action.when  - cryptographically signed")
        print("  2. ExifTool          - XMP/EXIF embedded metadata")
        print("  3. FFprobe           - container tags")
        print("  4. File system       - OS timestamps (least reliable)")
        return 0

    # Handle URL analysis mode
    if args.url:
        return analyze_url(args)

    # Require files for other modes
    if not args.files:
        parser.error("the following arguments are required: files")

    # Handle signing mode
    if args.sign:
        if not args.output:
            print(
                "Error: --sign requires -o/--output for signed file path",
                file=sys.stderr,
            )
            return 1
        if len(args.files) != 1:
            print("Error: --sign requires exactly one input file", file=sys.stderr)
            return 1

        if not check_c2patool_available():
            print(
                "Error: c2patool not found. Install with: cargo install c2patool",
                file=sys.stderr,
            )
            print(
                "       Or download from: https://github.com/contentauth/c2pa-rs/releases",
                file=sys.stderr,
            )
            return 1

        input_file = args.files[0]
        success, message = sign_with_c2pa(input_file, args.sign, args.output)
        print(message)
        return 0 if success else 1

    all_metadata = []
    errors = 0

    for file_path in args.files:
        try:
            print(f"Analyzing: {file_path}")
            metadata = analyze_file(file_path, full=args.full)
            all_metadata.append(metadata)

            if args.quiet:
                # Quick summary
                print(format_quiet(metadata))
            elif args.c2pa:
                # C2PA mode
                print(format_c2pa(metadata))
            elif args.full:
                # Full mode
                print(format_full(metadata))
            else:
                # Default mode
                print(format_default(metadata))

            print()

        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            errors += 1

    # JSON export
    if args.output and all_metadata:
        json_output = format_json_list(all_metadata)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Report saved to: {args.output}")

    return 1 if errors > 0 else 0


def analyze_url(args: argparse.Namespace) -> int:
    """Analyze video from URL.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    from aivid.downloaders import DownloadError, get_downloader_for_url
    from aivid.utils.url_parser import detect_platform

    url = args.url
    platform = detect_platform(url)

    print(f"Detected platform: {platform.value}")

    downloader = get_downloader_for_url(url)
    if not downloader:
        print(f"Error: Unsupported URL: {url}", file=sys.stderr)
        return 1

    if not downloader.is_available():
        print(
            f"Error: {downloader.name} downloader not available. "
            "Install yt-dlp: pip install yt-dlp",
            file=sys.stderr,
        )
        return 1

    try:
        print(f"Downloading from {platform.value}...")
        file_path, source_info = downloader.download(url)
        print(f"Downloaded: {file_path}")

        # Analyze the downloaded file
        print(f"Analyzing: {file_path}")
        metadata = analyze_file(file_path, full=args.full)

        # Attach source info to metadata (if model supports it)
        # Note: This requires updating VideoMetadata model
        # For now, we'll just include it in the output

        # Format output
        if args.quiet:
            print(format_quiet(metadata))
        elif args.c2pa:
            print(format_c2pa(metadata))
        elif args.full:
            print(format_full(metadata))
        else:
            print(format_default(metadata))

        # Show source info
        print("\n## SOURCE INFO")
        print(f"  Platform: {source_info.platform.value}")
        print(f"  Video ID: {source_info.video_id}")
        if source_info.title:
            print(f"  Title: {source_info.title}")
        if source_info.uploader:
            print(f"  Uploader: {source_info.uploader}")
        if source_info.upload_date:
            print(f"  Upload Date: {source_info.upload_date.strftime('%Y-%m-%d')}")

        # JSON export
        if args.output:
            json_output = format_json_list([metadata])
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"\nReport saved to: {args.output}")

        # Cleanup or keep
        if args.keep:
            print(f"\nDownloaded file kept at: {file_path}")
        else:
            try:
                os.unlink(file_path)
                print("\nDownloaded file cleaned up.")
            except OSError:
                pass

        return 0

    except DownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
