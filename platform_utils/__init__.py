"""Platform-specific utilities for PyEveSettings."""

from .detector import Platform, detect_platform
from .paths import EVEPathResolver

__all__ = ["Platform", "detect_platform", "EVEPathResolver"]
