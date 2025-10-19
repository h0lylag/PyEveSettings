"""Core business logic for EVE settings management."""

import shutil
from pathlib import Path
from typing import List, Dict, Optional

from .paths import EVEPathResolver
from .models import SettingFile


class SettingsManager:
    """Manages EVE settings files detection and operations."""
    
    def __init__(self, path_resolver: Optional[EVEPathResolver] = None, api_cache=None):
        """Initialize the settings manager.
        
        Args:
            path_resolver: Path resolver instance. If None, creates a new one.
            api_cache: API cache instance for character name resolution.
        """
        self.path_resolver = path_resolver or EVEPathResolver()
        self.api_cache = api_cache
        self.settings_folders: List[Path] = []
        self.char_list: List[SettingFile] = []
        self.user_list: List[SettingFile] = []
        self.file_to_folder: Dict[Path, Path] = {}
    
    def discover_settings_folders(self) -> List[Path]:
        """Discover EVE settings directories.
        
        Checks:
        1. Current directory (if it contains profile files)
        2. Default EVE location with subdirectories (settings_Default, settings_Mining, etc.)
        
        Returns:
            List of paths to settings folders.
        """
        settings_dirs = []
        
        # Check current directory first
        cwd = Path.cwd()
        if self.path_resolver.validate_settings_folder(cwd):
            settings_dirs.append(cwd)
            return settings_dirs  # If current dir has files, use only that
        
        # Check default EVE location
        eve_base = self.path_resolver.get_base_path()
        
        if eve_base and eve_base.exists():
            # Use path resolver to find settings folders
            settings_dirs = self.path_resolver.find_settings_folders(eve_base)
        
        return settings_dirs
    
    def find_settings_directories(self) -> List[Path]:
        """Deprecated: Use discover_settings_folders() instead."""
        return self.discover_settings_folders()
    
    def load_files(self, settings_folders: List[Path]) -> List[int]:
        """Load and sort character and account settings files from all settings directories.
        
        Args:
            settings_folders: List of paths to settings folders to load from.
            
        Returns:
            List of character IDs that need names fetched.
        """
        self.settings_folders = settings_folders
        self.char_list.clear()
        self.user_list.clear()
        self.file_to_folder.clear()
        
        # Collect all character IDs for bulk fetch
        character_ids = []
        
        # Load files from all found settings directories
        for settings_folder in settings_folders:
            for file_path in settings_folder.iterdir():
                if file_path.is_file():
                    setting_file = SettingFile(file_path, api_cache=self.api_cache)
                    
                    if setting_file.is_char_file():
                        # Only add if ID is valid (non-zero and at least 7 digits)
                        if setting_file.id > 0:
                            self.char_list.append(setting_file)
                            self.file_to_folder[setting_file.path] = settings_folder
                            character_ids.append(setting_file.id)
                    elif setting_file.is_user_file():
                        self.user_list.append(setting_file)
                        self.file_to_folder[setting_file.path] = settings_folder
        
        # Sort by last modified (most recent first)
        self.char_list.sort(key=lambda f: f.last_modified(), reverse=True)
        self.user_list.sort(key=lambda f: f.last_modified(), reverse=True)
        
        return character_ids
    
    def copy_settings_to_targets(self, source_file: SettingFile) -> int:
        """Copy settings from source file to all other files of the same type.
        
        Only copies to files in the same settings folder.
        
        Args:
            source_file: The file to use as source for copying.
            
        Returns:
            Number of files copied.
        """
        # Get the appropriate list (char or user)
        file_list = self.char_list if source_file.is_char_file() else self.user_list
        
        # Get the source file's folder
        source_folder = self.file_to_folder.get(source_file.path)
        
        copied_count = 0
        
        # Copy to all other files in the same folder
        for target_file in file_list:
            target_folder = self.file_to_folder.get(target_file.path)
            
            # Only copy within the same settings folder
            if (target_file.path != source_file.path and 
                target_folder == source_folder):
                try:
                    shutil.copy2(source_file.path, target_file.path)
                    folder_name = source_folder.name if source_folder else "unknown"
                    print(f"Copied {source_file.path.name} to {target_file.path.name} in {folder_name}")
                    copied_count += 1
                except Exception as e:
                    print(f"Error copying to {target_file.path.name}: {e}")
                    raise
        
        return copied_count
    
    def copy_settings(self, source_file: SettingFile) -> int:
        """Deprecated: Use copy_settings_to_targets() instead."""
        return self.copy_settings_to_targets(source_file)
