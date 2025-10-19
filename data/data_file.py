"""Data file management for PyEveSettings.

Handles loading and saving data to/from the JSON data file.
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional, List
from datetime import datetime, timezone
from utils import DataFileError, ValidationError


class DataFile:
    """Manages persistent data storage in JSON format.
    
    Handles character name cache, invalid IDs, notes, and window settings.
    """
    
    def __init__(self, file_path: Optional[Path] = None):
        """Initialize the DataFile manager.
        
        Args:
            file_path: Path to the JSON data file. If None, uses default location.
        """
        if file_path is None:
            file_path = Path(__file__).parent.parent / "pyevesettings_data.json"
        self.file_path = Path(file_path)
        self._data: Dict = {}
        
    def load(self) -> Dict:
        """Load all data from the JSON file.
        
        Returns:
            Dictionary containing all stored data.
            Returns empty dict with default structure if file doesn't exist.
            
        Raises:
            DataFileError: If the file exists but cannot be read or parsed.
        """
        if not self.file_path.exists():
            self._data = self._get_default_structure()
            return self._data
            
        try:
            with self.file_path.open('r', encoding='utf-8') as f:
                self._data = json.load(f)
            # Ensure all required keys exist
            default = self._get_default_structure()
            for key in default:
                if key not in self._data:
                    self._data[key] = default[key]
            return self._data
        except json.JSONDecodeError as e:
            raise DataFileError(
                f"Data file is corrupted or contains invalid JSON: {e}"
            ) from e
        except PermissionError as e:
            raise DataFileError(
                f"Permission denied reading data file '{self.file_path}': {e}"
            ) from e
        except Exception as e:
            raise DataFileError(
                f"Unexpected error loading data file '{self.file_path}': {e}"
            ) from e
    
    def save(self) -> bool:
        """Save all data to the JSON file.
        
        Returns:
            True if successful.
            
        Raises:
            DataFileError: If the file cannot be written.
        """
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create ordered data structure with window_settings first
            ordered_data = {
                'window_settings': self._data.get('window_settings', {
                    'width': 800,
                    'height': 600,
                    'x_pos': 0,
                    'y_pos': 0
                }),
                'character_ids': self._data.get('character_ids', {}),
                'account_ids': self._data.get('account_ids', {})
            }
            
            with self.file_path.open('w', encoding='utf-8') as f:
                json.dump(ordered_data, f, indent=2)
            return True
        except PermissionError as e:
            raise DataFileError(
                f"Permission denied writing to '{self.file_path}': {e}"
            ) from e
        except OSError as e:
            raise DataFileError(
                f"Failed to create directory or write file '{self.file_path}': {e}"
            ) from e
        except Exception as e:
            raise DataFileError(
                f"Unexpected error saving data file '{self.file_path}': {e}"
            ) from e
    
    def get_character_names(self) -> Dict[str, str]:
        """Get cached character ID to name mappings.
        
        Returns:
            Dictionary mapping character IDs (as strings) to character names.
            Only returns valid characters with names.
        """
        char_data = self._data.get('character_ids', {})
        result = {}
        
        for char_id, value in char_data.items():
            if isinstance(value, dict) and value.get('valid', True):
                name = value.get('name', '')
                if name:
                    result[char_id] = name
        
        return result
    
    def save_character_name(self, char_id: str, name: str, valid: bool = True) -> None:
        """Save a character ID with full metadata.
        
        Args:
            char_id: Character ID as string.
            name: Character name.
            valid: Whether the character ID is valid (default True).
        """
        if 'character_ids' not in self._data:
            self._data['character_ids'] = {}
        
        char_id_str = str(char_id)
        
        # Preserve existing note if present, otherwise empty string
        existing_note = ""
        if char_id_str in self._data['character_ids']:
            existing = self._data['character_ids'][char_id_str]
            if isinstance(existing, dict):
                existing_note = existing.get('note', '')
        
        # Save with full structure
        self._data['character_ids'][char_id_str] = {
            'name': name,
            'valid': valid,
            'checked': datetime.now(timezone.utc).isoformat(),
            'note': existing_note
        }
    
    def get_invalid_ids(self) -> Set[str]:
        """Get set of invalid character IDs.
        
        Returns:
            Set of character IDs marked as invalid.
        """
        invalid = set()
        char_data = self._data.get('character_ids', {})
        
        for char_id, value in char_data.items():
            if isinstance(value, dict) and not value.get('valid', True):
                invalid.add(str(char_id))
        
        return invalid
    
    def add_invalid_id(self, char_id: str) -> None:
        """Mark a character ID as invalid.
        
        Args:
            char_id: Character ID to mark as invalid.
        """
        char_id_str = str(char_id)
        
        if 'character_ids' not in self._data:
            self._data['character_ids'] = {}
        
        # Preserve existing note if present
        existing_note = ""
        if char_id_str in self._data['character_ids']:
            existing = self._data['character_ids'][char_id_str]
            if isinstance(existing, dict):
                existing_note = existing.get('note', '')
        
        self._data['character_ids'][char_id_str] = {
            'name': '',
            'valid': False,
            'checked': datetime.now(timezone.utc).isoformat(),
            'note': existing_note
        }
    
    def get_character_notes(self) -> Dict[str, str]:
        """Get all character notes.
        
        Returns:
            Dictionary mapping character IDs to notes.
        """
        notes = {}
        char_data = self._data.get('character_ids', {})
        
        for char_id, value in char_data.items():
            if isinstance(value, dict):
                note = value.get('note', '')
                if note:  # Only include non-empty notes
                    notes[char_id] = note
        
        return notes
    
    def get_account_notes(self) -> Dict[str, str]:
        """Get all account notes.
        
        Returns:
            Dictionary mapping account IDs to notes.
        """
        notes = {}
        account_data = self._data.get('account_ids', {})
        
        for account_id, value in account_data.items():
            if isinstance(value, dict):
                note = value.get('note', '')
                if note:  # Only include non-empty notes
                    notes[account_id] = note
        
        return notes
    
    def set_character_note(self, char_id: str, note: str) -> None:
        """Set a note for a character.
        
        Args:
            char_id: Character ID.
            note: Note text (max 100 characters).
            
        Raises:
            ValidationError: If note exceeds maximum length.
        """
        if len(note) > 100:
            raise ValidationError(
                f"Character note exceeds maximum length of 100 characters (got {len(note)})"
            )
        
        char_id_str = str(char_id)
        
        if 'character_ids' not in self._data:
            self._data['character_ids'] = {}
        
        if char_id_str in self._data['character_ids']:
            # Update existing entry
            existing = self._data['character_ids'][char_id_str]
            if isinstance(existing, dict):
                existing['note'] = note
            else:
                # Should not happen in single-format version, but handle it
                self._data['character_ids'][char_id_str] = {
                    'name': '',
                    'valid': True,
                    'checked': datetime.now(timezone.utc).isoformat(),
                    'note': note
                }
        else:
            # Create new entry with note
            self._data['character_ids'][char_id_str] = {
                'name': '',
                'valid': True,
                'checked': datetime.now(timezone.utc).isoformat(),
                'note': note
            }
    
    def set_account_note(self, account_id: str, note: str) -> None:
        """Set a note for an account.
        
        Args:
            account_id: Account ID.
            note: Note text (max 100 characters).
            
        Raises:
            ValidationError: If note exceeds maximum length.
        """
        if len(note) > 100:
            raise ValidationError(
                f"Account note exceeds maximum length of 100 characters (got {len(note)})"
            )
        
        account_id_str = str(account_id)
        
        if 'account_ids' not in self._data:
            self._data['account_ids'] = {}
        
        if account_id_str in self._data['account_ids']:
            # Update existing entry
            existing = self._data['account_ids'][account_id_str]
            if isinstance(existing, dict):
                existing['note'] = note
            else:
                # Should not happen in single-format version, but handle it
                self._data['account_ids'][account_id_str] = {
                    'note': note
                }
        else:
            # Create new entry with note
            self._data['account_ids'][account_id_str] = {
                'note': note
            }
    
    def get_character_checked_time(self, char_id: str) -> Optional[str]:
        """Get the last ESI check timestamp for a character.
        
        Args:
            char_id: Character ID.
            
        Returns:
            ISO format timestamp string (UTC timezone aware) or None if not found.
        """
        char_data = self._data.get('character_ids', {})
        char_id_str = str(char_id)
        
        if char_id_str in char_data:
            value = char_data[char_id_str]
            if isinstance(value, dict):
                return value.get('checked')
        
        return None
    
    def is_character_valid(self, char_id: str) -> bool:
        """Check if a character ID is marked as valid.
        
        Args:
            char_id: Character ID.
            
        Returns:
            True if valid or unknown, False if marked invalid.
        """
        char_data = self._data.get('character_ids', {})
        char_id_str = str(char_id)
        
        if char_id_str in char_data:
            value = char_data[char_id_str]
            if isinstance(value, dict):
                return value.get('valid', True)
        
        return True
    
    def get_window_settings(self) -> Dict[str, int]:
        """Get window settings.
        
        Returns:
            Dictionary with width, height, x_pos, y_pos keys.
        """
        default = {"width": 800, "height": 600, "x_pos": 0, "y_pos": 0}
        return self._data.get('window_settings', default)
    
    def set_window_settings(self, width: int, height: int, x_pos: int, y_pos: int) -> None:
        """Set window settings.
        
        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x_pos: X position on screen.
            y_pos: Y position on screen.
        """
        self._data['window_settings'] = {
            'width': width,
            'height': height,
            'x_pos': x_pos,
            'y_pos': y_pos
        }
    
    def get_default_sorting(self) -> str:
        """Get default sorting preference.
        
        Returns:
            Sorting preference string (e.g., 'name_asc', 'id_desc', 'date_asc').
            Defaults to 'date_desc' if not set.
        """
        window_settings = self._data.get('window_settings', {})
        return window_settings.get('default_sorting', 'date_desc')
    
    def set_default_sorting(self, sort_preference: str) -> None:
        """Set default sorting preference.
        
        Args:
            sort_preference: Sorting preference string (e.g., 'name_asc', 'id_desc', 'date_asc').
        """
        valid_options = ['name_asc', 'name_desc', 'id_asc', 'id_desc', 'date_asc', 'date_desc']
        if sort_preference not in valid_options:
            raise ValidationError(
                f"Invalid sort preference '{sort_preference}'. Must be one of: {', '.join(valid_options)}"
            )
        
        # Ensure window_settings exists
        if 'window_settings' not in self._data:
            self._data['window_settings'] = {
                'width': 800,
                'height': 600,
                'x_pos': 0,
                'y_pos': 0,
                'default_sorting': 'date_desc'
            }
        
        self._data['window_settings']['default_sorting'] = sort_preference
    
    def get_custom_paths(self) -> List[str]:
        """Get custom EVE installation paths.
        
        Returns:
            List of custom path strings.
        """
        window_settings = self._data.get('window_settings', {})
        return window_settings.get('custom_paths', [])
    
    def set_custom_paths(self, paths: List[str]) -> None:
        """Set custom EVE installation paths.
        
        Args:
            paths: List of path strings to custom EVE installations.
        """
        # Ensure window_settings exists
        if 'window_settings' not in self._data:
            self._data['window_settings'] = {
                'width': 800,
                'height': 600,
                'x_pos': 0,
                'y_pos': 0,
                'default_sorting': 'name_asc'
            }
        
        self._data['window_settings']['custom_paths'] = paths
    
    @staticmethod
    def _get_default_structure() -> Dict:
        """Get the default data structure.
        
        Returns:
            Dictionary with default empty values for all data fields.
        """
        return {
            'window_settings': {
                'width': 800,
                'height': 600,
                'x_pos': 0,
                'y_pos': 0,
                'default_sorting': 'date_desc',
                'custom_paths': []
            },
            'character_ids': {},
            'account_ids': {}
        }
