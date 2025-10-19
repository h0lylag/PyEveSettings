"""Custom exceptions for PyEveSettings.

This module defines all custom exception classes used throughout the application.
All exceptions inherit from PyEveSettingsError for easy catching of all app errors.
"""


class PyEveSettingsError(Exception):
    """Base exception for all PyEveSettings errors.
    
    Catch this to handle any application-specific error.
    """
    pass


class DataFileError(PyEveSettingsError):
    """Raised when there's an error with the data file.
    
    Examples:
        - File is corrupted or contains invalid JSON
        - Unable to read or write the data file
        - Data validation fails
    """
    pass


class ESIError(PyEveSettingsError):
    """Raised when there's an error with the EVE ESI API.
    
    Examples:
        - Network connection failed
        - API returned an error status
        - Request timeout
        - Invalid response format
    """
    pass


class SettingsNotFoundError(PyEveSettingsError):
    """Raised when EVE settings folders cannot be found.
    
    Examples:
        - EVE installation path not found
        - No settings_* folders in EVE directory
        - Custom folder doesn't contain required files
    """
    pass


class InvalidCharacterError(PyEveSettingsError):
    """Raised when a character ID is invalid.
    
    Examples:
        - Character ID doesn't exist in ESI
        - Character was deleted/biomassed
        - Invalid character ID format
    """
    pass


class PlatformNotSupportedError(PyEveSettingsError):
    """Raised when the current platform is not supported.
    
    Examples:
        - Running on macOS (not yet implemented)
        - Unknown/unsupported operating system
    """
    pass


class ValidationError(PyEveSettingsError):
    """Raised when input validation fails.
    
    Examples:
        - Invalid note length
        - Invalid file path
        - Missing required data
    """
    pass
