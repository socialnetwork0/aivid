# aivid

> AI video toolkit - detect, analyze, and work with AI-generated videos

[![PyPI version](https://badge.fury.io/py/aivid.svg)](https://pypi.org/project/aivid/)
[![Python versions](https://img.shields.io/pypi/pyversions/aivid)](https://pypi.org/project/aivid/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/SocialNetwork0/aivid/workflows/CI/badge.svg)](https://github.com/SocialNetwork0/aivid/actions)

## Features

- **AI Detection**: Detect AI-generated videos through C2PA metadata and heuristic analysis
- **C2PA Signing**: Add C2PA manifests to media files (requires c2patool)
- **Metadata Extraction**: Extract comprehensive metadata from video files
- **Multi-tool Support**: Leverages ffprobe, mediainfo, exiftool, and c2patool for thorough analysis
- **MP4 Box Analysis**: Binary parsing of MP4/MOV container structure
- **Software Detection**: Identify editing software (FFmpeg, Adobe, DaVinci, OBS, etc.)
- **Multiple Output Modes**: Default summary, full details, C2PA focus, or quiet mode
- **JSON Export**: Export reports for automation and integration
- **Batch Processing**: Analyze multiple files with single command

## Supported AI Generators

| Generator | Detection Method | Confidence |
|-----------|------------------|------------|
| OpenAI Sora | C2PA manifest + 96kHz audio signature | High |
| OpenAI DALL-E | C2PA manifest | High |
| Google Gemini/Veo | Encoder tag + C2PA manifest | High |
| Adobe Firefly | C2PA manifest | High |
| Midjourney | C2PA manifest | High |
| Stability AI | C2PA manifest | High |
| Runway | C2PA manifest | Medium |
| Pika Labs | C2PA manifest | Medium |
| Kling AI | C2PA manifest | Medium |
| Luma AI | Handler name + C2PA manifest | Medium |

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
from aivid import analyze_file, check_c2patool_available, sign_with_c2pa, MetadataReport

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

# Sign a file with C2PA manifest (requires c2patool)
if check_c2patool_available():
    sign_with_c2pa(
        input_path="video.mp4",
        output_path="signed_video.mp4",
        manifest_path="manifest.json"
    )
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

### Local CLI usage for testing (方法 2，本地 CLI 测试)

> 方便本地从源码仓库里直接跑 `aivid` 命令做测试（你现在用的就是这种方式）

```bash
cd /Users/yuanlu/Code/ai-video-tools

# 1. 创建并激活虚拟环境（只需创建一次，之后每次只需激活）
uv venv
source .venv/bin/activate  # macOS / Linux

# 2. 以开发模式安装当前仓库（代码改动会立刻反映到 CLI）
uv pip install -e ".[dev]"

# 3. 在这个虚拟环境里使用 aivid 命令进行测试
aivid --help

# 示例：对 data 目录下的视频做一次基础分析
aivid data/sora_video/19700121_0310_69650d0aeaec8191bdb986a1b9b2a84f.mp4
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

## Supported File Formats

**Native MP4/MOV parsing:** `.mp4`, `.m4v`, `.m4a`, `.mov`, `.3gp`, `.3g2`

**Other formats:** Any format supported by ffprobe

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [C2PA](https://c2pa.org/) - Coalition for Content Provenance and Authenticity
- [c2patool](https://github.com/contentauth/c2pa-rs) - C2PA command line tool
- [FFmpeg](https://ffmpeg.org/) - Multimedia framework
- [MediaInfo](https://mediaarea.net/en/MediaInfo) - Media file analysis
- [ExifTool](https://exiftool.org/) - Metadata extraction
