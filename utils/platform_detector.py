"""Platform detection for PyEveSettings."""

import platform
from enum import Enum
from .exceptions import PlatformNotSupportedError


class Platform(Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


def detect_platform() -> Platform:
    """Detect the current operating system platform.
    
    Returns:
        Platform enum value.
    """
    system = platform.system().lower()
    
    if system == "windows":
        return Platform.WINDOWS
    elif system == "linux":
        return Platform.LINUX
    elif system == "darwin":
        return Platform.MACOS
    else:
        return Platform.UNKNOWN
