"""ESI API client for EVE Online character information."""

import http.client
import json
import socket
from typing import Optional


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
            Character name if successful, None otherwise.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self._make_request(f"/latest/characters/{char_id}/")
                
                if result is None:
                    # Could be 404 (invalid ID) or other non-retryable error
                    return None
                
                return result.get('name')
                
            except socket.timeout:
                if attempt < self.MAX_RETRIES - 1:
                    print(f"  Timeout for character {char_id}, retrying (attempt {attempt + 2}/{self.MAX_RETRIES})...")
                    continue
                else:
                    print(f"  Timeout for character {char_id} after {self.MAX_RETRIES} attempts")
                    return None
                    
            except (socket.error, ConnectionError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    print(f"  Connection error for {char_id}, retrying...")
                    continue
                else:
                    print(f"  Connection error for character {char_id} after {self.MAX_RETRIES} attempts")
                    return None
                    
            except Exception as e:
                print(f"  Unexpected error for character {char_id}: {e}")
                return None
        
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
            Parsed JSON response, or None if error.
        """
        if status_code == 200:
            try:
                return json.loads(data.decode('utf-8'))
            except json.JSONDecodeError as e:
                print(f"  JSON decode error: {e}")
                return None
                
        elif status_code == 404:
            # Invalid character ID - don't retry
            return None
            
        elif status_code >= 500:
            # Server error - caller can retry
            print(f"  Server error: HTTP {status_code}")
            raise ConnectionError(f"ESI server error: {status_code}")
            
        else:
            # Other error - don't retry
            print(f"  HTTP error: {status_code}")
            return None
