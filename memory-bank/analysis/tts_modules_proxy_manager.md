# Analysis for `tts_modules/proxy_manager.py`

### **`ProxyRotator` Class**

#### **Core Purpose and Logic:**
The `ProxyRotator` class manages a list of HTTP/HTTPS proxies, enabling the application to rotate through them for API requests. Its key functionalities include:
- Loading proxy configurations from a CSV file (`proxies.csv`) or environment variables.
- Providing the current active proxy in a format suitable for the `requests` library.
- Rotating to the next available proxy.
- Marking proxies as failed (e.g., due to connection errors or API abuse detection) and temporarily excluding them from rotation.
- Testing individual proxies and all configured proxies to determine their health and response times.
- Maintaining statistics on proxy usage (successes, failures, last used, response times).

#### **Internal and External Dependencies:**
- **Internal Dependencies:** None directly within this file, but its instances are consumed by `tts_modules/processor.py`, `tts_modules/api_key_manager.py`, `tts_modules/voice_manager.py`, and `tts_gui.py`.
- **External Dependencies (Libraries):**
    - `csv`: For reading from CSV files.
    - `os`: For reading environment variables.
    - `requests`: For testing proxy connections (e.g., to `http://httpbin.org/ip`).
    - `time`: For delays.
    - `datetime`: For tracking `last_used` timestamps.
    - `logging`: For logging messages.
    - `pathlib.Path`: For object-oriented file path manipulation.
    - `typing`: For type hints.

#### **Inputs and Outputs:**

##### **`__init__(self, proxies_file: Optional[Path] = None)`**
- **Inputs:**
    - `proxies_file` (Optional[Path]): Path to the CSV file containing proxy configurations (defaults to `proxies.csv` if `None`).
- **Outputs:** Initializes `self.proxies_file`, `self.proxies` (loaded from file/env), `self.current_proxy_index`, `self.failed_proxies` (set), and `self.proxy_stats` (dict).

##### **`load_proxies(self)`**
- **Purpose:** Attempts to load proxy configurations, first from the CSV file specified by `self.proxies_file`, and if that file doesn't exist, then from environment variables.
- **Inputs:** Reads `self.proxies_file` or environment variables (`PROXY_LOGIN`, `PROXY_PASS`, `PROXY_IP`, `PROXY_PORT`, `PROXY_TYPE`).
- **Outputs:** Populates `self.proxies` list and initializes `self.proxy_stats`. Logs warnings if no proxies are found.

##### **`_load_from_csv(self)`**
- **Purpose:** Private helper to load proxies from the CSV file.
- **Inputs:** Reads `self.proxies_file`.
- **Outputs:** Appends proxy configurations to `self.proxies` and initializes stats in `self.proxy_stats`.

##### **`_load_from_env(self)`**
- **Purpose:** Private helper to load a single proxy from environment variables.
- **Inputs:** Reads environment variables.
- **Outputs:** Appends a single proxy configuration to `self.proxies` and initializes its stats.

##### **`_get_proxy_key(self, proxy_config: Dict) -> str`**
- **Purpose:** Generates a unique string key for a given proxy configuration (e.g., "ip:port").
- **Inputs:**
    - `proxy_config` (Dict): A dictionary representing a proxy's configuration.
- **Outputs:** Returns `str`: The unique proxy key.

##### **`_build_proxy_url(self, proxy_config: Dict) -> str`**
- **Purpose:** Constructs a full proxy URL string (e.g., "http://login:pass@ip:port") from a proxy configuration dictionary.
- **Inputs:**
    - `proxy_config` (Dict): A dictionary representing a proxy's configuration.
- **Outputs:** Returns `str`: The formatted proxy URL.

##### **`get_current_proxy(self) -> Dict[str, str]`**
- **Purpose:** Returns the currently active proxy configuration in a dictionary format suitable for the `requests` library (e.g., `{"http": "url", "https": "url"}`). It handles rotation and skips failed proxies. If all proxies have failed, it resets the failed list.
- **Inputs:** Uses `self.proxies`, `self.failed_proxies`, `self.current_proxy_index`.
- **Outputs:** Returns `Dict[str, str]`: A dictionary with "http" and "https" keys pointing to the proxy URL, or an empty dictionary if no proxies are available.

##### **`rotate_proxy(self)`**
- **Purpose:** Advances the `current_proxy_index` to select the next proxy in the list.
- **Inputs:** Uses `self.proxies`, `self.current_proxy_index`.
- **Outputs:** Updates `self.current_proxy_index`. Logs rotation.

##### **`mark_proxy_failed(self, proxy_config: Optional[Dict] = None)`**
- **Purpose:** Marks a proxy as failed, adding its key to `self.failed_proxies` and incrementing its failure count in `self.proxy_stats`. If no `proxy_config` is provided, it marks the currently active proxy as failed.
- **Inputs:**
    - `proxy_config` (Optional[Dict]): The proxy configuration to mark as failed.
- **Outputs:** Updates `self.failed_proxies` and `self.proxy_stats`. Logs warnings.

##### **`mark_proxy_success(self, response_time: float = 0)`**
- **Purpose:** Marks the currently active proxy as successful, incrementing its success count, updating its `last_used` timestamp, and recording its response time in `self.proxy_stats`.
- **Inputs:**
    - `response_time` (float): The time taken for the request.
- **Outputs:** Updates `self.proxy_stats`.

##### **`test_proxy(self, proxy_config: Dict, timeout: int = 10) -> Tuple[bool, float]`**
- **Purpose:** Tests a single proxy's connectivity by making a request to `http://httpbin.org/ip`.
- **Inputs:**
    - `proxy_config` (Dict): The proxy configuration to test.
    - `timeout` (int): Timeout for the test request.
- **Outputs:** Returns `Tuple[bool, float]`: `True` and response time on success, `False` and 0 on failure. Logs test results.

##### **`test_all_proxies(self)`**
- **Purpose:** Iterates through all configured proxies, tests each one using `test_proxy`, and updates their status (failed/successful) in `self.failed_proxies` and `self.proxy_stats`. Clears `self.failed_proxies` before starting.
- **Inputs:** Uses `self.proxies`.
- **Outputs:** Updates `self.failed_proxies` and `self.proxy_stats`. Logs overall testing progress.

##### **`get_proxy_stats(self) -> Dict`**
- **Purpose:** Provides a summary of proxy statistics.
- **Inputs:** Uses `self.proxies`, `self.failed_proxies`, `self.current_proxy_index`, `self.proxy_stats`.
- **Outputs:** Returns `Dict`: A dictionary containing total proxies, failed proxies count, current proxy index, and detailed stats for each proxy.
