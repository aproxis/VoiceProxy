# Analysis for `tts_modules/voice_manager.py`

### **`VoiceManager` Class**

#### **Core Purpose and Logic:**
The `VoiceManager` class is responsible for all operations related to ElevenLabs voices. This includes:
- Fetching a list of available standard voices.
- Searching and retrieving shared voices based on criteria (gender, language).
- Managing library voices (adding a voice from the ElevenLabs library to the user's account, getting its ID, and cleaning up/deleting non-premade voices).
- Caching voice data and preview MP3s locally to reduce API calls and improve performance.
- Utilizing `ProxyRotator` for all ElevenLabs API interactions.

#### **Internal and External Dependencies:**
- **Internal Dependencies (Classes/Modules):**
    - `TTSConfig` (from `.config`): To access configuration settings like `cache_dir`, `timeout`, `max_retries`, `api_call_delay_seconds`, `retry_delay`.
    - `ProxyRotator` (from `.proxy_manager`): To route all ElevenLabs API requests through configured proxies.
- **External Dependencies (Libraries):**
    - `logging`: For logging messages.
    - `requests`: For making HTTP requests to the ElevenLabs API.
    - `time`: For delays and timeouts.
    - `json`: For reading/writing JSON data to cache files.
    - `hashlib`: For generating hashes for cache file names.
    - `pathlib.Path`: For object-oriented file path manipulation.
    - `typing`: For type hints.

#### **Inputs and Outputs:**

##### **`__init__(self, config: TTSConfig, proxy_rotator: ProxyRotator)`**
- **Inputs:**
    - `config` (TTSConfig): An instance of the configuration class.
    - `proxy_rotator` (ProxyRotator): An instance of the proxy rotator.
- **Outputs:** Initializes `self.config`, `self.proxy_rotator`, `self._voice_cache`, and ensures `self.cache_dir` exists.

##### **`get_available_voices(self, api_key: str, force_refresh: bool = False) -> List[Dict]`**
- **Purpose:** Fetches a list of standard voices available to the provided API key from the ElevenLabs API. It first checks a local disk cache and downloads voice preview MP3s if not already cached.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
    - `force_refresh` (bool): If `True`, bypasses the cache and fetches directly from the API.
- **Outputs:** Returns `List[Dict]`: A list of dictionaries, each representing a voice with its details (ID, name, preview URL, verified languages).
    - **API Calls:** Makes GET requests to `https://api.elevenlabs.io/v1/voices`.
    - **File Output:** Saves voice data to `self.cache_dir/voices_data_{api_key_hash}.json` and preview MP3s to `self.cache_dir/preview_*.mp3`.

##### **`get_shared_voices(self, api_key: str, gender: Optional[str] = None, language: Optional[str] = None, page_size: int = 10, force_refresh: bool = False) -> List[Dict]`**
- **Purpose:** Fetches a list of shared voices from the ElevenLabs API based on specified filters (gender, language, page size). It also caches the results and downloads preview MP3s. Only includes voices where `free_users_allowed` is true.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
    - `gender` (Optional[str]): Filter by gender (e.g., "female", "male").
    - `language` (Optional[str]): Filter by language (e.g., "en", "ru").
    - `page_size` (int): Number of results per page.
    - `force_refresh` (bool): If `True`, bypasses the cache.
- **Outputs:** Returns `List[Dict]`: A list of dictionaries, each representing a shared voice.
    - **API Calls:** Makes GET requests to `https://api.elevenlabs.io/v1/shared-voices`.
    - **File Output:** Saves shared voice data to `self.cache_dir/shared_voices_data_{api_key_hash}_{params_hash}.json` and preview MP3s to `self.cache_dir/shared_preview_*.mp3`.

##### **`add_voice(self, api_key: str, voice_id: str, public_owner_id: str, new_name: str) -> bool`**
- **Purpose:** Adds a voice from the ElevenLabs voice library to the user's account.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
    - `voice_id` (str): The ID of the voice to add.
    - `public_owner_id` (str): The public owner ID of the voice.
    - `new_name` (str): The name to give the new voice in the user's account.
- **Outputs:** Returns `bool`: `True` on success, `False` on failure.
    - **API Calls:** Makes POST requests to `https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{voice_id}`.

##### **`get_voice_id(self, api_key: str, original_voice_id: str, public_owner_id: str) -> Optional[str]`**
- **Purpose:** Retrieves the voice ID of a newly added library voice from the user's account by matching its original voice ID and public owner ID.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
    - `original_voice_id` (str): The original ID of the library voice.
    - `public_owner_id` (str): The public owner ID of the library voice.
- **Outputs:** Returns `Optional[str]`: The voice ID of the added voice, or `None` if not found.
    - **API Calls:** Makes GET requests to `https://api.elevenlabs.io/v1/voices`.

##### **`cleanup_voices(self, api_key: str)`**
- **Purpose:** Deletes all non-premade voices from the user's ElevenLabs account. This is typically used before adding a new library voice to ensure the voice limit is not reached.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
- **Outputs:** Deletes voices from the ElevenLabs account.
    - **API Calls:** Makes GET requests to `https://api.elevenlabs.io/v1/voices` and DELETE requests to `https://api.elevenlabs.io/v1/voices/{voice_id}`.

##### **`delete_voice(self, api_key: str, voice_id: str) -> bool`**
- **Purpose:** Deletes a specific voice from the user's ElevenLabs account.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key.
    - `voice_id` (str): The ID of the voice to delete.
- **Outputs:** Returns `bool`: `True` on success, `False` on failure.
    - **API Calls:** Makes DELETE requests to `https://api.elevenlabs.io/v1/voices/{voice_id}`.

##### **`_make_request_with_retry(self, request_func, operation: str, return_response: bool = False)`**
- **Purpose:** A private helper method that executes an HTTP request with retry logic, proxy rotation on failure, and configurable delays.
- **Inputs:**
    - `request_func` (callable): A function that performs the actual `requests` call.
    - `operation` (str): A descriptive string for the operation being performed (for logging).
    - `return_response` (bool): If `True`, returns the `requests.Response` object; otherwise, returns a boolean indicating success.
- **Outputs:** Returns `requests.Response` or `bool`. Logs request status, errors, and proxy actions.

##### **`_cache_voice_data(self, api_key: str, voices_data: List[Dict])`**
- **Purpose:** Saves fetched standard voice data to a JSON file in the local cache directory.
- **Inputs:**
    - `api_key` (str): The API key (used for hashing the filename).
    - `voices_data` (List[Dict]): The voice data to cache.
- **Outputs:** Writes a JSON file to `self.cache_dir`.

##### **`_cache_shared_voice_data(self, api_key: str, params_hash: str, shared_voices_data: List[Dict])`**
- **Purpose:** Saves fetched shared voice data to a JSON file in the local cache directory.
- **Inputs:**
    - `api_key` (str): The API key (used for hashing the filename).
    - `params_hash` (str): A hash of the search parameters (used for hashing the filename).
    - `shared_voices_data` (List[Dict]): The shared voice data to cache.
- **Outputs:** Writes a JSON file to `self.cache_dir`.

##### **`_download_and_cache_preview(self, url: str, local_path: Path)`**
- **Purpose:** Downloads an MP3 preview file from a given URL and saves it to the local cache.
- **Inputs:**
    - `url` (str): The URL of the MP3 preview.
    - `local_path` (Path): The local path where the preview should be saved.
- **Outputs:** Writes an MP3 file to `local_path`. Raises `requests.exceptions.RequestException` on download failure.
