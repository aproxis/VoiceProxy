# Analysis of `tts_modules/processor.py`

### **Core Purpose and Logic:**

This script serves as the central processing unit for the VoiceProxy application. It orchestrates the entire text-to-speech conversion workflow, from loading text data and managing API keys/proxies to making ElevenLabs API calls, handling responses, and merging generated audio files. It also provides utility functions for command-line argument parsing, sample configuration creation, and proxy testing.

### **`TTSProcessor` Class**

#### **Core Purpose and Logic:**
The `TTSProcessor` class encapsulates the main business logic for converting text to speech. It manages the configuration, interacts with API key management, proxy rotation, and voice management components, and handles the iterative process of reading text, splitting it into chunks, sending it to the ElevenLabs API, and saving the resulting audio. It also implements retry mechanisms and error handling for API calls.

#### **Internal and External Dependencies:**
- **Internal Dependencies (Classes/Modules):**
    - `TTSConfig` (from `.config`): For application-wide configuration settings.
    - `ProxyRotator` (from `.proxy_manager`): For managing and rotating proxies used for API calls.
    - `APIKeyManager` (from `.api_key_manager`): For managing ElevenLabs API keys, including selection, rotation, and token balance updates.
    - `VoiceManager` (from `.voice_manager`): For managing ElevenLabs voices (standard, library, shared).
- **External Dependencies (Libraries):**
    - `logging`: For logging messages.
    - `pandas`: For reading Excel and CSV files.
    - `re`: For regular expression operations (sentence splitting).
    - `subprocess`: For executing external commands (like `ffmpeg` for audio merging).
    - `time`: For delays and timeouts.
    - `os`: For file system operations.
    - `requests`: For making HTTP requests to the ElevenLabs API.
    - `pathlib.Path`: For object-oriented file path manipulation.

#### **Inputs and Outputs:**

##### **`__init__(self, config: TTSConfig)`**
- **Inputs:**
    - `config` (TTSConfig): An instance of the configuration class containing all necessary settings (file paths, API settings, proxy settings, etc.).
- **Outputs:** Initializes `self.config`, `self.proxy_rotator`, `self.api_manager`, `self.voice_manager`, and `self.request_count`.

##### **`text_to_speech(self, api_key: str, text: str, output_file_path: Path, voice_id: str, model_id: str, public_owner_id: Optional[str] = None, similarity: float = 0.75, stability: float = 0.50) -> str`**
- **Purpose:** Sends a text chunk to the ElevenLabs API for speech synthesis. Includes retry logic and proxy rotation.
- **Inputs:**
    - `api_key` (str): The ElevenLabs API key to use for the request.
    - `text` (str): The text to convert to speech.
    - `output_file_path` (Path): The file path where the generated MP3 audio will be saved.
    - `voice_id` (str): The ID of the voice to use for synthesis.
    - `model_id` (str): The ID of the ElevenLabs model to use (e.g., "eleven_multilingual_v2").
    - `public_owner_id` (Optional[str]): Optional ID for shared voices.
    - `similarity` (float): Voice setting for similarity boost.
    - `stability` (float): Voice setting for stability.
- **Outputs:**
    - Returns `str`: "success" on successful audio generation, "quota_exceeded", "voice_limit_reached", "proxy_abuse_detected", "critical_error", or "error" based on API response or network issues.
    - **File Output:** Writes an MP3 audio file to `output_file_path`.
    - **API Calls:** Makes POST requests to `https://api.us.elevenlabs.io/v1/text-to-speech/{voice_id}`.

##### **`get_starting_row(self) -> int`**
- **Purpose:** Determines the starting row for processing based on existing numbered MP3 files in the output directory, enabling auto-resumption.
- **Inputs:** None (uses `self.config.output_directory`).
- **Outputs:** Returns `int`: The next available number for an output file (e.g., if `1.mp3` and `2.mp3` exist, returns 3).

##### **`load_text_data(self, language: str) -> Tuple[Optional[pd.DataFrame], bool]`**
- **Purpose:** Loads text data from a specified sheet in the Excel input file.
- **Inputs:**
    - `language` (str): The name of the Excel sheet to read (corresponds to language).
- **Outputs:** Returns `Tuple[Optional[pd.DataFrame], bool]`: A pandas DataFrame containing the text data (from column B) and a boolean indicating success.
    - **File Input:** Reads `self.config.xlsx_file_path`.

##### **`process_texts(self, language: str)`**
- **Purpose:** The main processing loop. It loads text, splits it into sentences, chunks sentences based on character limits, processes each chunk, and merges the resulting audio files.
- **Inputs:**
    - `language` (str): The language/sheet name to process.
- **Outputs:**
    - **File Output:** Creates individual MP3 files for chunks (e.g., `1_0.mp3`, `1_1.mp3`) and then a merged MP3 file for each original row (e.g., `1.mp3`).
    - **API Calls:** Indirectly triggers `text_to_speech` calls.
    - **Logging:** Extensive logging of progress, warnings, and errors.

##### **`_split_text_into_sentences(self, text: str) -> List[str]`**
- **Purpose:** Splits a given text into individual sentences using regular expressions.
- **Inputs:**
    - `text` (str): The input text.
- **Outputs:** Returns `List[str]`: A list of strings, where each string is a sentence.

##### **`_process_chunk(self, api_key_manager: APIKeyManager, voice_manager: VoiceManager, text_to_speech_func, config: TTSConfig, chunk_text: str, chunk_chars: int, output_file_path: Path)`**
- **Purpose:** Helper function to process a single chunk of text. It handles API key selection, voice selection (standard, library, shared), and calls the `text_to_speech` function. It also manages API key token balances and voice cleanup for library voices.
- **Inputs:**
    - `api_key_manager` (APIKeyManager): Instance of the API key manager.
    - `voice_manager` (VoiceManager): Instance of the voice manager.
    - `text_to_speech_func` (callable): Reference to the `text_to_speech` method.
    - `config` (TTSConfig): The configuration object.
    - `chunk_text` (str): The text chunk to process.
    - `chunk_chars` (int): Number of characters in the chunk (used for token management).
    - `output_file_path` (Path): Path to save the audio for this chunk.
- **Outputs:**
    - **API Calls:** Indirectly triggers `text_to_speech` calls.
    - **Logging:** Logs processing details, warnings, and errors.
    - Updates API key token balances via `api_key_manager`.
    - Adds/deletes library voices via `voice_manager`.

##### **`_merge_audio_files(self, original_row_number: int)`**
- **Purpose:** Merges all intermediate MP3 files generated for a single original Excel row into one final MP3 file using `ffmpeg`, then cleans up the intermediate files.
- **Inputs:**
    - `original_row_number` (int): The row number from the Excel file.
- **Outputs:**
    - **File Input:** Reads intermediate MP3 files (e.g., `1_0.mp3`, `1_1.mp3`).
    - **File Output:** Creates a single merged MP3 file (e.g., `1.mp3`).
    - **File Deletion:** Deletes intermediate MP3 files and the `ffmpeg` concat list.
    - **External Command Execution:** Executes `ffmpeg` command.

### **Helper Functions (Outside `TTSProcessor` Class)**

#### **`test_proxy_connection(proxy_rotator: ProxyRotator)`**
- **Core Purpose and Logic:** Tests the connectivity of configured proxies.
- **Internal Dependencies:** `ProxyRotator`.
- **Inputs:**
    - `proxy_rotator` (ProxyRotator): An instance of the proxy rotator.
- **Outputs:** Returns `bool`: `True` if at least one working proxy is found or no proxies are configured, `False` otherwise. Logs proxy test results.

#### **`create_sample_proxy_config()`**
- **Core Purpose and Logic:** Creates a sample `proxies.csv` file with example proxy configurations if it doesn't already exist.
- **Inputs:** None.
- **Outputs:**
    - **File Output:** Creates `proxies.csv` if not present.
    - **Logging:** Logs file creation.

#### **`create_sample_api_config()`**
- **Core Purpose and Logic:** Creates a sample `BASE.csv` file with example API key configurations if it doesn't already exist.
- **Inputs:** None.
- **Outputs:**
    - **File Output:** Creates `BASE.csv` if not present.
    - **Logging:** Logs file creation.

#### **`parse_arguments()`**
- **Core Purpose and Logic:** Parses command-line arguments for the script, such as language, config file path, and flags for creating samples or testing proxies.
- **External Dependencies:** `argparse`.
- **Inputs:** Command-line arguments (`sys.argv`).
- **Outputs:** Returns `argparse.Namespace`: An object containing the parsed arguments.

#### **`main()`**
- **Core Purpose and Logic:** The entry point for the command-line execution of the script. It parses arguments, handles sample file creation and proxy testing, initializes the `TTSConfig` and `TTSProcessor`, and starts the text processing.
- **Internal Dependencies:** `parse_arguments`, `create_sample_proxy_config`, `create_sample_api_config`, `TTSConfig`, `ProxyRotator`, `test_proxy_connection`, `TTSProcessor`.
- **Inputs:** Command-line arguments (via `parse_arguments`).
- **Outputs:**
    - Orchestrates the entire command-line workflow.
    - **Logging:** Logs various stages of execution.
