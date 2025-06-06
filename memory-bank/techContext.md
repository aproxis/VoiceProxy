# Technical Context

## Technologies Used:
- **Python:** The primary programming language.
- **PyQt5:** The GUI framework used for `tts_gui.py`.
- **ElevenLabs API:** The core Text-to-Speech (TTS) service used for voice generation.
- **Pandas:** Used for reading and processing Excel (`.xlsx`) and CSV (`.csv`) files.
- **Requests:** Used for making HTTP requests to the ElevenLabs API.
- **CSV/Excel:** Used for input data (text to convert) and configuration (API keys).
- **QMediaPlayer (PyQt5.QtMultimedia):** Used for playing audio previews within the GUI.

## Development Setup:
- **Python 3.6+:** Required Python version.
- **Required Python Packages:** `requests`, `pandas`, `PyQt5`. These need to be installed via `pip`.
- **API Keys:** ElevenLabs API keys are essential for the system to function, stored in `BASE.csv`.
- **Proxy Configuration:** Optional, but requires settings to be configured in the GUI or `tts_modules/config.py`.

## Technical Constraints:
- **ElevenLabs API Rate Limits:** Managed by API key rotation and caching.
- **Plain Text Credentials:** API keys and proxy credentials are still stored in plain text in `BASE.csv`, which is a security concern.
- **Input Format:** Limited to text from Excel files (specifically column B).
- **Single Language Processing:** The core processing logic likely still processes one language (Excel sheet) at a time.
- **Audio Quality:** Dependent on the ElevenLabs API and chosen voice models.

## Dependencies:
- The `tts_gui.py` application depends on:
    - `tts_modules/config.py` for configuration.
    - `tts_modules/processor.py` for core TTS logic.
    - `tts_modules/proxy_manager.py` for proxy handling.
    - `tts_modules/api_key_manager.py` for API key management.
    - `tts_modules/voice_manager.py` for voice management.
- The core logic (`tts_modules/processor.py`) depends on `requests` and `pandas`.
- Audio playback depends on `PyQt5.QtMultimedia`.

## Tool Usage Patterns:
- **Graphical User Interface:** Primary interaction through `tts_gui.py`.
- **Command Line Interface:** `tts_modules/cli.py` suggests command-line usage is also supported.
- **Configuration via GUI/File:** Settings can be managed through the GUI, which then updates the `TTSConfig` object.
- **File-based Data Management:** Input text and API keys are managed through Excel and CSV files.
