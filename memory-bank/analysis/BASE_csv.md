# Analysis for `BASE.csv`

### **Core Purpose and Logic:**
`BASE.csv` serves as the persistent storage for ElevenLabs API keys used by the VoiceProxy application. It's crucial for the API key rotation and management system implemented in `tts_modules/api_key_manager.py`. This file allows the application to track the usage, token balance, and status of multiple API keys, enabling it to switch keys when quotas are exceeded or issues arise.

### **Structure and Fields:**
The file is a comma-separated values (CSV) file with the following columns:

-   **`API`**:
    -   **Purpose:** Stores the actual ElevenLabs API key string.
    -   **Format:** String (e.g., `sk_806ffee74c432655f0....29b8f9e3368ae7`).
    -   **Example Value:** `sk_806ffee74c432655f0....29b8f9e3368ae7`

-   **`Date`**:
    -   **Purpose:** Stores the last known usage date of the API key. This field's format (`DD.MM.YYYY`) suggests it might be a legacy field or used for human readability, as `last_checked` provides a more precise timestamp.
    -   **Format:** String, `DD.MM.YYYY`.
    -   **Example Value:** `05.06.2025`

-   **`available_tokens`**:
    -   **Purpose:** Stores the number of available characters (tokens) remaining for the API key's quota. This value is updated by `APIKeyManager` after each usage and periodically refreshed from the ElevenLabs API.
    -   **Format:** Integer.
    -   **Example Value:** `9640`

-   **`last_checked`**:
    -   **Purpose:** Stores the timestamp of the last time the API key's token balance was checked or updated. This is used by `APIKeyManager` to determine when a refresh is needed.
    -   **Format:** ISO 8601 formatted string (e.g., `YYYY-MM-DDTHH:MM:SS.ffffff`).
    -   **Example Value:** `2025-06-06T18:00:47.302250`

-   **`is_exhausted`**:
    -   **Purpose:** A boolean flag indicating whether the API key is currently considered exhausted (e.g., 0 available tokens or marked as such due to API errors). This helps `APIKeyManager` avoid trying keys that are known to be unusable.
    -   **Format:** Boolean string (`True` or `False`).
    -   **Example Value:** `False`

### **Dependencies and Usage:**
-   **Used by:** `tts_modules/api_key_manager.py` (specifically the `APIKeyManager` class).
-   **Usage:**
    -   `APIKeyManager` reads this file on initialization (`_load_api_keys`).
    -   `APIKeyManager` writes back to this file after updating token balances, `last_checked` timestamps, and `is_exhausted` flags (`_save_api_keys_to_csv`).
    -   The `create_sample_api_config()` function (found in `tts_modules/processor.py` and `tts_modules/cli.py`) can generate a sample `BASE.csv` if it doesn't exist.

### **Security Considerations:**
-   **Plain Text Storage:** API keys are stored in plain text within this CSV file. This is a significant security vulnerability, as anyone with access to the file can use the API keys. For production environments, a more secure method of storing sensitive credentials (e.g., environment variables, a secure vault, or encrypted configuration files) should be implemented.
