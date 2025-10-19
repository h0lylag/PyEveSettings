"""Character name caching for PyEveSettings."""

from typing import Dict, Set, Optional, List
from concurrent.futures import ThreadPoolExecutor
from .esi_client import ESIClient


class APICache:
    """Manages caching of character names from ESI API."""
    
    def __init__(self, esi_client: Optional[ESIClient] = None):
        """Initialize the API cache.
        
        Args:
            esi_client: ESI client instance. If None, creates a new one.
        """
        self.esi_client = esi_client or ESIClient()
        self._cache: Dict[int, str] = {}
        self._invalid_ids: Set[int] = set()
    
    def load_cache(self, character_names: Dict[int, str], invalid_ids: Set[int]) -> None:
        """Load cache from existing data.
        
        Args:
            character_names: Dictionary of character ID -> name mappings.
            invalid_ids: Set of invalid character IDs.
        """
        self._cache = character_names.copy()
        self._invalid_ids = invalid_ids.copy()
    
    def get(self, char_id: int) -> Optional[str]:
        """Get character name from cache.
        
        Args:
            char_id: Character ID.
            
        Returns:
            Character name if cached, None otherwise.
        """
        return self._cache.get(char_id)
    
    def is_cached(self, char_id: int) -> bool:
        """Check if character ID is in cache.
        
        Args:
            char_id: Character ID.
            
        Returns:
            True if cached, False otherwise.
        """
        return char_id in self._cache
    
    def is_invalid(self, char_id: int) -> bool:
        """Check if character ID is marked as invalid.
        
        Args:
            char_id: Character ID.
            
        Returns:
            True if invalid, False otherwise.
        """
        return char_id in self._invalid_ids
    
    def add(self, char_id: int, name: str) -> None:
        """Add character to cache.
        
        Args:
            char_id: Character ID.
            name: Character name.
        """
        self._cache[char_id] = name
    
    def mark_invalid(self, char_id: int) -> None:
        """Mark character ID as invalid.
        
        Args:
            char_id: Character ID.
        """
        self._invalid_ids.add(char_id)
    
    def get_all_cached(self) -> Dict[int, str]:
        """Get all cached character names.
        
        Returns:
            Dictionary of all cached character ID -> name mappings.
        """
        return self._cache.copy()
    
    def get_all_invalid(self) -> Set[int]:
        """Get all invalid character IDs.
        
        Returns:
            Set of all invalid character IDs.
        """
        return self._invalid_ids.copy()
    
    def fetch_names_bulk(self, character_ids: List[int]) -> Dict[int, str]:
        """Fetch character names for multiple IDs, using cache where possible.
        
        Args:
            character_ids: List of character IDs to fetch.
            
        Returns:
            Dictionary mapping character ID to name (only for valid IDs).
        """
        if not character_ids:
            return {}
        
        # Deduplicate
        unique_ids = list(set(character_ids))
        
        if not unique_ids:
            return {}
        
        # Find IDs we need to fetch (skip cached and invalid)
        ids_to_fetch = [
            cid for cid in unique_ids 
            if cid not in self._cache and cid not in self._invalid_ids
        ]
        
        # Count statistics
        cached_count = len([cid for cid in unique_ids if cid in self._cache])
        invalid_count = len([cid for cid in unique_ids if cid in self._invalid_ids])
        
        # All IDs already processed
        if not ids_to_fetch:
            if invalid_count > 0:
                print(f"All {len(unique_ids)} character names loaded from cache ({invalid_count} known invalid).")
            else:
                print(f"All {len(unique_ids)} character names loaded from cache.")
            return self._cache.copy()
        
        # Fetch missing names
        print(f"Fetching {len(ids_to_fetch)} character names (async)...")
        if cached_count > 0:
            print(f"Using cache for {cached_count} characters.")
        if invalid_count > 0:
            print(f"Skipping {invalid_count} known invalid IDs.")
        
        # Use thread pool for concurrent requests
        failed_ids = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {
                executor.submit(self.esi_client.fetch_character_name, cid): cid 
                for cid in ids_to_fetch
            }
            
            for future in future_to_id:
                char_id = future_to_id[future]
                try:
                    result = future.result()
                    if result:
                        self._cache[char_id] = result
                    else:
                        # Mark as invalid
                        self._invalid_ids.add(char_id)
                        failed_ids.append(char_id)
                except Exception as e:
                    print(f"  Exception fetching character {char_id}: {e}")
                    failed_ids.append(char_id)
        
        if failed_ids:
            print(f"Failed to fetch {len(failed_ids)} character name(s).")
        
        print(f"Successfully fetched {len(ids_to_fetch) - len(failed_ids)} character names.")
        
        return self._cache.copy()
