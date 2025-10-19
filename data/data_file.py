"""Data file management for PyEveSettings.

Handles loading and saving data to/from the JSON data file.
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional, List
from datetime import datetime, timezone
from utils import DataFileError, ValidationError
import config


class DataFile:
    """Manages persistent data storage in JSON format.
    
    This class handles all persistent application data including:
    - Character name cache and validation status
    - Account information
    - Character and account notes
    - Window geometry (size/position)
    - User preferences (default sorting, custom EVE paths)
    
    Initialization Flow:
    1. __init__: Sets up file path and empty data structure
    2. load(): Called by application at startup
       - First run: Creates new data structure with defaults (_initialize_new_file)
       - Existing file: Loads JSON (_load_existing_file)
       - Migration: Adds missing fields for backward compatibility (_ensure_data_integrity)
    3. save(): Called when data changes
       - Ensures directory exists
       - Orders data structure consistently
       - Writes JSON to disk
    
    Data Structure:
    {
        'settings': {
            'width': int, 'height': int, 'x_pos': int, 'y_pos': int,
            'default_sorting': str (e.g., 'date_desc'),
            'custom_paths': List[str]
        },
        'character_ids': {
            '<char_id>': {
                'name': str, 'valid': bool, 'checked': ISO datetime, 'note': str
            }
        },
        'account_ids': {
            '<account_id>': {'note': str}
        }
    }
    """
    
    def __init__(self, file_path: Optional[Path] = None):
        """Initialize the DataFile manager.
        
        Args:
            file_path: Path to the JSON data file. If None, uses default location.
        """
        if file_path is None:
            file_path = Path(__file__).parent.parent / config.DATA_FILE_NAME
        self.file_path = Path(file_path)
        self._data: Dict = {}
        
    def load(self) -> Dict:
        """Load all data from the JSON file.
        
        If the file doesn't exist, initializes a new data file with default structure.
        If the file exists but is missing fields, migrates it to the current structure.
        
        Returns:
            Dictionary containing all stored data.
            
        Raises:
            DataFileError: If the file exists but cannot be read or parsed.
        """
        if not self.file_path.exists():
            self._initialize_new_file()
            return self._data
            
        try:
            self._load_existing_file()
            self._ensure_data_integrity()
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
    
    def _initialize_new_file(self) -> None:
        """Initialize a new data file with default structure.
        
        Called when the data file doesn't exist on first run.
        Creates the in-memory data structure but doesn't write to disk yet.
        """
        self._data = self._get_default_structure()
    
    def _load_existing_file(self) -> None:
        """Load data from existing JSON file.
        
        Raises:
            json.JSONDecodeError: If the JSON is invalid.
            PermissionError: If the file cannot be read.
        """
        with self.file_path.open('r', encoding='utf-8') as f:
            self._data = json.load(f)
    
    def _ensure_data_integrity(self) -> None:
        """Ensure loaded data has all required fields.
        
        Migrates old data structures to current format by adding missing fields.
        This allows backward compatibility when new fields are added.
        """
        default = self._get_default_structure()
        
        # Ensure all top-level keys exist
        for key in default:
            if key not in self._data:
                self._data[key] = default[key]
        
        # Ensure app_settings has all required fields
        if 'app_settings' in self._data:
            default_app_settings = default['app_settings']
            for field, default_value in default_app_settings.items():
                if field not in self._data['app_settings']:
                    self._data['app_settings'][field] = default_value
    
    def save(self) -> bool:
        """Save all data to the JSON file.
        
        Ensures the data structure is properly ordered and formatted before writing.
        Creates parent directories if they don't exist.
        
        Returns:
            True if successful.
            
        Raises:
            DataFileError: If the file cannot be written.
        """
        try:
            self._ensure_directory_exists()
            ordered_data = self._prepare_data_for_save()
            self._write_to_file(ordered_data)
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
    
    def _ensure_directory_exists(self) -> None:
        """Ensure the parent directory for the data file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _prepare_data_for_save(self) -> Dict:
        """Prepare data structure for saving.
        
        Orders keys consistently: app_settings, character_ids, account_ids.
        Ensures all required fields exist with defaults if missing.
        
        Returns:
            Ordered dictionary ready for JSON serialization.
        """
        default = self._get_default_structure()
        
        return {
            'app_settings': self._data.get('app_settings', default['app_settings']),
            'character_ids': self._data.get('character_ids', {}),
            'account_ids': self._data.get('account_ids', {})
        }
    
    def _write_to_file(self, data: Dict) -> None:
        """Write data to the JSON file.
        
        Args:
            data: Dictionary to serialize and write.
            
        Raises:
            PermissionError: If file cannot be written.
            OSError: If file operation fails.
        """
        with self.file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
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
            note: Note text (max length defined in config).
            
        Raises:
            ValidationError: If note exceeds maximum length.
        """
        if len(note) > config.MAX_NOTE_LENGTH:
            raise ValidationError(
                f"Character note exceeds maximum length of {config.MAX_NOTE_LENGTH} characters (got {len(note)})"
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
            note: Note text (max length defined in config).
            
        Raises:
            ValidationError: If note exceeds maximum length.
        """
        if len(note) > config.MAX_NOTE_LENGTH:
            raise ValidationError(
                f"Account note exceeds maximum length of {config.MAX_NOTE_LENGTH} characters (got {len(note)})"
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
        default = {
            "width": config.DEFAULT_WINDOW_WIDTH,
            "height": config.DEFAULT_WINDOW_HEIGHT,
            "x_pos": config.DEFAULT_WINDOW_X,
            "y_pos": config.DEFAULT_WINDOW_Y
        }
        return self._data.get('app_settings', default)
    
    def set_window_settings(self, width: int, height: int, x_pos: int, y_pos: int) -> None:
        """Set window position and size.
        
        Only updates the window geometry fields, preserving other app_settings
        like default_sorting and custom_paths.
        
        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            x_pos: X position on screen.
            y_pos: Y position on screen.
        """
        # Update only geometry fields, preserve other settings
        self._data['app_settings']['width'] = width
        self._data['app_settings']['height'] = height
        self._data['app_settings']['x_pos'] = x_pos
        self._data['app_settings']['y_pos'] = y_pos
    
    def get_default_sorting(self) -> str:
        """Get default sorting preference.
        
        Returns:
            Sorting preference string (e.g., 'name_asc', 'id_desc', 'date_asc').
            Defaults to configured default if not set.
        """
        app_settings = self._data.get('app_settings', {})
        return app_settings.get('default_sorting', config.DEFAULT_SORTING)
    
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
        
        self._data['app_settings']['default_sorting'] = sort_preference
    
    def get_custom_paths(self) -> List[str]:
        """Get custom EVE installation paths.
        
        Returns:
            List of custom path strings.
        """
        app_settings = self._data.get('app_settings', {})
        return app_settings.get('custom_paths', [])
    
    def set_custom_paths(self, paths: List[str]) -> None:
        """Set custom EVE installation paths.
        
        Args:
            paths: List of path strings to custom EVE installations.
        """
        self._data['app_settings']['custom_paths'] = paths
    
    def get_sash_positions(self) -> List[int]:
        """Get PanedWindow sash positions.
        
        Returns:
            List of two integers representing sash positions in pixels.
            Defaults to configured defaults if not set.
        """
        app_settings = self._data.get('app_settings', {})
        return app_settings.get('sash_positions', [config.DEFAULT_SASH_0, config.DEFAULT_SASH_1])
    
    def set_sash_positions(self, positions: List[int]) -> None:
        """Set PanedWindow sash positions.
        
        Args:
            positions: List of two integers representing sash positions in pixels.
        """
        if len(positions) != 2:
            raise ValidationError(
                f"Expected 2 sash positions, got {len(positions)}"
            )
        self._data['app_settings']['sash_positions'] = positions
    
    @staticmethod
    def _get_default_structure() -> Dict:
        """Get the default data structure for a fresh installation.
        
        This is the single source of truth for:
        - Default values (window size, sorting preference, etc.)
        - Required fields in the JSON structure
        - Data migration when adding new fields
        
        When adding new fields:
        1. Add them here with appropriate defaults
        2. _ensure_data_integrity() will automatically migrate existing files
        
        Returns:
            Dictionary with default values for all data fields:
            - app_settings: UI state (geometry + preferences)
            - character_ids: Character name cache and metadata
            - account_ids: Account metadata
        """
        return {
            'app_settings': {
                'width': config.DEFAULT_WINDOW_WIDTH,
                'height': config.DEFAULT_WINDOW_HEIGHT,
                'x_pos': config.DEFAULT_WINDOW_X,
                'y_pos': config.DEFAULT_WINDOW_Y,
                'sash_positions': [config.DEFAULT_SASH_0, config.DEFAULT_SASH_1],  # PanedWindow divider positions
                'default_sorting': config.DEFAULT_SORTING,
                'custom_paths': []      # No custom EVE paths by default
            },
            'character_ids': {},        # Empty on first run
            'account_ids': {}           # Empty on first run
        }
