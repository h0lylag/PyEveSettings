"""
Data models for EVE settings files
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import requests
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os


@dataclass
class CharacterESIResponse:
    """Character information from EVE ESI API"""
    character_id: int
    character_name: str
    alliance_id: Optional[int] = None
    corporation_id: Optional[int] = None
    faction_id: Optional[int] = None


# Global cache for character names (populated via API calls)
_CHARACTER_NAME_CACHE: Dict[int, str] = {}

# Set of invalid character IDs (404s from API)
_INVALID_CHARACTER_IDS: set = set()

# Cache file path
_CACHE_FILE = Path(__file__).parent.parent / "chars.json"


class SettingFile:
    """Represents an EVE settings file (character or account)"""
    
    CHAR_PREFIX = "core_char_"
    USER_PREFIX = "core_user_"
    
    def __init__(self, file_path: Path):
        self.path = file_path
        self.name = file_path.name
        # Extract numeric ID from filename
        extracted_id = int(''.join(filter(str.isdigit, self.name)) or '0')
        # Character IDs must be at least 7 digits and non-zero
        if extracted_id == 0 or extracted_id < 1000000:
            self.id = 0  # Mark as invalid
        else:
            self.id = extracted_id
        self._esi_response: Optional[CharacterESIResponse] = None
    
    def __str__(self) -> str:
        """String representation for display in GUI"""
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
        """Get character name from cache or return unknown"""
        return _CHARACTER_NAME_CACHE.get(self.id, "unknown")
    
    def get_infos(self) -> Optional[CharacterESIResponse]:
        """Get character information from cache"""
        if self.id in _CHARACTER_NAME_CACHE:
            return CharacterESIResponse(
                character_id=self.id,
                character_name=_CHARACTER_NAME_CACHE[self.id]
            )
        return None
    
    @staticmethod
    def load_cache() -> Dict[int, str]:
        """Load character names and invalid IDs from cache file"""
        global _INVALID_CHARACTER_IDS
        
        if _CACHE_FILE.exists():
            try:
                with open(_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Load valid character names
                    names = {}
                    if 'characters' in data:
                        names = {int(k): v for k, v in data['characters'].items()}
                    else:
                        # Old format - just a dict of IDs to names
                        names = {int(k): v for k, v in data.items() if k != 'invalid_ids'}
                    
                    # Load invalid IDs
                    if 'invalid_ids' in data:
                        _INVALID_CHARACTER_IDS = set(data['invalid_ids'])
                    
                    return names
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
        return {}
    
    @staticmethod
    def save_cache(cache: Dict[int, str]) -> None:
        """Save character names and invalid IDs to cache file"""
        try:
            with open(_CACHE_FILE, 'w') as f:
                data = {
                    'characters': {str(k): v for k, v in cache.items()},
                    'invalid_ids': list(_INVALID_CHARACTER_IDS)
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    @staticmethod
    def fetch_single_character(char_id: int, max_retries: int = 3) -> Optional[str]:
        """
        Fetch a single character name from ESI API with retry logic
        
        Args:
            char_id: Character ID to fetch
            max_retries: Maximum number of retries for timeouts
            
        Returns:
            Character name or None if failed
        """
        global _INVALID_CHARACTER_IDS
        
        url = f"https://esi.evetech.net/latest/characters/{char_id}/"
        headers = {'Accept': 'application/json'}
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('name')
                elif response.status_code == 404:
                    # Invalid character ID - don't retry and mark as invalid
                    print(f"  Character {char_id} not found (invalid ID)")
                    _INVALID_CHARACTER_IDS.add(char_id)
                    return None
                elif response.status_code >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        print(f"  Server error for {char_id}, retrying...")
                        continue
                    return None
                else:
                    # Other error - don't retry
                    print(f"  Error {response.status_code} for character {char_id}")
                    return None
                    
            except requests.exceptions.Timeout:
                # Timeout - retry
                if attempt < max_retries - 1:
                    print(f"  Timeout for character {char_id}, retrying (attempt {attempt + 2}/{max_retries})...")
                    continue
                else:
                    print(f"  Timeout for character {char_id} after {max_retries} attempts")
                    return None
                    
            except requests.exceptions.ConnectionError:
                # Connection error - retry
                if attempt < max_retries - 1:
                    print(f"  Connection error for {char_id}, retrying...")
                    continue
                else:
                    print(f"  Connection error for character {char_id} after {max_retries} attempts")
                    return None
                    
            except Exception as e:
                # Unknown error - don't retry
                print(f"  Unexpected error for character {char_id}: {e}")
                return None
        
        return None
    
    @staticmethod
    def fetch_character_names_bulk(character_ids: List[int]) -> Dict[int, str]:
        """
        Fetch character names using individual async requests with caching
        
        Args:
            character_ids: List of character IDs to fetch
            
        Returns:
            Dictionary mapping character ID to character name
        """
        if not character_ids:
            return {}
        
        # Deduplicate character IDs
        unique_ids = list(set(character_ids))
        
        if not unique_ids:
            return {}
        
        # Load cache
        cache = SettingFile.load_cache()
        _CHARACTER_NAME_CACHE.update(cache)
        
        # Find IDs we need to fetch (skip cached and invalid IDs)
        ids_to_fetch = [cid for cid in unique_ids 
                       if cid not in cache and cid not in _INVALID_CHARACTER_IDS]
        
        # Count how many we're skipping
        cached_count = len([cid for cid in unique_ids if cid in cache])
        invalid_count = len([cid for cid in unique_ids if cid in _INVALID_CHARACTER_IDS])
        
        if not ids_to_fetch:
            if invalid_count > 0:
                print(f"All {len(unique_ids)} character names loaded from cache ({invalid_count} known invalid).")
            else:
                print(f"All {len(unique_ids)} character names loaded from cache.")
            return cache
        
        print(f"Fetching {len(ids_to_fetch)} character names (async)...")
        if cached_count > 0:
            print(f"Using cache for {cached_count} characters.")
        if invalid_count > 0:
            print(f"Skipping {invalid_count} known invalid IDs.")
        
        # Fetch missing names using thread pool for async requests
        names = {}
        failed_ids = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {executor.submit(SettingFile.fetch_single_character, cid): cid 
                           for cid in ids_to_fetch}
            
            completed = 0
            for future in future_to_id:
                char_id = future_to_id[future]
                try:
                    name = future.result()
                    if name:
                        names[char_id] = name
                        completed += 1
                        if completed % 10 == 0:
                            print(f"  Fetched {completed}/{len(ids_to_fetch)}...")
                    else:
                        failed_ids.append(char_id)
                except Exception as e:
                    print(f"  Error fetching character {char_id}: {e}")
                    failed_ids.append(char_id)
        
        if failed_ids:
            print(f"Successfully fetched {len(names)} character names ({len(failed_ids)} failed/invalid).")
        else:
            print(f"Successfully fetched {len(names)} character names.")
        
        # Update cache with new names
        cache.update(names)
        _CHARACTER_NAME_CACHE.update(names)
        
        # Save updated cache
        SettingFile.save_cache(cache)
        
        return cache
    
    def is_char_file(self) -> bool:
        """Check if this is a character-specific settings file"""
        return (self.name.startswith(self.CHAR_PREFIX) and 
                not self.name.startswith(self.CHAR_PREFIX + "_"))
    
    def is_user_file(self) -> bool:
        """Check if this is an account-specific settings file"""
        return (self.name.startswith(self.USER_PREFIX) and 
                not self.name.startswith(self.USER_PREFIX + "_"))
    
    def last_modified(self) -> float:
        """Get the last modified timestamp"""
        return self.path.stat().st_mtime
