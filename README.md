# VoiceProxy Module

## Overview

The `VoiceProxy` module is a robust Python-based application designed for automated text-to-speech (TTS) conversion using the ElevenLabs API. It provides both a Graphical User Interface (GUI) and a Command Line Interface (CLI) to manage the generation of voiceovers from text data, primarily sourced from Excel files. The system features advanced capabilities such as API key rotation, proxy integration, dynamic voice selection (standard, library, and shared voices), and intelligent audio file management with auto-resumption.

## Features

-   **Multi-language Support**: Process text from different language-specific sheets within an Excel input file.
-   **API Key Rotation**: Automatic management of ElevenLabs API keys, including token quota tracking and a fallback mechanism to ensure continuous operation.
-   **Voice Management**: Comprehensive support for ElevenLabs voices, including fetching standard voices, searching and using shared voices, and managing custom library voices (adding/deleting).
-   **Proxy Integration**: Built-in support for routing all API communications through configured HTTP/HTTPS proxies, with health checking and rotation.
-   **Auto-resumption**: Seamlessly continues audio generation from the last processed entry, preventing data loss and re-processing.
-   **Error Handling**: Robust error management with configurable retries, delays, and intelligent handling of API-specific errors (e.g., quota exceeded, voice limit reached).
-   **Modular Design**: Core functionalities are separated into distinct Python modules for maintainability and extensibility.
-   **GUI and CLI**: Offers both an intuitive graphical interface for easy configuration and operation, and a command-line interface for automated workflows.

## Architecture

The VoiceProxy application follows a modular architecture, with core logic encapsulated in `tts_modules` and distinct entry points for GUI and CLI interactions.

### Component Diagram (ASCII)

```
+-----------------+       +-----------------+       +-----------------+
|                 |       |                 |       |                 |
|   Input Files   |       |   Core Modules  |       |   Output/Cache  |
|                 |       |                 |       |                 |
+-----------------+       +-----------------+       +-----------------+
         |                         |                         |
         v                         v                         v
+-----------------------------------------------------------------------+
|                                                                       |
|  +-----------------+    +-----------------+    +-----------------+    |
|  |   Base.xlsx     |    |   TTSProcessor  |    |   Audio/        |    |
|  | (Text Data)     |    | (Orchestration) |    | (Generated MP3s)|    |
|  +-----------------+    +-----------------+    +-----------------+    |
|         |                      ^ |                      ^             |
|         |                      | |                      |             |
|  +-----------------+    +-----------------+    +-----------------+    |
|  |   BASE.csv      |    |  APIKeyManager  |    |   cache/voices  |    |
|  | (API Keys)      |    | (Key Rotation)  |    | (Voice Previews)|    |
|  +-----------------+    +-----------------+    +-----------------+    |
|         |                      ^ |                      ^             |
|         |                      | |                      |             |
|  +-----------------+    +-----------------+    +-----------------+    |
|  |   proxies.csv   |    |  VoiceManager   |    |                 |    |
|  | (Proxy Config)  |    | (Voice Handling)|    |                 |    |
|  +-----------------+    +-----------------+    +-----------------+    |
|                                ^ |                                      |
|                                | |                                      |
|  +-----------------+    +-----------------+                             |
|  |   TTSConfig     |    |  ProxyRotator   |                             |
|  | (Configuration) |    | (Proxy Handling)|                             |
|  +-----------------+    +-----------------+                             |
|                                                                       |
+-----------------------------------------------------------------------+
         ^                         ^
         |                         |
+-----------------+       +-----------------+
|                 |       |                 |
|   tts_gui.py    |       |   tts_modules/  |
|   (GUI Entry)   |       |     cli.py      |
|                 |       |   (CLI Entry)   |
+-----------------+       +-----------------+
```

### Process Flow (ASCII)

```
+-----------------+
|      User       |
+-----------------+
         |
         v
+-----------------------------------------------------------------------+
|                                                                       |
|  Application Startup (GUI: tts_gui.py / CLI: tts_modules/cli.py)      |
|  +-----------------+  +-----------------+  +-----------------+        |
|  | Load Config     |->| Init Managers   |->| Test Proxies    |        |
|  | (TTSConfig)     |  | (API, Voice,    |  | (if enabled)    |        |
|  |                 |  | Proxy)          |  |                 |        |
|  +-----------------+  +-----------------+  +-----------------+        |
|                                                                       |
+-----------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------+
|                                                                       |
|  Text Processing Loop (TTSProcessor.process_texts)                    |
|  +-----------------+  +-----------------+  +-----------------+        |
|  | Load Text Data  |->| Get Starting    |->| Iterate Text    |        |
|  | (Base.xlsx)     |  | Row (Auto-Res.) |  | Rows            |        |
|  +-----------------+  +-----------------+  +-----------------+        |
|                                |                                      |
|                                v                                      |
|  +-----------------------------------------------------------------+  |
|  |  For Each Text Row:                                             |  |
|  |  +-----------------+  +-----------------+  +-----------------+  |  |
|  |  | Split into      |->| Chunk Sentences |->| For Each Chunk: |  |  |
|  |  | Sentences       |  | (max_chunk_chars)|  |                 |  |  |
|  |  +-----------------+  +-----------------+  +-----------------+  |  |
|  |                                |                                |  |
|  |                                v                                |  |
|  |  +------------------------------------------------------------+  |  |
|  |  |  Process Chunk (TTSProcessor._process_chunk)             |  |  |
|  |  |  +-----------------+  +-----------------+  +-----------+ |  |  |
|  |  |  | Get API Key     |->| Select Voice    |->| Make TTS  | |  |  |
|  |  |  | (APIKeyManager) |  | (VoiceManager)  |  | Request   | |  |  |
|  |  |  +-----------------+  +-----------------+  | (ElevenLabs)| |  |  |
|  |  |          |                    |            | (via Proxy) | |  |  |
|  |  |          v                    v            +-----------+ |  |  |
|  |  |  +-----------------+  +-----------------+        |        |  |  |
|  |  |  | Handle API      |  | Update Token    |        v        |  |  |
|  |  |  | Response (Retry,|  | Balance         |<-------+        |  |  |
|  |  |  | Quota, Error)   |  |                 |                 |  |  |
|  |  |  +-----------------+  +-----------------+                 |  |  |
|  |  |                                                           |  |  |
|  |  +------------------------------------------------------------+  |  |
|  |                                                                 |  |
|  |  +-----------------+                                            |  |
|  |  | Merge Audio     |                                            |  |
|  |  | Files (ffmpeg)  |                                            |  |
|  |  +-----------------+                                            |  |
|  |                                                                 |  |
|  +-----------------------------------------------------------------+  |
|                                                                       |
+-----------------------------------------------------------------------+
         |
         v
+-----------------+
|  Processing     |
|  Complete       |
+-----------------+
```

## Installation

### Prerequisites

-   Python 3.6+
-   Required Python packages:
    ```
    PyQt5
    requests
    pandas
    ```
-   `ffmpeg` (for merging audio files)

### Setup

1.  Clone the repository or download the script files.
2.  Install required Python packages:
    ```bash
    pip install PyQt5 requests pandas
    ```
3.  Ensure `ffmpeg` is installed and accessible in your system's PATH.
4.  Prepare your input files:
    *   **`Base.xlsx`**: Excel file with text to convert. Each sheet represents a language, and text should be in column B.
    *   **`BASE.csv`**: CSV file containing ElevenLabs API keys. Refer to `tts_modules/api_key_manager.py` for expected format (`API`, `Date`, `available_tokens`, `last_checked`, `is_exhausted`).
    *   **`proxies.csv` (Optional)**: CSV file for proxy configurations. Refer to `tts_modules/proxy_manager.py` for expected format (`ip`, `port`, `login`, `password`, `type`).

## Configuration

Configuration settings are primarily managed through the `tts_modules/config.py` file and can be adjusted via the GUI.

Key configurable parameters include:
-   **File Paths**: Paths to `BASE.csv`, `Base.xlsx`, output directory, and `proxies.csv`.
-   **Voice Settings**: Default voice IDs, language, model IDs, and settings for library/shared voices.
-   **API Settings**: Max retries, timeouts, retry delays, API call delays, and max characters per chunk.
-   **Proxy Settings**: Proxy rotation interval, auto-rotation, and startup testing.

**Note:** API keys and proxy credentials are currently stored in plain text within `BASE.csv` and `proxies.csv`. For production environments, consider implementing more secure credential management.

## File Structure

```
.
├── Audio/                      # Output directory for generated MP3 files
├── BASE.csv                    # Stores ElevenLabs API keys and their usage data
├── Base.xlsx                   # Input Excel file with text for TTS conversion
├── cache/
│   └── voices/                 # Cache for ElevenLabs voice data and preview MP3s
├── memory-bank/                # Documentation and analysis files
│   ├── activeContext.md
│   ├── analysis/               # Detailed analysis of code and data files
│   │   ├── BASE_csv.md
│   │   ├── Base_xlsx.md
│   │   ├── api_keys_csv.md     # Analysis of an unused/obsolete API keys file
│   │   ├── tts_gui.md
│   │   ├── tts_modules_api_key_manager.md
│   │   ├── tts_modules_cli.md
│   │   ├── tts_modules_config.md
│   │   ├── tts_modules_processor.md
│   │   └── tts_modules_voice_manager.md
│   ├── productContext.md
│   ├── progress.md
│   ├── projectbrief.md
│   ├── systemPatterns.md
│   └── techContext.md
├── proxies.csv                 # (Optional) Stores proxy configurations
├── README.md                   # This documentation file
├── tts_gui.py                  # Main script for the Graphical User Interface (GUI)
├── tts_modules/                # Core modules for TTS processing
│   ├── api_key_manager.py      # Manages ElevenLabs API keys
│   ├── cli.py                  # Command-line interface entry point
│   ├── config.py               # Centralized configuration settings
│   ├── processor.py            # Core TTS processing logic and orchestration
│   ├── proxy_manager.py        # Manages proxy rotation and health checking
│   └── voice_manager.py        # Manages ElevenLabs voice operations
└── VOICE_Proxy.py              # (Obsolete) Old main script with proxy support
└── Voice.py                    # (Obsolete) Old alternative script without proxy support
```

## Usage

### Graphical User Interface (GUI)

Run the GUI application:

```bash
python tts_gui.py
```

The GUI provides fields to configure file paths, voice settings, API parameters, and proxy settings. You can then initiate text processing, test proxies, or clear the output directory.

### Command Line Interface (CLI)

Run the CLI script with desired arguments:

```bash
python tts_modules/cli.py --lang RU
```

**Arguments:**
-   `--lang <LANGUAGE_CODE>`: Specifies the Excel sheet (language) to process (e.g., `RU`, `EN`). Defaults to `RU`.
-   `--create-samples`: Creates sample `proxies.csv` and `BASE.csv` files if they don't exist.
-   `--test-proxies`: Tests proxy connections only.
-   `--test-api-switching`: Enables a test mode for API switching (artificially reduces tokens to force key rotation).

## Error Handling

The application includes robust error handling mechanisms:
-   **API Quota Exceeded**: Automatically switches to the next available API key.
-   **Connection Timeouts**: Retries API requests with configurable delays.
-   **Proxy Errors**: Marks problematic proxies as failed, rotates to a new proxy, and retries.
-   **Voice Limit Reached**: Marks the API key as having reached its voice creation limit and attempts to use another key.
-   **Critical Errors**: Logs detailed error messages and terminates execution if unrecoverable.

## Technical Details

### API Key Management

API keys are stored in `BASE.csv` along with their available token balance and last checked timestamp. The `APIKeyManager` selects keys with sufficient tokens, refreshes balances periodically, and rotates to new keys upon quota exhaustion or voice limit issues.

### Voice Selection Logic

The `VoiceManager` handles three modes of voice selection:
1.  **Standard Voices**: Fetches and caches voices available to the user's ElevenLabs account.
2.  **Library Voices**: Allows adding a voice from the ElevenLabs public library to the user's account for use, cleaning up non-premade voices as needed.
3.  **Shared Voices**: Searches and uses voices from the ElevenLabs shared voice marketplace, with caching of previews.

### File Naming and Resumption

The `TTSProcessor` automatically detects existing audio files in the output directory (`Audio/`) and continues numbering from the highest existing file number. This enables seamless resumption of processing after interruptions. Intermediate audio files (for individual sentences/chunks) are merged into a single file per original text entry and then deleted.

## Limitations

-   **Plain Text Credentials**: API keys and proxy credentials are stored in plain text in `BASE.csv` and `proxies.csv`, posing a security risk.
-   **Hardcoded File Paths**: Default file paths are hardcoded in `tts_modules/config.py`, requiring manual modification or GUI interaction for changes.
-   **Input Format Dependency**: Currently only supports text input from Excel files (specifically column B).
-   **Code Duplication**: Utility functions and the `main` entry point are duplicated between `tts_modules/processor.py` and `tts_modules/cli.py`.
-   **Single Language Processing**: The CLI processes only one language (Excel sheet) per run.

## Troubleshooting

-   **Proxy Connection Issues**: Verify proxy credentials and test connectivity using the "Test Proxies" button in the GUI or `--test-proxies` CLI argument.
-   **API Key Errors**: Ensure `BASE.csv` is properly formatted and contains valid, active keys with sufficient quotas. Check logs for specific ElevenLabs API error messages.
-   **Voice Selection Failures**: Verify voice IDs and account permissions. Ensure the correct voice selection mode is active in the GUI.
-   **File Access Errors**: Check configured file paths and directory permissions for input, output, and cache directories.
-   **`ffmpeg` Not Found**: Ensure `ffmpeg` is installed and its executable path is included in your system's PATH environment variable.
