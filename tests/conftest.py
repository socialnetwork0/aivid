"""Pytest configuration and fixtures."""

import subprocess

import pytest


def command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def has_ffprobe() -> bool:
    """Check if ffprobe is available."""
    return command_exists("ffprobe")


@pytest.fixture
def has_mediainfo() -> bool:
    """Check if mediainfo is available."""
    return command_exists("mediainfo")


@pytest.fixture
def has_exiftool() -> bool:
    """Check if exiftool is available."""
    return command_exists("exiftool")
