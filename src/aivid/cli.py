"""
Command-line interface for aivid.

Usage:
  aivid video.mp4                    # Default mode
  aivid --full video.mp4             # Full details
  aivid --c2pa video.mp4             # C2PA/AI detection focus
  aivid -o report.json *.mp4         # JSON export
  aivid -q *.mp4                     # Quick summary
  aivid --sign manifest.json -o out.mp4 video.mp4  # Sign with C2PA
"""

import argparse
import json
import sys

from aivid import __version__
from aivid.formatters import format_c2pa_report, format_report, report_to_dict
from aivid.metadata import analyze_file, check_c2patool_available, sign_with_c2pa


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

Signing (requires c2patool):
  --sign       Sign file with C2PA manifest (requires -o for output)

Examples:
  aivid video.mp4                    # Default mode
  aivid --full video.mp4             # Full details
  aivid --c2pa video.mp4             # C2PA/AI detection
  aivid -o report.json *.mp4         # JSON export
  aivid -q *.mp4                     # Quick summary
  aivid --sign manifest.json -o signed.mp4 video.mp4  # Sign with C2PA
        """,
    )
    parser.add_argument("files", nargs="+", help="Media file(s) to analyze")
    parser.add_argument("-o", "--output", help="Save report to JSON file")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

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

    args = parser.parse_args()

    # Handle signing mode
    if args.sign:
        if not args.output:
            print("Error: --sign requires -o/--output for signed file path", file=sys.stderr)
            return 1
        if len(args.files) != 1:
            print("Error: --sign requires exactly one input file", file=sys.stderr)
            return 1

        if not check_c2patool_available():
            print(
                "Error: c2patool not found. Install with: cargo install c2patool", file=sys.stderr
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

    all_reports = []
    errors = 0

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
            errors += 1
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
            errors += 1

    # JSON export
    if args.output and all_reports:
        output_data = [report_to_dict(r) for r in all_reports]
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"Report saved to: {args.output}")

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
