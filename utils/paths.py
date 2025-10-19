"""Path resolution for EVE Online installation and settings."""

import os
from pathlib import Path
from typing import List, Optional, Dict
from .platform_detector import Platform, detect_platform
from .exceptions import SettingsNotFoundError, PlatformNotSupportedError


class EVEPathResolver:
    """Resolves paths to EVE Online installation and settings folders."""
    
    def __init__(self, server: Optional[str] = None, custom_paths: Optional[List[str]] = None):
        """Initialize the path resolver.
        
        Args:
            server: Server name (e.g., 'tranquility', 'singularity'). If None, defaults to tranquility.
            custom_paths: Optional list of custom EVE installation paths to check.
        """
        self.platform = detect_platform()
        self.server = server or 'tranquility'
        self.custom_paths = [Path(p) for p in (custom_paths or [])]
    
    def discover_servers(self) -> Dict[str, str]:
        """Discover all available EVE servers.
        
        Returns:
            Dictionary mapping display names to server folder names.
            Example: {'Tranquility': 'c_ccp_eve_tq_tranquility', 'Singularity': 'c_ccp_eve_sisi_singularity'}
        """
        servers = {}
        
        # Check default base directory
        base_dir = self._get_eve_base_directory()
        if base_dir and base_dir.exists():
            self._scan_for_servers(base_dir, servers)
        
        # Check custom paths
        for custom_path in self.custom_paths:
            if custom_path.exists():
                self._scan_for_servers(custom_path, servers)
        
        return servers
    
    def _scan_for_servers(self, base_dir: Path, servers: Dict[str, str]) -> None:
        """Scan a directory for EVE server folders.
        
        Args:
            base_dir: Directory to scan.
            servers: Dictionary to add found servers to.
        """
        try:
            for item in base_dir.iterdir():
                if item.is_dir() and item.name.startswith('c_ccp_eve_'):
                    # Extract server name from folder (e.g., c_ccp_eve_tq_tranquility -> tranquility)
                    parts = item.name.split('_')
                    if len(parts) >= 4:
                        # Get the last part as the server name
                        server_name = parts[-1]
                        # Capitalize for display
                        display_name = server_name.capitalize()
                        # Store full path as value instead of just folder name
                        servers[display_name] = str(item)
        except PermissionError:
            print(f"Warning: Permission denied accessing {base_dir}")
    
    def _get_eve_base_directory(self) -> Optional[Path]:
        """Get the base EVE directory containing server folders.
        
        Returns:
            Path to EVE base directory (one level above server folders), or None if not found.
        """
        if self.platform == Platform.WINDOWS:
            username = os.environ.get('USERNAME') or os.environ.get('USER')
            if not username:
                return None
            return Path(f"C:/Users/{username}/AppData/Local/CCP/EVE")
        
        elif self.platform == Platform.LINUX:
            username = os.environ.get('USER')
            if not username:
                return None
            
            # Try Steam Proton path first (most common)
            steam_path = Path(f"/home/{username}/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/AppData/Local/CCP/EVE")
            if steam_path.exists():
                return steam_path
            
            # Try Wine path as fallback
            wine_path = Path.home() / ".eve/wineenv/drive_c/users" / username / "Local Settings/Application Data/CCP/EVE"
            if wine_path.exists():
                return wine_path
        
        return None
    
    def get_server_folder_name(self, server: Optional[str] = None) -> str:
        """Get the folder name for a specific server.
        
        Args:
            server: Server name (e.g., 'tranquility', 'singularity'). If None, uses self.server.
            
        Returns:
            Folder name for the server (e.g., 'c_ccp_eve_tq_tranquility').
        """
        server_name = (server or self.server).lower()
        
        # Try to find the exact folder name from discovered servers
        servers = self.discover_servers()
        for display_name, folder_name in servers.items():
            if display_name.lower() == server_name:
                return folder_name
        
        # Fallback to constructed name
        # Map common server names to their abbreviations
        server_map = {
            'tranquility': 'tq_tranquility',
            'singularity': 'sisi_singularity',
            'duality': 'duality',
            'serenity': 'serenity'
        }
        
        server_suffix = server_map.get(server_name, server_name)
        return f'c_ccp_eve_{server_suffix}'
    
    def get_base_path(self, server: Optional[str] = None) -> Optional[Path]:
        """Get the EVE base path for settings storage for a specific server.
        
        Args:
            server: Server name (e.g., 'tranquility', 'singularity'). If None, uses self.server.
        
        Returns:
            Path to EVE settings base directory for the server, or None if not found.
            
        Raises:
            PlatformNotSupportedError: If the current platform is not supported.
        """
        # First check if server folder is from custom paths (will be full path)
        servers = self.discover_servers()
        server_key = (server or self.server).capitalize()
        if server_key in servers:
            server_path_str = servers[server_key]
            # If it's a full path (from custom paths), return it
            if '/' in server_path_str or '\\' in server_path_str:
                return Path(server_path_str)
        
        # Otherwise use platform-specific logic
        if self.platform == Platform.WINDOWS:
            return self._get_windows_path(server)
        elif self.platform == Platform.LINUX:
            return self._get_linux_path(server)
        elif self.platform == Platform.MACOS:
            raise PlatformNotSupportedError(
                "macOS is not yet supported. Please use Windows or Linux."
            )
        else:
            raise PlatformNotSupportedError(
                f"Unknown or unsupported platform: {self.platform}"
            )
    
    def _get_windows_path(self, server: Optional[str] = None) -> Optional[Path]:
        """Get Windows EVE path for a specific server.
        
        Args:
            server: Server name. If None, uses self.server.
        
        Returns:
            Path to Windows EVE settings directory, or None if not found.
        """
        username = os.environ.get('USERNAME') or os.environ.get('USER')
        if not username:
            return None
        
        server_folder = self.get_server_folder_name(server)
        eve_base = Path(f"C:/Users/{username}/AppData/Local/CCP/EVE/{server_folder}")
        if eve_base.exists():
            return eve_base
        return None
    
    def _get_linux_path(self, server: Optional[str] = None) -> Optional[Path]:
        """Get Linux Steam EVE path for a specific server.
        
        Args:
            server: Server name. If None, uses self.server.
        
        Returns:
            Path to Linux Steam EVE settings directory, or None if not found.
        """
        username = os.environ.get('USER')
        if not username:
            return None
        
        server_folder = self.get_server_folder_name(server)
        
        # Try Steam Proton path first (most common)
        steam_path = Path(f"/home/{username}/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/AppData/Local/CCP/EVE/{server_folder}")
        if steam_path.exists():
            return steam_path
        
        # Try Wine path as fallback
        wine_path = Path.home() / ".eve/wineenv/drive_c/users" / username / "Local Settings/Application Data/CCP/EVE" / server_folder
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
