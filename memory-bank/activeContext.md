# Active Context

## Current Work Focus:
- Detailed project understanding through code analysis.
- Generating detailed analysis for each script/class (purpose, dependencies, inputs/outputs) and saving them to `memory-bank/analysis/`.
- Updating memory bank files with validated information.

## Recent Changes:
- Completed detailed analysis of all Python scripts/classes in `tts_modules` and `tts_gui.py`.
- Completed detailed analysis of `BASE.csv` and `Base.xlsx`.
- Completed detailed analysis of `api_keys.csv` and saved to `memory-bank/analysis/api_keys_csv.md`. Confirmed it is not actively used.
- Re-created all missing analysis files in `memory-bank/analysis/` after user feedback.

## Next Steps:
- Update `progress.md`.
- Consolidate findings and prepare for potential refactoring suggestions (e.g., addressing code duplication, security concerns).
- Finalize memory bank documentation.

## Active Decisions and Considerations:
- The project is a Python-based TTS automation tool using ElevenLabs API, with both GUI (`tts_gui.py`) and CLI (`tts_modules/cli.py`) interfaces.
- Core logic is modularized within `tts_modules`.
- `VOICE_Proxy.py` and `Voice.py` are confirmed obsolete.
- Security concern: API keys and proxy credentials are stored in plain text in `BASE.csv`.
- **Code Duplication:** The `main()` function and several helper functions are duplicated between `tts_modules/processor.py` and `tts_modules/cli.py`. This should be addressed in future refactoring.

## Learnings and Project Insights:
- `README.md` provides valuable feature and architectural overview but can be outdated regarding specific file roles.
- The project has robust features for managing API usage and resuming operations.
- The use of PyQt5 for the GUI indicates a desktop application.
- `tts_modules/processor.py` is indeed the core orchestration logic, handling TTS requests, proxy rotation, API key management, and audio merging.
- `tts_modules/config.py` centralizes all application settings, making them easily configurable and accessible throughout the application.
- `tts_modules/api_key_manager.py` provides robust API key management, including token tracking, rotation, and handling of various API-related errors.
- `tts_modules/voice_manager.py` handles all ElevenLabs voice-related operations, including fetching, searching, managing library voices, and caching previews.
- `tts_modules/proxy_manager.py` provides a comprehensive proxy management system, including loading from CSV/env, rotation, health checks, and statistics.
- `tts_modules/cli.py` is the dedicated command-line interface, despite some code duplication.
- `tts_gui.py` is the main GUI application, providing a user-friendly interface for configuring and running the TTS process, utilizing worker threads for responsiveness.
- `BASE.csv` is the active API key storage, confirming the security concern of plain text credentials.
- `Base.xlsx` is the primary input for text data, supporting multi-language processing via sheets and expecting text in column B.
- `api_keys.csv` appears to be an unused or obsolete file.
