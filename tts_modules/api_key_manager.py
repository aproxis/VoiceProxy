import csv
import shutil
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from .config import TTSConfig
from .proxy_manager import ProxyRotator

logger = logging.getLogger(__name__)

class APIKeyManager:
    """Manages API key rotation and validation, including token tracking."""

    def __init__(self, csv_file_path: Path, proxy_rotator: ProxyRotator, config: TTSConfig):
        self.csv_file_path = csv_file_path
        self.proxy_rotator = proxy_rotator
        self.config = config # Store config to access test_api_switching_mode
        self.api_keys_data: List[Dict[str, Any]] = []
        self.current_api_key_index = 0
        self.token_refresh_interval = timedelta(hours=1) # Refresh token balance every hour
        self._load_api_keys()

    def _load_api_keys(self):
        """Load API keys from CSV file, including token balance and last checked timestamp."""
        if not self.csv_file_path.exists():
            logger.warning(f"API keys CSV file not found: {self.csv_file_path}. Please create it.")
            return

        try:
            with open(self.csv_file_path, mode='r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    api_key_data = {
                        'API': row.get('API', '').strip(),
                        'Date': row.get('Date', '').strip(), # Keep original date format for now
                        'available_tokens': int(row['available_tokens']) if row.get('available_tokens') else None,
                        'last_checked': datetime.fromisoformat(row['last_checked']) if row.get('last_checked') else None,
                        'is_exhausted': False, # Track if key is temporarily exhausted
                        'voice_limit_reached': row.get('voice_limit_reached', 'False').lower() == 'true' # New: Track if voice limit is reached
                    }
                    if api_key_data['API']:
                        self.api_keys_data.append(api_key_data)
            logger.info(f"Loaded {len(self.api_keys_data)} API keys.")
        except Exception as e:
            logger.error(f"Error loading API keys from CSV: {e}")
            self.api_keys_data = []

    def _save_api_keys_to_csv(self):
        """Save current API key data back to the CSV file."""
        if not self.api_keys_data:
            return

        fieldnames = ['API', 'Date', 'available_tokens', 'last_checked', 'is_exhausted', 'voice_limit_reached'] # Added 'voice_limit_reached'
        try:
            temp_file_path = self.csv_file_path.with_suffix('.tmp')
            with open(temp_file_path, mode='w', newline='', encoding='utf-8') as temp_file:
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                for key_data in self.api_keys_data:
                    row_to_write = key_data.copy()
                    if isinstance(row_to_write.get('last_checked'), datetime):
                        row_to_write['last_checked'] = row_to_write['last_checked'].isoformat()
                    # Ensure boolean flags are written as strings
                    row_to_write['is_exhausted'] = str(row_to_write.get('is_exhausted', False))
                    row_to_write['voice_limit_reached'] = str(row_to_write.get('voice_limit_reached', False))
                    writer.writerow(row_to_write)

            shutil.move(str(temp_file_path), str(self.csv_file_path))
            logger.info("API keys CSV file updated successfully.")
        except Exception as e:
            logger.error(f"Error saving API keys to CSV: {e}")

    def _fetch_token_balance(self, api_key: str) -> Optional[int]:
        """Fetches the current token balance for a given API key from ElevenLabs."""
        url = "https://api.elevenlabs.io/v1/user/subscription"
        headers = {"xi-api-key": api_key}
        
        try:
            response = requests.get(url, headers=headers, 
                                    proxies=self.proxy_rotator.get_current_proxy(), 
                                    timeout=10) # Shorter timeout for balance check
            response.raise_for_status()
            data = response.json()
            logger.debug(f"ElevenLabs subscription response data: {data}")

            # Check for character_limit and character_count directly in the top-level response
            if 'character_limit' in data and 'character_count' in data:
                character_limit = data['character_limit']
                character_count = data['character_count']
                available = character_limit - character_count
                
                logger.info(f"API key {api_key[:5]}... has {available} available tokens.")
                return available
            else:
                logger.warning(f"Unexpected response structure from ElevenLabs subscription API for API key {api_key[:5]}...: Missing character_limit or character_count. Response: {data}")
                return None # Indicate failure to get balance
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch token balance for API key {api_key[:5]}...: {e}")
            return None

    def update_token_balance(self, api_key: str, used_tokens: int):
        """Decrements available tokens for an API key and persists the change."""
        for key_data in self.api_keys_data:
            if key_data['API'] == api_key:
                if key_data['available_tokens'] is not None:
                    if self.config.test_api_switching_mode:
                        # In test mode, drastically reduce tokens to force switching
                        key_data['available_tokens'] = max(0, key_data['available_tokens'] - 10) # Use a small fixed reduction
                        logger.info(f"TEST MODE: Artificially reduced tokens for {api_key[:5]}... by 10. Remaining: {key_data['available_tokens']}")
                    else:
                        key_data['available_tokens'] -= used_tokens
                        if key_data['available_tokens'] < 0:
                            key_data['available_tokens'] = 0 # Ensure it doesn't go negative
                key_data['last_checked'] = datetime.now()
                key_data['is_exhausted'] = (key_data['available_tokens'] == 0)
                logger.info(f"Updated API key {api_key[:5]}...: used {used_tokens} tokens, remaining: {key_data['available_tokens']}")
                self._save_api_keys_to_csv()
                return
        logger.warning(f"Attempted to update token balance for unknown API key: {api_key[:5]}...")

    def mark_voice_limit_reached(self, api_key: str):
        """Marks an API key as having reached its voice creation limit."""
        for key_data in self.api_keys_data:
            if key_data['API'] == api_key:
                key_data['voice_limit_reached'] = True
                logger.warning(f"API key {api_key[:5]}... marked as voice limit reached.")
                self._save_api_keys_to_csv()
                return
        logger.warning(f"Attempted to mark voice limit for unknown API key: {api_key[:5]}...")

    def get_api_key(self, required_tokens: int = 1) -> Optional[str]:
        """
        Gets an available API key with sufficient tokens.
        Refreshes token balance if needed. Rotates through keys.
        """
        if not self.api_keys_data:
            logger.error("No API keys loaded.")
            return None

        # Filter out exhausted keys for this rotation attempt
        available_keys_for_rotation = [
            key_data for key_data in self.api_keys_data if not key_data['is_exhausted']
        ]
        
        if not available_keys_for_rotation:
            logger.warning("All API keys are currently exhausted. Attempting to refresh all.")
            # If all are exhausted, try to refresh all of them
            for key_data in self.api_keys_data:
                self._refresh_key_balance(key_data)
            
            available_keys_for_rotation = [
                key_data for key_data in self.api_keys_data if not key_data['is_exhausted']
            ]
            if not available_keys_for_rotation:
                logger.error("No API keys available even after refreshing.")
                return None

        # Start from current index and iterate through available keys
        start_index = self.current_api_key_index
        for _ in range(len(available_keys_for_rotation)):
            current_key_data = available_keys_for_rotation[self.current_api_key_index % len(available_keys_for_rotation)]
            self.current_api_key_index = (self.current_api_key_index + 1) % len(available_keys_for_rotation)

            api_key = current_key_data['API']

            # Refresh token balance if needed
            if current_key_data['available_tokens'] is None or \
               (current_key_data['last_checked'] and datetime.now() - current_key_data['last_checked'] > self.token_refresh_interval):
                self._refresh_key_balance(current_key_data)
            
            # Check if key has enough tokens after refresh
            if current_key_data['available_tokens'] is not None and \
               current_key_data['available_tokens'] >= required_tokens:
                logger.info(f"Selected API key: {api_key[:5]}... (Available tokens: {current_key_data['available_tokens']})")
                return api_key
            else:
                logger.warning(f"API key {api_key[:5]}... has insufficient tokens ({current_key_data['available_tokens']}) or is exhausted. Trying next.")
                current_key_data['is_exhausted'] = True # Mark as exhausted for this cycle

        logger.error(f"No API key found with at least {required_tokens} available tokens.")
        return None

    def _refresh_key_balance(self, key_data: Dict[str, Any]):
        """Helper to refresh a single key's balance."""
        fetched_tokens = self._fetch_token_balance(key_data['API'])
        if fetched_tokens is not None:
            key_data['available_tokens'] = fetched_tokens
            key_data['last_checked'] = datetime.now()
            key_data['is_exhausted'] = (fetched_tokens == 0)
            self._save_api_keys_to_csv()
        else:
            # If fetching fails, assume 0 tokens for now to avoid using it
            key_data['available_tokens'] = 0
            key_data['last_checked'] = datetime.now()
            key_data['is_exhausted'] = True
            logger.warning(f"Could not refresh balance for {key_data['API'][:5]}..., marking as exhausted.")
            self._save_api_keys_to_csv()

    def current_api_key_has_enough_tokens(self, required_tokens: int) -> bool:
        """Checks if the currently selected API key has enough tokens."""
        if not self.api_keys_data:
            return False
        
        # Find the currently active API key data
        current_api_key_str = self.get_current_api_key_string()
        if not current_api_key_str:
            return False

        for key_data in self.api_keys_data:
            if key_data['API'] == current_api_key_str:
                return key_data['available_tokens'] is not None and key_data['available_tokens'] >= required_tokens
        return False # Should not happen if get_current_api_key_string works

    def get_current_api_key_string(self) -> Optional[str]:
        """Returns the string of the currently active API key."""
        if not self.api_keys_data:
            return None
        # This assumes get_api_key() has been called and current_api_key_index points to a valid key
        # However, get_api_key() rotates, so we need to be careful.
        # For now, let's assume the last key returned by get_api_key is "current"
        # A more robust solution might involve storing the currently active key explicitly.
        # For simplicity, we'll just return the key at the current_api_key_index
        # after get_api_key has been called.
        
        # This method needs to be called carefully, as current_api_key_index is for rotation.
        # A better approach would be to pass the active API key explicitly.
        # For now, let's return the API key that get_api_key() would *next* consider.
        # This is a temporary workaround until the calling logic is refactored.
        
        # Re-evaluating: The current_api_key_index is used for rotation *within* get_api_key.
        # We need to know which key was *actually* returned by the last successful get_api_key call.
        # Let's add an attribute to store the last successfully returned API key.
        return self._last_returned_api_key

    def set_last_returned_api_key(self, api_key: str):
        """Sets the last API key that was successfully returned by get_api_key."""
        self._last_returned_api_key = api_key
