import logging
import requests
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import TTSConfig
from .proxy_manager import ProxyRotator

logger = logging.getLogger(__name__)

class VoiceManager:
    """Manages voice operations for ElevenLabs API"""
    
    def __init__(self, config: TTSConfig, proxy_rotator: ProxyRotator):
        self.config = config
        self.proxy_rotator = proxy_rotator
        self._voice_cache: Dict[str, List[Dict]] = {} # Cache for voices, keyed by API key
        self.cache_dir = config.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True) # Ensure cache directory exists
        
    def get_available_voices(self, api_key: str, force_refresh: bool = False) -> List[Dict]:
        """Fetches and caches available voices from ElevenLabs API."""
        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"voices_data_{api_key_hash}.json"

        if not force_refresh and cache_file.exists():
            logger.debug(f"Loading voices from disk cache for API key {api_key[:5]}...")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                self._voice_cache[api_key] = cached_data
                logger.info(f"Successfully loaded {len(cached_data)} voices from disk cache.")
                return cached_data
            except Exception as e:
                logger.warning(f"Error loading voices from disk cache: {e}. Fetching from web.")
                # If cache is corrupted, proceed to fetch from web

        logger.debug(f"Fetching voices from web for API key {api_key[:5]}...")
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}

        def make_request():
            return requests.get(url, headers=headers,
                                proxies=self.proxy_rotator.get_current_proxy(),
                                timeout=self.config.timeout)

        response = self._make_request_with_retry(make_request, "get available voices", return_response=True)
        if not response:
            logger.error("Failed to retrieve available voices.")
            return []

        try:
            data = response.json()
            voices_data = []
            for voice in data.get("voices", []):
                # Process preview_url to be a local path if cached
                processed_voice = {
                    "voice_id": voice.get("voice_id"),
                    "name": voice.get("name"),
                    "preview_url": voice.get("preview_url"),
                    "verified_languages": [] # Initialize verified_languages
                }
                
                # Process verified_languages and their preview_urls
                verified_languages = []
                for lang_info in voice.get("verified_languages", []):
                    original_preview_url = lang_info.get("preview_url")
                    if original_preview_url:
                        # Generate a unique filename for the preview MP3
                        preview_filename = f"preview_{voice.get('voice_id')}_{lang_info.get('language')}_{lang_info.get('model_id')}.mp3"
                        local_preview_path = self.cache_dir / preview_filename
                        
                        # Only download if not already cached
                        if not local_preview_path.exists():
                            logger.debug(f"Downloading preview for {voice.get('name')} ({lang_info.get('language')})...")
                            try:
                                self._download_and_cache_preview(original_preview_url, local_preview_path)
                            except Exception as download_e:
                                logger.warning(f"Failed to download preview for {voice.get('name')} ({lang_info.get('language')}): {download_e}")
                                local_preview_path = None # Mark as not available locally
                        
                        if local_preview_path and local_preview_path.exists():
                            lang_info["preview_url"] = str(local_preview_path.resolve()) # Update to absolute local path
                        else:
                            lang_info["preview_url"] = original_preview_url # Keep original if download failed
                    verified_languages.append(lang_info)
                
                processed_voice["verified_languages"] = verified_languages
                voices_data.append(processed_voice)

            self._voice_cache[api_key] = voices_data
            self._cache_voice_data(api_key, voices_data) # Save processed data to disk cache
            logger.info(f"Successfully fetched and cached {len(voices_data)} voices for API key {api_key[:5]}...")
            return voices_data
        except Exception as e:
            logger.error(f"Error parsing available voices response: {e}")
            return []

    def get_shared_voices(self, api_key: str, gender: Optional[str] = None, language: Optional[str] = None, page_size: int = 10, force_refresh: bool = False) -> List[Dict]:
        """Fetches and caches shared voices from ElevenLabs API based on criteria."""
        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()
        # Create a unique cache file name based on search parameters
        params_hash = hashlib.md5(f"{gender}-{language}-{page_size}".encode()).hexdigest()
        cache_file = self.cache_dir / f"shared_voices_data_{api_key_hash}_{params_hash}.json"

        if not force_refresh and cache_file.exists():
            logger.debug(f"Loading shared voices from disk cache for API key {api_key[:5]} and params {params_hash}...")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                logger.info(f"Successfully loaded {len(cached_data)} shared voices from disk cache.")
                return cached_data
            except Exception as e:
                logger.warning(f"Error loading shared voices from disk cache: {e}. Fetching from web.")
                # If cache is corrupted, proceed to fetch from web

        logger.debug(f"Fetching shared voices from web for API key {api_key[:5]} and params {params_hash}...")
        url = "https://api.elevenlabs.io/v1/shared-voices"
        headers = {"xi-api-key": api_key}
        params = {"page_size": page_size}
        if gender:
            params["gender"] = gender
        if language:
            params["language"] = language

        def make_request():
            return requests.get(url, headers=headers, params=params,
                                proxies=self.proxy_rotator.get_current_proxy(),
                                timeout=self.config.timeout)

        response = self._make_request_with_retry(make_request, "get shared voices", return_response=True)
        if not response:
            logger.error("Failed to retrieve shared voices.")
            return []

        try:
            data = response.json()
            shared_voices_data = []
            for voice in data.get("voices", []):
                # Only include voices where free_users_allowed is true
                if voice.get("free_users_allowed"):
                    processed_voice = {
                        "public_owner_id": voice.get("public_owner_id"),
                        "voice_id": voice.get("voice_id"),
                        "name": voice.get("name"),
                        "description": voice.get("description"),
                        "preview_url": voice.get("preview_url"), # This is the main preview for the voice
                        "verified_languages": [] # Initialize verified_languages
                    }
                    
                    # Process verified_languages and their preview_urls
                    verified_languages = []
                    for lang_info in voice.get("verified_languages", []):
                        original_preview_url = lang_info.get("preview_url")
                        if original_preview_url:
                            # Generate a unique filename for the preview MP3
                            preview_filename = f"shared_preview_{voice.get('voice_id')}_{lang_info.get('language')}_{lang_info.get('model_id')}.mp3"
                            local_preview_path = self.cache_dir / preview_filename
                            
                            # Only download if not already cached
                            if not local_preview_path.exists():
                                logger.debug(f"Downloading shared voice preview for {voice.get('name')} ({lang_info.get('language')})...")
                                try:
                                    self._download_and_cache_preview(original_preview_url, local_preview_path)
                                except Exception as download_e:
                                    logger.warning(f"Failed to download shared voice preview for {voice.get('name')} ({lang_info.get('language')}): {download_e}")
                                    local_preview_path = None # Mark as not available locally
                            
                            if local_preview_path and local_preview_path.exists():
                                lang_info["preview_url"] = str(local_preview_path.resolve()) # Update to absolute local path
                            else:
                                lang_info["preview_url"] = original_preview_url # Keep original if download failed
                        verified_languages.append(lang_info)
                    
                    processed_voice["verified_languages"] = verified_languages
                    shared_voices_data.append(processed_voice)
                else:
                    logger.debug(f"Skipping shared voice '{voice.get('name')}' as free_users_allowed is false.")

            self._cache_shared_voice_data(api_key, params_hash, shared_voices_data) # Save processed data to disk cache
            logger.info(f"Successfully fetched and cached {len(shared_voices_data)} shared voices for API key {api_key[:5]}...")
            return shared_voices_data
        except Exception as e:
            logger.error(f"Error parsing shared voices response: {e}")
            return []

    def add_voice(self, api_key: str, voice_id: str, public_owner_id: str, new_name: str) -> bool:
        """Add voice from library"""
        url = f"https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{voice_id}"
        headers = {"xi-api-key": api_key}
        data = {"new_name": new_name}
        
        return self._make_request_with_retry(
            lambda: requests.post(url, json=data, headers=headers, 
                                proxies=self.proxy_rotator.get_current_proxy(), 
                                timeout=self.config.timeout),
            "add voice"
        )
    
    def get_voice_id(self, api_key: str, original_voice_id: str, public_owner_id: str) -> Optional[str]:
        """Get new voice ID after adding from library"""
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        
        def make_request():
            return requests.get(url, headers=headers, 
                              proxies=self.proxy_rotator.get_current_proxy(), 
                              timeout=self.config.timeout)
        
        response = self._make_request_with_retry(make_request, "get voice ID", return_response=True)
        if not response:
            return None
            
        try:
            data = response.json()
            for voice in data.get("voices", []):
                sharing = voice.get("sharing", {})
                if (sharing.get("original_voice_id") == original_voice_id and 
                    sharing.get("public_owner_id") == public_owner_id):
                    return voice["voice_id"]
            
            logger.warning("New voice ID not found")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing voice ID response: {e}")
            return None
    
    def cleanup_voices(self, api_key: str):
        """Remove all non-premade voices"""
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "xi-api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        def make_request():
            return requests.get(url, headers=headers, 
                              proxies=self.proxy_rotator.get_current_proxy(), 
                              timeout=self.config.timeout)
        
        response = self._make_request_with_retry(make_request, "cleanup voices", return_response=True)
        if not response:
            return
            
        try:
            data = response.json()
            voices_to_delete = [
                voice for voice in data.get("voices", [])
                if voice.get("category") != "premade"
            ]
            
            for voice in voices_to_delete:
                logger.info(f"Deleting voice: {voice['name']}")
                self.delete_voice(api_key, voice["voice_id"])
                
        except Exception as e:
            logger.error(f"Error processing cleanup response: {e}")
    
    def delete_voice(self, api_key: str, voice_id: str) -> bool:
        """Delete voice from library"""
        url = f"https://api.elevenlabs.io/v1/voices/{voice_id}"
        headers = {"xi-api-key": api_key}
        
        success = self._make_request_with_retry(
            lambda: requests.delete(url, headers=headers, 
                                  proxies=self.proxy_rotator.get_current_proxy(), 
                                  timeout=self.config.timeout),
            f"delete voice {voice_id}"
        )
        
        if success:
            logger.info(f"Voice {voice_id} deleted successfully")
        return success
    
    def _make_request_with_retry(self, request_func, operation: str, return_response: bool = False):
        """Make HTTP request with proxy rotation on failure"""
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()
                # Add configurable delay before API call
                time.sleep(self.config.api_call_delay_seconds)
                response = request_func()
                response_time = time.time() - start_time
                
                response.raise_for_status()
                self.proxy_rotator.mark_proxy_success(response_time)
                
                if return_response:
                    return response
                return True
                
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Proxy error during {operation} (attempt {attempt + 1}): {e}")
                self.proxy_rotator.mark_proxy_failed()
                self.proxy_rotator.rotate_proxy()
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error during {operation} (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
        
        logger.error(f"All attempts failed for {operation}")
        if return_response:
            return None
        return False

    def _cache_voice_data(self, api_key: str, voices_data: List[Dict]):
        """Saves voice data to disk cache."""
        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"voices_data_{api_key_hash}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(voices_data, f, indent=4)
            logger.debug(f"Voice data cached to {cache_file}")
        except Exception as e:
            logger.error(f"Failed to cache voice data: {e}")

    def _cache_shared_voice_data(self, api_key: str, params_hash: str, shared_voices_data: List[Dict]):
        """Saves shared voice data to disk cache."""
        api_key_hash = hashlib.md5(api_key.encode()).hexdigest()
        cache_file = self.cache_dir / f"shared_voices_data_{api_key_hash}_{params_hash}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(shared_voices_data, f, indent=4)
            logger.debug(f"Shared voice data cached to {cache_file}")
        except Exception as e:
            logger.error(f"Failed to cache shared voice data: {e}")

    def _download_and_cache_preview(self, url: str, local_path: Path):
        """Downloads a preview MP3 and saves it to the local cache."""
        try:
            response = requests.get(url, stream=True, timeout=self.config.timeout)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.debug(f"Preview downloaded and cached to {local_path}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading preview from {url}: {e}")
            raise # Re-raise to be caught by calling function
