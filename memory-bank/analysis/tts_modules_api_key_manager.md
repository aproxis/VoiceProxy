# Analysis for `tts_modules/api_key_manager.py`

### **`APIKeyManager` Class**

#### **Core Purpose and Logic:**
The `APIKeyManager` class is designed to robustly handle ElevenLabs API keys. Its core responsibilities include:
- Loading API keys from a CSV file (`BASE.csv`).
- Saving updated API key data (including token balances and last checked timestamps) back to the CSV.
- Fetching the current token balance for an API key from the ElevenLabs subscription API.
- Decrementing token balances as they are used.
- Marking API keys as exhausted or having reached voice creation limits.
- Providing an available API key with sufficient tokens, rotating through keys as needed, and refreshing token balances periodically.
- Interacting with `ProxyRotator` to use proxies for API calls to ElevenLabs.

#### **Internal and External Dependencies:**
- **Internal Dependencies (Classes/Modules):**
    - `TTSConfig` (from `.config`): To access configuration settings like `test_api_switching_mode`.
    - `ProxyRotator` (from `.proxy_manager`): To use proxies when making API calls to ElevenLabs (e.g., fetching token balance).
- **External Dependencies (Libraries):**
    - `csv`: For reading from and writing to CSV files.
    - `shutil`: For moving temporary files during CSV saving.
    - `logging`: For logging messages.
    - `requests`: For making HTTP requests to the ElevenLabs API.
    - `datetime`, `timedelta` (from `datetime` module): For managing timestamps and time intervals (e.g., `token_refresh_interval`).
    - `pathlib.Path`: For object-oriented file path manipulation.
    - `typing`: For type hints.

#### **Inputs and Outputs:**

##### **`__init__(self, csv_file_path: Path, proxy_rotator: ProxyRotator, config: TTSConfig)`**
- **Inputs:**
    - `csv_file_path` (Path): Path to the CSV file containing API keys.
    - `proxy_rotator` (ProxyRotator): An instance of the proxy rotator to use for API calls.
    - `config` (TTSConfig): An instance of the configuration class.
- **Outputs:** Initializes `self.csv_file_path`, `self.proxy_rotator`, `self.config`, `self.api_keys_data` (loaded from CSV), `self.current_api_key_index`, and `self.token_refresh_interval`.

##### **`_load_api_keys(self)`**
- **Purpose:** Loads API key data from the specified CSV file into `self.api_keys_data`.
- **Inputs:** Reads `self.csv_file_path`.
- **Outputs:** Populates `self.api_keys_data` list with dictionaries representing each API key, including `API`, `Date`, `available_tokens`, `last_checked`, `is_exhausted`, and `voice_limit_reached`. Logs warnings if the file is not found or errors during loading.

##### **`_save_api_keys_to_csv(self)`**
- **Purpose:** Saves the current state of `self.api_keys_data` back to the CSV file. It uses a temporary file to ensure data integrity during saving.
- **Inputs:** Uses `self.api_keys_data`.
- **Outputs:** Writes to `self.csv_file_path`. Logs errors during saving.

##### **`_fetch_token_balance(self, api_key: str) -> Optional[int]`**
- **Purpose:** Fetches the current token balance for a given API key from the ElevenLabs subscription API.
- **Inputs:**
    - `api_key` (str): The API key for which to fetch the balance.
- **Outputs:** Returns `Optional[int]`: The number of available tokens, or `None` if fetching fails. Makes a GET request to `https://api.elevenlabs.io/v1/user/subscription`.

##### **`update_token_balance(self, api_key: str, used_tokens: int)`**
- **Purpose:** Decrements the available tokens for a specific API key and persists the change to the CSV file. Includes a test mode to artificially reduce tokens.
- **Inputs:**
    - `api_key` (str): The API key to update.
    - `used_tokens` (int): The number of tokens used.
- **Outputs:** Updates `available_tokens`, `last_checked`, and `is_exhausted` for the specified key in `self.api_keys_data` and saves to CSV. Logs updates.

##### **`mark_voice_limit_reached(self, api_key: str)`**
- **Purpose:** Marks an API key as having reached its voice creation limit and persists the change.
- **Inputs:**
    - `api_key` (str): The API key to mark.
- **Outputs:** Sets `voice_limit_reached` to `True` for the specified key in `self.api_keys_data` and saves to CSV. Logs warnings.

##### **`get_api_key(self, required_tokens: int = 1) -> Optional[str]`**
- **Purpose:** Selects and returns an available API key that has enough tokens for the `required_tokens`. It rotates through keys, refreshes token balances if needed, and filters out exhausted keys.
- **Inputs:**
    - `required_tokens` (int): The minimum number of tokens required for the operation.
- **Outputs:** Returns `Optional[str]`: The selected API key string, or `None` if no suitable key is found. Logs selection and warnings.

##### **`_refresh_key_balance(self, key_data: Dict[str, Any])`**
- **Purpose:** Helper function to refresh the token balance for a single API key data entry.
- **Inputs:**
    - `key_data` (Dict[str, Any]): A dictionary representing an API key's data.
- **Outputs:** Updates `available_tokens`, `last_checked`, and `is_exhausted` within the `key_data` dictionary and saves to CSV.

##### **`current_api_key_has_enough_tokens(self, required_tokens: int) -> bool`**
- **Purpose:** Checks if the currently selected API key (based on internal state) has enough tokens.
- **Inputs:**
    - `required_tokens` (int): The number of tokens to check against.
- **Outputs:** Returns `bool`: `True` if the current key has enough tokens, `False` otherwise.

##### **`get_current_api_key_string(self) -> Optional[str]`**
- **Purpose:** Returns the string of the API key that was last successfully returned by `get_api_key`.
- **Inputs:** None.
- **Outputs:** Returns `Optional[str]`: The API key string.

##### **`set_last_returned_api_key(self, api_key: str)`**
- **Purpose:** Sets an internal attribute to store the last API key successfully returned by `get_api_key`.
- **Inputs:**
    - `api_key` (str): The API key string.
- **Outputs:** Sets `self._last_returned_api_key`.
