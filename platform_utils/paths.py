"""Path resolution for EVE Online installation and settings."""

import os
from pathlib import Path
from typing import List, Optional
from .detector import Platform, detect_platform
from exceptions import SettingsNotFoundError, PlatformNotSupportedError


class EVEPathResolver:
    """Resolves paths to EVE Online installation and settings folders."""
    
    def __init__(self):
        """Initialize the path resolver."""
        self.platform = detect_platform()
    
    def get_base_path(self) -> Optional[Path]:
        """Get the EVE base path for settings storage.
        
        Returns:
            Path to EVE settings base directory, or None if not found.
            
        Raises:
            PlatformNotSupportedError: If the current platform is not supported.
        """
        if self.platform == Platform.WINDOWS:
            return self._get_windows_path()
        elif self.platform == Platform.LINUX:
            return self._get_linux_path()
        elif self.platform == Platform.MACOS:
            raise PlatformNotSupportedError(
                "macOS is not yet supported. Please use Windows or Linux."
            )
        else:
            raise PlatformNotSupportedError(
                f"Unknown or unsupported platform: {self.platform}"
            )
    
    def _get_windows_path(self) -> Optional[Path]:
        """Get Windows EVE path.
        
        Returns:
            Path to Windows EVE settings directory, or None if not found.
        """
        username = os.environ.get('USERNAME') or os.environ.get('USER')
        if not username:
            return None
        
        eve_base = Path(f"C:/Users/{username}/AppData/Local/CCP/EVE/c_ccp_eve_tq_tranquility")
        if eve_base.exists():
            return eve_base
        return None
    
    def _get_linux_path(self) -> Optional[Path]:
        """Get Linux Steam EVE path.
        
        Returns:
            Path to Linux Steam EVE settings directory, or None if not found.
        """
        username = os.environ.get('USER')
        if not username:
            return None
        
        # Try Steam Proton path first (most common)
        steam_path = Path(f"/home/{username}/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/AppData/Local/CCP/EVE/c_ccp_eve_tq_tranquility")
        if steam_path.exists():
            return steam_path
        
        # Try Wine path as fallback
        wine_path = Path.home() / ".eve/wineenv/drive_c/users" / username / "Local Settings/Application Data/CCP/EVE/c_tq_tranquility"
        if wine_path.exists():
            return wine_path
        
        return None
    
    def find_settings_folders(self, base_path: Optional[Path] = None) -> List[Path]:
        """Find all settings_* folders in the EVE base path.
        
        Args:
            base_path: Base path to search in. If None, uses get_base_path().
            
        Returns:
            List of Path objects for settings folders, sorted by name.
        """
        if base_path is None:
            base_path = self.get_base_path()
        
        if base_path is None or not base_path.exists():
            return []
        
        settings_folders = []
        try:
            for item in base_path.iterdir():
                if item.is_dir() and item.name.startswith('settings_'):
                    settings_folders.append(item)
        except PermissionError:
            print(f"Warning: Permission denied accessing {base_path}")
            return []
        
        return sorted(settings_folders)
    
    def validate_settings_folder(self, folder: Path) -> bool:
        """Validate that a folder contains required EVE settings files.
        
        A valid settings folder must contain at least one character file
        (core_char_*) and one user file (core_user_*), but not the default
        templates (core_char__ or core_user__).
        
        Args:
            folder: Path to the settings folder to validate.
            
        Returns:
            True if folder contains valid settings files, False otherwise.
        """
        if not folder.exists() or not folder.is_dir():
            return False
        
        has_char = False
        has_user = False
        
        try:
            for file_path in folder.iterdir():
                if file_path.is_file():
                    name = file_path.name
                    if name.startswith("core_char_") and not name.startswith("core_char__"):
                        has_char = True
                    if name.startswith("core_user_") and not name.startswith("core_user__"):
                        has_user = True
                    
                    if has_char and has_user:
                        return True
        except PermissionError:
            return False
        
        return False
