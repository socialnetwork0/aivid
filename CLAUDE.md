# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Setup (use uv, not pip)
uv venv
uv pip install -e ".[dev]"

# Run CLI
aivid video.mp4
aivid --c2pa video.mp4      # AI detection focus
aivid --full video.mp4      # Full metadata
aivid --status              # Show extractor availability

# Testing
uv run pytest                           # Run all tests
uv run pytest tests/test_metadata.py    # Run single test file
uv run pytest -k "test_name"            # Run tests matching pattern

# Code quality
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run mypy src             # Type check
```

## Architecture Overview

### Plugin System

The codebase uses a plugin architecture with four extension points:

1. **Extractors** (`src/aivid/extractors/`) - Extract metadata from video files
   - Each extractor extends `BaseExtractor` with `is_available()` and `extract(path, metadata)`
   - Priority system: lower number = runs first (FFprobe=10, ExifTool=15, C2PATools=25, Heuristic=90)
   - Extractors mutate the `VideoMetadata` object in place

2. **Downloaders** (`src/aivid/downloaders/`) - Download videos from platforms (YouTube, TikTok, Sora)
   - Each extends `BaseDownloader`
   - Returns `(file_path, SourceInfo)` tuple

3. **Detectors** (`src/aivid/detectors/`) - Watermark detection (AudioSeal, VideoSeal)
   - Each extends `BaseDetector`
   - Heavy ML dependencies, optional install

4. **Formatters** (`src/aivid/formatters/`) - Output formatting (default, full, c2pa, json, quiet)

### Data Flow

```
analyze_file(path)
  → get_file_info()              # Basic file stats
  → get_available_extractors()   # Get enabled extractors sorted by priority
  → extractor.extract()          # Each extractor populates VideoMetadata
  → parse_mp4_boxes()            # Container structure (MP4/MOV only)
  → VideoMetadata                # Unified pydantic model
```

### Models (`src/aivid/models/`)

`VideoMetadata` is the central pydantic model containing:
- `file_info` - Path, size, timestamps (FileInfo)
- `technical` - Codec, resolution, bitrate (TechnicalMetadata)
- `descriptive` - XMP/EXIF/IPTC metadata (DescriptiveMetadata)
- `provenance` - C2PA credentials, watermarks (ProvenanceMetadata)
- `ai_detection` - AI generation signals (AIDetectionResult)
- `raw` - Raw tool output for debugging (RawMetadata)

### Key Design Patterns

- **Graceful degradation**: Extractors/detectors that fail don't break analysis
- **Optional dependencies**: Features like watermark detection require separate installs (`pip install aivid[watermark]`)
- **Priority-based execution**: Extractors run in priority order; later extractors can use earlier results

## System Dependencies

Required: `ffprobe` (part of ffmpeg)
Optional: `mediainfo`, `exiftool`, `c2patool`
