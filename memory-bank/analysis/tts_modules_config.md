# Analysis of `tts_modules/config.py`

### **`TTSConfig` Class**

#### **Core Purpose and Logic:**
The `TTSConfig` class serves as a centralized repository for all configuration settings required by the VoiceProxy application. It initializes default values for file paths, voice selection, API parameters, and proxy settings. This class is designed to be instantiated once and passed around to other components (like `TTSProcessor`) to ensure consistent access to configuration throughout the application.

#### **Internal and External Dependencies:**
- **Internal Dependencies:** None directly within this file, but its instances are consumed by other modules like `tts_modules/processor.py` and `tts_gui.py`.
- **External Dependencies (Libraries):**
    - `pathlib.Path`: Used for handling file and directory paths in an object-oriented manner.

#### **Inputs and Outputs:**

##### **`__init__(self)`**
- **Purpose:** Initializes all configuration attributes with their default values.
- **Inputs:** None (all values are hardcoded defaults within the constructor).
- **Outputs:** An instance of `TTSConfig` with populated attributes.

##### **Attributes (Accessed as Inputs by other modules):**

- **File Paths:**
    - `csv_file_path` (Path): Path to the CSV file containing API keys (default: `/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/BASE.csv`).
    - `output_directory` (Path): Path to the directory where generated audio files will be saved (default: `/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/Audio`).
    - `xlsx_file_path` (Path): Path to the Excel file containing text data for conversion (default: `/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/Base.xlsx`).
    - `proxies_file` (Path): Path to the CSV file containing proxy configurations (default: `/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/proxies.csv`).
    - `cache_dir` (Path): Directory for caching voice data and previews (default: `/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/cache/voices`).

- **Voice Settings:**
    - `voice_selection_mode` (str): Determines how voices are selected ("standard", "library", or "shared") (default: "standard").
    - `standard_voice_id` (str): Default ElevenLabs voice ID for standard voice mode (default: "nPczCjzI2devNBz1zQrb").
    - `selected_language` (str): Selected language for the voice (default: "en").
    - `selected_model_id` (str): Selected model ID for the language (default: "eleven_multilingual_v2").
    - `original_voice_id` (str): ID of the original voice from the library for library voice mode (default: "repzAAjoKlgcT2oOAIWt").
    - `public_owner_id` (str): Public owner ID for the library voice (default: "6448d1215d14246fd2c38cdaff7e8840c0396b21d8a84ab77f2fe9cca89409fa").

- **Shared Voice Search Settings:**
    - `shared_voice_gender` (str): Filter for shared voice search (default: "").
    - `shared_voice_language` (str): Filter for shared voice search (default: "").
    - `shared_voice_page_size` (int): Number of results per page for shared voice search (default: 10).
    - `selected_shared_voice_id` (str): ID of the currently selected shared voice (default: "").
    - `selected_shared_public_owner_id` (str): Public owner ID of the currently selected shared voice (default: "").
    - `selected_shared_model_id` (str): Model ID of the currently selected shared voice (default: "").

- **API Settings:**
    - `max_retries` (int): Maximum number of retry attempts for API calls (default: 3).
    - `timeout` (int): Timeout for API requests in seconds (default: 60).
    - `retry_delay` (int): Delay between retry attempts in seconds (default: 10).
    - `api_call_delay_seconds` (int): Delay between consecutive API calls in seconds (default: 1).
    - `max_chunk_chars` (int): Maximum characters for each audio chunk sent to the API (default: 1500).

- **Proxy Settings:**
    - `proxy_rotation_interval` (int): Number of requests after which the proxy should rotate (default: 10).
    - `proxy_test_on_startup` (bool): Whether to test proxies on application startup (default: `True`).
    - `auto_proxy_rotation` (bool): Whether to automatically rotate proxies (default: `True`).
    - `test_api_switching_mode` (bool): Flag to enable test mode for API key switching (default: `False`).
