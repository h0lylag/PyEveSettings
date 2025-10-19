"""Notes management for PyEveSettings."""

from typing import Dict, Optional


class NotesManager:
    """Manages character and account notes."""
    
    def __init__(self):
        """Initialize the notes manager."""
        self._character_notes: Dict[str, str] = {}
        self._account_notes: Dict[str, str] = {}
    
    def load_from_dict(self, character_notes: Dict[str, str], 
                       account_notes: Dict[str, str]) -> None:
        """Load notes from dictionaries.
        
        Args:
            character_notes: Dictionary of character ID -> note mappings.
            account_notes: Dictionary of account ID -> note mappings.
        """
        self._character_notes = character_notes.copy()
        self._account_notes = account_notes.copy()
    
    def get_character_note(self, char_id: str) -> str:
        """Get note for a character.
        
        Args:
            char_id: Character ID.
            
        Returns:
            Note text, or empty string if no note exists.
        """
        return self._character_notes.get(str(char_id), "")
    
    def set_character_note(self, char_id: str, note: str) -> None:
        """Set note for a character.
        
        Args:
            char_id: Character ID.
            note: Note text.
        """
        self._character_notes[str(char_id)] = note
    
    def get_account_note(self, account_id: str) -> str:
        """Get note for an account.
        
        Args:
            account_id: Account ID.
            
        Returns:
            Note text, or empty string if no note exists.
        """
        return self._account_notes.get(str(account_id), "")
    
    def set_account_note(self, account_id: str, note: str) -> None:
        """Set note for an account.
        
        Args:
            account_id: Account ID.
            note: Note text.
        """
        self._account_notes[str(account_id)] = note
    
    def get_all_character_notes(self) -> Dict[str, str]:
        """Get all character notes.
        
        Returns:
            Dictionary of character ID -> note mappings.
        """
        return self._character_notes.copy()
    
    def get_all_account_notes(self) -> Dict[str, str]:
        """Get all account notes.
        
        Returns:
            Dictionary of account ID -> note mappings.
        """
        return self._account_notes.copy()
