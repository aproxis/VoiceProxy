# Product Context

## Purpose:
The `VoiceProxy` module is designed to automate the process of generating voiceovers from text data stored in Excel files, specifically leveraging the ElevenLabs API. Its core purpose is to streamline the creation of audio content for various applications, such as:
- Generating multi-language voiceovers for media or presentations.
- Automating audio content creation for large datasets.
- Providing a robust and manageable system for TTS operations with API key rotation and proxy support.

## Problems Solved:
- **Efficient Voiceover Generation:** Automates the conversion of large volumes of text from Excel into audio.
- **API Key Management:** Handles API key rotation and fallback mechanisms to manage quotas and ensure continuous operation.
- **Multi-language Support:** Facilitates processing text in different languages by organizing content in Excel sheets.
- **Proxy Integration:** Allows routing API communications through proxies for network flexibility or security.
- **Auto-resumption:** Prevents loss of progress by resuming from the last processed file.
- **Error Handling:** Provides robust mechanisms for retries and fallbacks in case of API or connection issues.

## How it Should Work:
- The user initiates the script, specifying the language (Excel sheet) to process.
- The script reads text data from the specified Excel sheet.
- It checks for existing audio files to determine the starting point for new generation.
- An available ElevenLabs API key is retrieved and managed, with rotation if quotas are exceeded.
- For each text entry, a TTS request is made to ElevenLabs (potentially via a proxy).
- The generated audio data is saved as an MP3 file in a designated output directory.
- The system handles errors gracefully, retrying or switching API keys as needed.

## User Experience Goals:
- **Automation:** Minimize manual intervention in voiceover generation.
- **Reliability:** Ensure consistent and uninterrupted audio generation, even with API limitations.
- **Flexibility:** Support various languages and allow for custom voice selection.
- **Ease of Use:** Simple command-line interface for initiating the process.
- **Progress Preservation:** Ability to resume operations seamlessly after interruptions.
