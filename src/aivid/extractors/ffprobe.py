"""FFprobe metadata extractor."""

import contextlib
import json
import shutil
import subprocess
from datetime import datetime
from typing import Any, ClassVar

from aivid.extractors.base import BaseExtractor
from aivid.models import VideoMetadata


class FFprobeExtractor(BaseExtractor):
    """Extract metadata using FFprobe.

    FFprobe is the primary extractor for technical metadata including:
    - Container format
    - Video/audio codecs
    - Resolution, frame rate, bitrate
    - Stream information
    """

    name: ClassVar[str] = "ffprobe"
    priority: ClassVar[int] = 10  # Run first

    @classmethod
    def is_available(cls) -> bool:
        """Check if ffprobe is available."""
        return shutil.which("ffprobe") is not None

    def extract(self, path: str, metadata: VideoMetadata) -> None:
        """Extract metadata using ffprobe."""
        probe_data = self._run_ffprobe(path)
        if not probe_data:
            return

        # Store raw data
        metadata.raw.ffprobe = probe_data

        # Parse format/container info
        self._parse_format(probe_data.get("format", {}), metadata)

        # Parse streams
        streams = probe_data.get("streams", [])
        metadata.raw.streams = streams
        self._parse_streams(streams, metadata)

        # Parse chapters
        chapters = probe_data.get("chapters", [])
        metadata.raw.chapters = chapters

        # Parse programs
        programs = probe_data.get("programs", [])
        metadata.raw.programs = programs

        # Store format tags
        format_tags = probe_data.get("format", {}).get("tags", {})
        metadata.raw.format_tags = format_tags

        # Extract descriptive metadata from tags
        self._parse_tags(format_tags, metadata)

    def _run_ffprobe(self, path: str) -> dict[str, Any]:
        """Run ffprobe and return JSON output."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                "-show_programs",
                path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout:
                data: dict[str, Any] = json.loads(result.stdout)
                return data
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return {}

    def _parse_format(self, fmt: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse format/container information."""
        metadata.technical.container = fmt.get("format_name")
        metadata.technical.container_long = fmt.get("format_long_name")

        if "duration" in fmt:
            with contextlib.suppress(ValueError, TypeError):
                metadata.technical.duration = float(fmt["duration"])

        if "bit_rate" in fmt:
            with contextlib.suppress(ValueError, TypeError):
                metadata.technical.bitrate = int(fmt["bit_rate"])

        if "size" in fmt:
            with contextlib.suppress(ValueError, TypeError):
                metadata.technical.size_bytes = int(fmt["size"])

        metadata.technical.nb_streams = fmt.get("nb_streams")

    def _parse_streams(self, streams: list[dict[str, Any]], metadata: VideoMetadata) -> None:
        """Parse stream information."""
        for stream in streams:
            codec_type = stream.get("codec_type")

            if codec_type == "video" and not metadata.technical.video.codec:
                self._parse_video_stream(stream, metadata)
            elif codec_type == "audio" and not metadata.technical.audio.codec:
                self._parse_audio_stream(stream, metadata)

    def _parse_video_stream(self, stream: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse video stream information."""
        video = metadata.technical.video
        video.codec = stream.get("codec_name")
        video.codec_long = stream.get("codec_long_name")
        video.profile = stream.get("profile")
        video.level = stream.get("level")
        video.width = stream.get("width")
        video.height = stream.get("height")
        video.pixel_format = stream.get("pix_fmt")
        video.field_order = stream.get("field_order")

        # Parse frame rate
        fps_str = stream.get("r_frame_rate", "0/1")
        if "/" in str(fps_str):
            try:
                num, den = str(fps_str).split("/")
                if int(den) > 0:
                    video.fps = int(num) / int(den)
            except (ValueError, ZeroDivisionError):
                pass

        avg_fps_str = stream.get("avg_frame_rate", "0/1")
        if "/" in str(avg_fps_str):
            try:
                num, den = str(avg_fps_str).split("/")
                if int(den) > 0:
                    video.avg_fps = int(num) / int(den)
            except (ValueError, ZeroDivisionError):
                pass

        # Parse bitrate
        if "bit_rate" in stream:
            with contextlib.suppress(ValueError, TypeError):
                video.bitrate = int(stream["bit_rate"])

        # Parse duration
        if "duration" in stream:
            with contextlib.suppress(ValueError, TypeError):
                video.duration = float(stream["duration"])

        # Tags
        tags = stream.get("tags", {})
        video.encoder = tags.get("encoder")
        video.handler = tags.get("handler_name")

    def _parse_audio_stream(self, stream: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse audio stream information."""
        audio = metadata.technical.audio
        audio.codec = stream.get("codec_name")
        audio.codec_long = stream.get("codec_long_name")
        audio.profile = stream.get("profile")
        audio.sample_format = stream.get("sample_fmt")
        audio.channels = stream.get("channels")
        audio.channel_layout = stream.get("channel_layout")

        # Parse sample rate
        if "sample_rate" in stream:
            with contextlib.suppress(ValueError, TypeError):
                audio.sample_rate = int(stream["sample_rate"])

        # Parse bitrate
        if "bit_rate" in stream:
            with contextlib.suppress(ValueError, TypeError):
                audio.bitrate = int(stream["bit_rate"])

        # Parse duration
        if "duration" in stream:
            with contextlib.suppress(ValueError, TypeError):
                audio.duration = float(stream["duration"])

        # Tags
        tags = stream.get("tags", {})
        audio.handler = tags.get("handler_name")

    def _parse_tags(self, tags: dict[str, Any], metadata: VideoMetadata) -> None:
        """Parse format tags into descriptive metadata."""
        desc = metadata.descriptive

        # Common tags
        desc.title = tags.get("title")
        desc.creator = tags.get("artist") or tags.get("author")
        desc.description = tags.get("description") or tags.get("comment")
        desc.copyright = tags.get("copyright")
        desc.software = tags.get("encoder") or tags.get("encoding_tool")

        # Genre
        desc.genre = tags.get("genre")

        # Parse creation_time from container tags
        creation_time = tags.get("creation_time")
        if creation_time:
            with contextlib.suppress(ValueError, TypeError):
                parsed = datetime.fromisoformat(str(creation_time).replace("Z", "+00:00"))
                # Only set if not already set by higher priority source (e.g., exiftool)
                if not desc.creation_timestamp.value:
                    desc.creation_timestamp.value = parsed
                    desc.creation_timestamp.source = "ffprobe"
                    desc.creation_timestamp.raw_value = str(creation_time)
                    desc.creation_date = parsed
