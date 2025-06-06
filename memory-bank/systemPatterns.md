# System Patterns

## System Architecture:
The `VoiceProxy` module is designed with a clear component-based architecture.

- **Main Entry Points:**
    - `tts_gui.py`: The primary graphical user interface (GUI) application.
    - `tts_modules/cli.py`: Likely provides a command-line interface for the core functionality.
- **Input Sources:** `Base.xlsx` (text data, multi-language sheets) and `BASE.csv` (API keys).
- **Core Components (within `tts_modules`):**
    - `tts_modules/processor.py`: The central component responsible for orchestrating TTS generation, interacting with other modules.
    - `tts_modules/api_key_manager.py`: Handles API key rotation, quota tracking, and fallback.
    - `tts_modules/voice_manager.py`: Manages standard and ElevenLabs library voices, including fetching voice data and previews.
    - `tts_modules/proxy_manager.py`: Manages proxy settings and rotation for API communications.
    - `tts_modules/config.py`: Manages application configuration settings.
- **Output:** Generated audio files (`.mp3`) stored in the `Audio/` directory.
- **Caching:** `cache/voices` directory is used for caching voice preview MP3s and potentially other voice-related data.

## Key Technical Decisions:
- **Python-based:** The entire system is implemented in Python, utilizing PyQt5 for the GUI.
- **ElevenLabs API:** Primary TTS service provider.
- **Excel/CSV for Data:** Input text from Excel, API keys from CSV.
- **Modular Design:** Strong separation of concerns into distinct Python modules within `tts_modules`.
- **Proxy Support:** Built-in proxy integration for API calls.
- **Auto-resumption:** Logic to continue processing from the last generated file.
- **Asynchronous Operations:** Use of `QThread` for long-running tasks in the GUI to prevent freezing.

## Design Patterns in Use:
- **Module Pattern:** Code organized into logical modules (`tts_modules`).
- **Configuration Pattern:** External configuration managed by `tts_modules/config.py`.
- **Worker Thread Pattern:** `Worker` class in `tts_gui.py` for offloading heavy tasks.
- **Retry/Fallback Pattern:** Implemented for API errors, connection timeouts, and proxy errors.
- **Caching Pattern:** Storing frequently accessed data (audio files, voice previews) for quicker retrieval.

## Component Relationships:
- `tts_gui.py` (or `tts_modules/cli.py`) initializes `TTSProcessor` from `tts_modules/processor.py`.
- `TTSProcessor` orchestrates calls to `APIKeyManager`, `VoiceManager`, and `ProxyRotator` (from `tts_modules`).
- `APIKeyManager` reads from `BASE.csv`.
- `VoiceManager` interacts with the ElevenLabs API and manages the `cache/voices` directory.
- `ProxyRotator` handles proxy settings and testing.
- The system reads text from `Base.xlsx` and writes audio to `Audio/`.

## Critical Implementation Paths:
- **TTS Generation Flow (GUI):** User configures settings in GUI -> Clicks "Process Texts" -> `TTSProcessor` reads Excel, gets API key, selects voice -> Makes TTS request to ElevenLabs (via proxy) -> Audio data returned -> Audio saved to file.
- **API Key Rotation:** If ElevenLabs returns a quota error, `APIKeyManager` provides a new key.
- **Voice Selection Logic:** Dynamic handling of standard, library, and shared voices, including fetching and caching previews.
- **Error Handling:** Robust mechanisms for retries, key rotation, and user feedback via logs.
