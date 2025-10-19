"""
Utility functions for EVE settings management
"""

from pathlib import Path
from typing import List
import os


def get_eve_base_path() -> Path:
    """Get the base EVE installation path for the current platform"""
    username = os.environ.get('USERNAME') or os.environ.get('USER')
    
    if not username:
        raise ValueError("Could not determine username")
    
    # Windows path
    if os.name == 'nt':
        return Path(f"C:/Users/{username}/AppData/Local/CCP/EVE/c_ccp_eve_tq_tranquility")
    
    # Linux (Wine) path
    else:
        home = Path.home()
        return home / ".eve/wineenv/drive_c/users" / username / "Local Settings/Application Data/CCP/EVE/c_tq_tranquility"


def find_all_settings_folders(base_path: Path) -> List[Path]:
    """Find all settings_* folders in the EVE base path"""
    if not base_path.exists():
        return []
    
    settings_folders = []
    for item in base_path.iterdir():
        if item.is_dir() and item.name.startswith('settings_'):
            settings_folders.append(item)
    
    return sorted(settings_folders)


def validate_settings_folder(folder: Path) -> bool:
    """Validate that a folder contains EVE settings files"""
    if not folder.exists() or not folder.is_dir():
        return False
    
    has_char = False
    has_user = False
    
    for file_path in folder.iterdir():
        if file_path.is_file():
            name = file_path.name
            if name.startswith("core_char_") and not name.startswith("core_char__"):
                has_char = True
            if name.startswith("core_user_") and not name.startswith("core_user__"):
                has_user = True
            
            if has_char and has_user:
                return True
    
    return False
