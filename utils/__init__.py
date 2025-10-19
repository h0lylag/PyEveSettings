"""Utils package for py-eve-settings."""

from .core import SettingsManager
from .models import SettingFile, CharacterESIResponse
from .platform_detector import Platform, detect_platform
from .paths import EVEPathResolver
from .backup_manager import BackupManager
from .exceptions import (
    PyEveSettingsError,
    DataFileError,
    ESIError,
    InvalidCharacterError,
    PlatformNotSupportedError,
    ValidationError,
    SettingsNotFoundError,
)

__all__ = [
    'SettingsManager',
    'SettingFile',
    'CharacterESIResponse',
    'Platform',
    'detect_platform',
    'EVEPathResolver',
    'BackupManager',
    'PyEveSettingsError',
    'DataFileError',
    'ESIError',
    'InvalidCharacterError',
    'PlatformNotSupportedError',
    'ValidationError',
    'SettingsNotFoundError',
]
