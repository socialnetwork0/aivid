# aivid

> AI video toolkit - detect, analyze, and work with AI-generated videos

[![PyPI version](https://badge.fury.io/py/aivid.svg)](https://badge.fury.io/py/aivid)
[![Python versions](https://img.shields.io/pypi/pyversions/aivid)](https://pypi.org/project/aivid/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/SocialNetwork0/aivid/workflows/CI/badge.svg)](https://github.com/SocialNetwork0/aivid/actions)

## Features

- **AI Detection**: Detect AI-generated videos through C2PA metadata and heuristic analysis
- **Metadata Extraction**: Extract comprehensive metadata from video files
- **Multi-tool Support**: Leverages ffprobe, mediainfo, and exiftool for thorough analysis
- **Multiple Output Modes**: Default summary, full details, C2PA focus, or quiet mode
- **JSON Export**: Export reports for automation and integration

## Supported AI Generators

| Generator | Detection Method | Confidence |
|-----------|------------------|------------|
| OpenAI Sora | C2PA manifest + 96kHz audio signature | High |
| Google Gemini/Veo | Encoder tag | High |
| Luma AI | Handler name | Medium |
| Pika Labs | C2PA manifest | Medium |
| Adobe Firefly | C2PA manifest | High |

## Requirements

### System Dependencies

aivid requires these command-line tools to be installed:

- **ffprobe** (required) - Part of FFmpeg
- **mediainfo** (optional, recommended)
- **exiftool** (optional, recommended)
- **c2patool** (optional) - For accurate C2PA manifest parsing and signing

#### macOS

```bash
brew install ffmpeg mediainfo exiftool
```

#### Ubuntu/Debian

```bash
sudo apt-get install ffmpeg mediainfo exiftool
```

#### Windows

```powershell
# Using Chocolatey
choco install ffmpeg mediainfo exiftool

# Or using Scoop
scoop install ffmpeg mediainfo exiftool
```

#### Install c2patool (optional)

c2patool provides more accurate C2PA manifest parsing and signing capabilities.

```bash
# Using Cargo (Rust package manager)
cargo install c2patool

# Or download prebuilt binaries from:
# https://github.com/contentauth/c2pa-rs/releases
```

### Python Installation

```bash
pip install aivid
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install aivid
```

## Quick Start

### Command Line

```bash
# Basic analysis
aivid video.mp4

# AI detection focus (C2PA mode)
aivid --c2pa video.mp4

# Full metadata details
aivid --full video.mp4

# Quick summary for multiple files
aivid -q *.mp4

# Export to JSON
aivid -o report.json video.mp4

# Sign a file with C2PA manifest (requires c2patool)
aivid --sign manifest.json -o signed_video.mp4 video.mp4
```

### Python API

```python
from aivid import analyze_file

# Analyze a video file
report = analyze_file("video.mp4")

# Check if AI-generated
if report.is_ai_generated:
    print(f"AI Generator: {report.ai_generator}")

# Access metadata
print(f"Duration: {report.container_info.get('duration')}s")
print(f"Resolution: {report.encoding_info['video']['width']}x{report.encoding_info['video']['height']}")

# C2PA information
if report.c2pa_info:
    print(f"C2PA Manifest: {report.c2pa_info.get('manifest_id')}")
    print(f"Signing Authority: {report.c2pa_info.get('signing_authorities')}")
```

## Output Modes

### Default Mode

Basic metadata with file info, container details, encoding info, and C2PA summary.

```bash
aivid video.mp4
```

### C2PA Mode (`--c2pa`)

Focused on AI content detection with indicators and confidence levels.

```bash
aivid --c2pa video.mp4
```

Output includes:
- C2PA manifest detection
- AI generation indicators (audio sample rate, encoder tags, etc.)
- Detection summary with confidence levels

Note: When c2patool is installed, aivid uses it for more accurate C2PA parsing.

### Full Mode (`--full`)

Complete metadata dump including mediainfo, exiftool, all streams, and raw data.

```bash
aivid --full video.mp4
```

### Quiet Mode (`-q`)

One-line summary per file, ideal for batch processing.

```bash
aivid -q *.mp4
```

### Sign Mode (`--sign`)

Add a C2PA manifest to a media file (requires c2patool).

```bash
# Create a manifest file
cat > manifest.json << 'EOF'
{
  "claim_generator": "aivid",
  "title": "My Video",
  "assertions": [
    {
      "label": "c2pa.actions",
      "data": {
        "actions": [{"action": "c2pa.edited"}]
      }
    }
  ]
}
EOF

# Sign the video
aivid --sign manifest.json -o signed_video.mp4 video.mp4

# Verify the signature
aivid --c2pa signed_video.mp4
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/SocialNetwork0/aivid.git
cd aivid

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [C2PA](https://c2pa.org/) - Coalition for Content Provenance and Authenticity
- [FFmpeg](https://ffmpeg.org/) - Multimedia framework
- [MediaInfo](https://mediaarea.net/en/MediaInfo) - Media file analysis
- [ExifTool](https://exiftool.org/) - Metadata extraction
