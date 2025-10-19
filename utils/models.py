"""Data models for EVE settings files."""

from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class CharacterESIResponse:
    """Character information from EVE ESI API."""
    character_id: int
    character_name: str
    alliance_id: Optional[int] = None
    corporation_id: Optional[int] = None
    faction_id: Optional[int] = None


class SettingFile:
    """Represents an EVE settings file (character or account)."""
    
    CHAR_PREFIX = "core_char_"
    USER_PREFIX = "core_user_"
    
    def __init__(self, file_path: Path, api_cache=None):
        """Initialize a settings file.
        
        Args:
            file_path: Path to the settings file.
            api_cache: Optional ESICache instance for character name resolution.
        """
        self.path = file_path
        self.name = file_path.name
        self.api_cache = api_cache
        
        # Extract numeric ID from filename
        extracted_id = int(''.join(filter(str.isdigit, self.name)) or '0')
        # Character IDs must be at least 7 digits and non-zero
        if extracted_id == 0 or extracted_id < 1000000:
            self.id = 0  # Mark as invalid
        else:
            self.id = extracted_id
    
    def __str__(self) -> str:
        """String representation for display in GUI."""
        last_modified = datetime.fromtimestamp(self.path.stat().st_mtime)
        date_str = last_modified.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get folder name for display
        folder_name = self.path.parent.name
        
        if self.is_char_file():
            char_name = self.get_char_name()
            return f"[{folder_name}] {self.id} - {char_name} - Last connection: {date_str}"
        else:
            return f"[{folder_name}] {self.id} - Last connection: {date_str}"
    
    def get_char_name(self) -> str:
        """Get character name from cache.
        
        Returns:
            Character name if cached, "unknown" otherwise.
        """
        if self.api_cache:
            name = self.api_cache.get(self.id)
            return name if name else "unknown"
        return "unknown"
    
    def get_infos(self) -> Optional[CharacterESIResponse]:
        """Get character information from cache.
        
        Returns:
            CharacterESIResponse if cached, None otherwise.
        """
        if self.api_cache:
            name = self.api_cache.get(self.id)
            if name:
                return CharacterESIResponse(
                    character_id=self.id,
                    character_name=name
                )
        return None
    
    def is_char_file(self) -> bool:
        """Check if this is a character settings file.
        
        Returns:
            True if character file, False otherwise.
        """
        return self.name.startswith(self.CHAR_PREFIX) and not self.name.startswith("core_char__")
    
    def is_user_file(self) -> bool:
        """Check if this is an account settings file.
        
        Returns:
            True if account file, False otherwise.
        """
        return self.name.startswith(self.USER_PREFIX) and not self.name.startswith("core_user__")
    
    def last_modified(self) -> datetime:
        """Get last modified time of the file.
        
        Returns:
            datetime of last modification.
        """
        return datetime.fromtimestamp(self.path.stat().st_mtime)
