"""ESI API client for EVE Online character information."""

import http.client
import json
import socket
from typing import Optional
from exceptions import ESIError, InvalidCharacterError


class ESIClient:
    """Client for EVE Online ESI API."""
    
    ESI_HOST = "esi.evetech.net"
    TIMEOUT = 10
    MAX_RETRIES = 3
    USER_AGENT = "PyEveSettings"
    
    def fetch_character_name(self, char_id: int) -> Optional[str]:
        """Fetch a single character name from ESI API.
        
        Args:
            char_id: Character ID to fetch.
            
        Returns:
            Character name if successful, None for invalid character IDs.
            
        Raises:
            ESIError: If API connection fails after retries or unexpected error occurs.
            InvalidCharacterError: If the character ID is invalid (404).
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self._make_request(f"/latest/characters/{char_id}/")
                
                if result is None:
                    return None
                
                return result.get('name')
            
            except InvalidCharacterError:
                # Invalid character ID (404) - don't retry
                return None
                
            except socket.timeout:
                if attempt < self.MAX_RETRIES - 1:
                    print(f"  Timeout for character {char_id}, retrying (attempt {attempt + 2}/{self.MAX_RETRIES})...")
                    continue
                else:
                    raise ESIError(
                        f"Timeout fetching character {char_id} after {self.MAX_RETRIES} attempts"
                    )
                    
            except (socket.error, ConnectionError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    print(f"  Connection error for {char_id}, retrying...")
                    continue
                else:
                    raise ESIError(
                        f"Connection error for character {char_id} after {self.MAX_RETRIES} attempts: {e}"
                    ) from e
                    
            except ESIError:
                # Re-raise ESI errors (from _handle_response)
                raise
                    
            except Exception as e:
                raise ESIError(
                    f"Unexpected error fetching character {char_id}: {e}"
                ) from e
        
        return None
    
    def _make_request(self, path: str) -> Optional[dict]:
        """Make an HTTPS request to ESI API.
        
        Args:
            path: API endpoint path (e.g., "/latest/characters/12345/").
            
        Returns:
            Parsed JSON response as dict, or None if request failed.
        """
        conn = None
        try:
            conn = http.client.HTTPSConnection(self.ESI_HOST, timeout=self.TIMEOUT)
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': self.USER_AGENT
            }
            
            conn.request("GET", path, headers=headers)
            response = conn.getresponse()
            data = response.read()
            
            return self._handle_response(response.status, data)
            
        finally:
            if conn:
                conn.close()
    
    def _handle_response(self, status_code: int, data: bytes) -> Optional[dict]:
        """Handle HTTP response from ESI API.
        
        Args:
            status_code: HTTP status code.
            data: Response body as bytes.
            
        Returns:
            Parsed JSON response if successful.
            
        Raises:
            InvalidCharacterError: If character ID is invalid (404).
            ESIError: For server errors or JSON decode failures.
        """
        if status_code == 200:
            try:
                return json.loads(data.decode('utf-8'))
            except json.JSONDecodeError as e:
                raise ESIError(f"Failed to decode ESI response: {e}") from e
                
        elif status_code == 404:
            # Invalid character ID - don't retry
            raise InvalidCharacterError(f"Character ID not found (HTTP 404)")
            
        elif status_code >= 500:
            # Server error - caller can retry
            raise ESIError(f"ESI server error: HTTP {status_code}")
            
        else:
            # Other error
            raise ESIError(f"ESI request failed: HTTP {status_code}")
