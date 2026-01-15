"""Configuration management for aivid.

Supports loading configuration from:
1. Environment variables (AIVID_*)
2. Config file (~/.aivid/config.yaml)
3. Default values

Example config file (~/.aivid/config.yaml):
    api_keys:
      youtube_api_key: "YOUR_API_KEY"
      tiktok_client_key: "YOUR_CLIENT_KEY"
      tiktok_client_secret: "YOUR_SECRET"
    download:
      temp_dir: "/tmp/aivid"
      keep_downloads: false
    detection:
      enable_watermark: true
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Config file search locations (in priority order)
CONFIG_LOCATIONS = [
    Path.home() / ".aivid" / "config.yaml",
    Path.home() / ".config" / "aivid" / "config.yaml",
    Path(".aivid.yaml"),
]


@dataclass
class APIKeysConfig:
    """API key configuration."""

    youtube_api_key: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None


@dataclass
class DownloadConfig:
    """Download configuration."""

    temp_dir: str | None = None
    keep_downloads: bool = False
    max_file_size_mb: int = 500
    timeout_seconds: int = 300


@dataclass
class DetectionConfig:
    """Detection configuration."""

    enable_watermark: bool = True
    audioseal_threshold: float = 0.5
    videoseal_threshold: float = 0.5


@dataclass
class AividConfig:
    """Main configuration for aivid."""

    api_keys: APIKeysConfig = field(default_factory=APIKeysConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)


def _load_yaml_config() -> dict[str, Any]:
    """Load configuration from YAML file if available."""
    try:
        import yaml
    except ImportError:
        return {}

    for config_path in CONFIG_LOCATIONS:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                    return data if data else {}
            except Exception:
                continue
    return {}


def _get_env(key: str, default: Any = None) -> Any:
    """Get environment variable with AIVID_ prefix."""
    return os.environ.get(f"AIVID_{key}", default)


def _parse_bool(value: str | None) -> bool | None:
    """Parse boolean from string."""
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes", "on")


def load_config() -> AividConfig:
    """Load configuration from file and environment variables.

    Priority (highest first):
    1. Environment variables (AIVID_*)
    2. Config file (~/.aivid/config.yaml)
    3. Default values
    """
    file_config = _load_yaml_config()

    # API Keys
    api_keys_config = file_config.get("api_keys", {})
    api_keys = APIKeysConfig(
        youtube_api_key=_get_env("YOUTUBE_API_KEY") or api_keys_config.get("youtube_api_key"),
        tiktok_client_key=_get_env("TIKTOK_CLIENT_KEY") or api_keys_config.get("tiktok_client_key"),
        tiktok_client_secret=_get_env("TIKTOK_CLIENT_SECRET")
        or api_keys_config.get("tiktok_client_secret"),
    )

    # Download config
    download_config = file_config.get("download", {})
    download = DownloadConfig(
        temp_dir=_get_env("DOWNLOAD_TEMP_DIR") or download_config.get("temp_dir"),
        keep_downloads=_parse_bool(_get_env("DOWNLOAD_KEEP"))
        or download_config.get("keep_downloads", False),
        max_file_size_mb=int(
            _get_env("DOWNLOAD_MAX_SIZE") or download_config.get("max_file_size_mb", 500)
        ),
        timeout_seconds=int(
            _get_env("DOWNLOAD_TIMEOUT") or download_config.get("timeout_seconds", 300)
        ),
    )

    # Detection config
    detection_config = file_config.get("detection", {})
    detection = DetectionConfig(
        enable_watermark=(
            _parse_bool(_get_env("ENABLE_WATERMARK"))
            if _get_env("ENABLE_WATERMARK")
            else detection_config.get("enable_watermark", True)
        ),
        audioseal_threshold=float(
            _get_env("AUDIOSEAL_THRESHOLD") or detection_config.get("audioseal_threshold", 0.5)
        ),
        videoseal_threshold=float(
            _get_env("VIDEOSEAL_THRESHOLD") or detection_config.get("videoseal_threshold", 0.5)
        ),
    )

    return AividConfig(
        api_keys=api_keys,
        download=download,
        detection=detection,
    )


# Global config instance (lazy loaded)
_config: AividConfig | None = None


def get_config() -> AividConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset the global configuration (for testing)."""
    global _config
    _config = None
