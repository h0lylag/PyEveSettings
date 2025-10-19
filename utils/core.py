"""
Core business logic for EVE settings management
"""

import os
import shutil
import platform
from pathlib import Path
from typing import List, Dict, Optional
from .models import SettingFile


def get_operating_system() -> str:
    """
    Determine the current operating system
    
    Returns:
        'windows' or 'linux'
    """
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        # Default to linux for other Unix-like systems
        return 'linux'


def get_eve_base_path() -> Optional[Path]:
    """
    Get the EVE base path based on the operating system
    
    Returns:
        Path to EVE base directory or None if not found
    """
    os_type = get_operating_system()
    
    if os_type == 'windows':
        # Windows default path
        username = os.environ.get('USERNAME') or os.environ.get('USER')
        if username:
            eve_base = Path(f"C:/Users/{username}/AppData/Local/CCP/EVE/c_ccp_eve_tq_tranquility")
            if eve_base.exists():
                return eve_base
    
    elif os_type == 'linux':
        # Linux Steam path
        username = os.environ.get('USER')
        if username:
            eve_base = Path(f"/home/{username}/.steam/steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/AppData/Local/CCP/EVE/c_ccp_eve_tq_tranquility")
            if eve_base.exists():
                return eve_base
    
    return None


class SettingsManager:
    """Manages EVE settings files detection and operations"""
    
    def __init__(self):
        self.settings_folders: List[Path] = []
        self.char_list: List[SettingFile] = []
        self.user_list: List[SettingFile] = []
        self.file_to_folder: Dict[Path, Path] = {}
    
    def find_settings_directories(self) -> List[Path]:
        """
        Find EVE settings directories
        Checks:
        1. Current directory (if it contains profile files)
        2. Default EVE location (OS-specific) with subdirectories (settings_Default, settings_Mining, etc.)
        """
        settings_dirs = []
        
        # Check current directory first
        cwd = Path.cwd()
        if self.has_settings_files(cwd):
            settings_dirs.append(cwd)
            return settings_dirs  # If current dir has files, use only that
        
        # Check default EVE location using OS-specific path
        eve_base = get_eve_base_path()
        
        if eve_base and eve_base.exists():
            # Look for settings_* subdirectories
            for subdir in eve_base.iterdir():
                if subdir.is_dir() and subdir.name.startswith('settings_'):
                    if self.has_settings_files(subdir):
                        settings_dirs.append(subdir)
        
        return settings_dirs
    
    def has_settings_files(self, directory: Path) -> bool:
        """Check if a directory contains EVE settings files"""
        if not directory.exists() or not directory.is_dir():
            return False
        
        has_char = False
        has_user = False
        
        for file_path in directory.iterdir():
            if file_path.is_file():
                name = file_path.name
                if name.startswith("core_char_") and not name.startswith("core_char__"):
                    has_char = True
                if name.startswith("core_user_") and not name.startswith("core_user__"):
                    has_user = True
                
                if has_char and has_user:
                    return True
        
        return False
    
    def load_files(self, settings_folders: List[Path]) -> None:
        """Load and sort character and account settings files from all settings directories"""
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
                    setting_file = SettingFile(file_path)
                    
                    if setting_file.is_char_file():
                        # Only add if ID is valid (non-zero and at least 7 digits)
                        if setting_file.id > 0:
                            self.char_list.append(setting_file)
                            self.file_to_folder[setting_file.path] = settings_folder
                            character_ids.append(setting_file.id)
                    elif setting_file.is_user_file():
                        self.user_list.append(setting_file)
                        self.file_to_folder[setting_file.path] = settings_folder
        
        # Fetch all character names in bulk (much more efficient!)
        if character_ids:
            SettingFile.fetch_character_names_bulk(character_ids)
        
        # Sort by last modified (most recent first)
        self.char_list.sort(key=lambda f: f.last_modified(), reverse=True)
        self.user_list.sort(key=lambda f: f.last_modified(), reverse=True)
    
    def copy_settings(self, source_file: SettingFile) -> int:
        """
        Copy settings from source file to all other files of the same type
        Only copies to files in the same settings folder
        
        Args:
            source_file: The file to use as source for copying
            
        Returns:
            Number of files copied
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
