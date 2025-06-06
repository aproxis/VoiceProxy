from pathlib import Path

class TTSConfig:
    """Configuration class for TTS script"""
    def __init__(self):
        # File paths
        self.csv_file_path = Path("/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/BASE.csv")
        self.output_directory = Path("/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/Audio")
        self.xlsx_file_path = Path("/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/Base.xlsx")
        self.proxies_file = Path("/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/proxies.csv")
        self.cache_dir = Path("/Users/a/Desktop/Share/YT/Scripts/VideoCutter/VoiceProxy/cache/voices") # New: Cache directory for voices and previews
        
        # Voice settings
        self.voice_selection_mode = "standard" # "standard", "library", or "shared"
        self.standard_voice_id = "nPczCjzI2devNBz1zQrb"
        self.selected_language = "en" # New: Selected language for the voice
        self.selected_model_id = "eleven_multilingual_v2" # New: Selected model ID for the language
        self.original_voice_id = "repzAAjoKlgcT2oOAIWt"
        self.public_owner_id = "6448d1215d14246fd2c38cdaff7e8840c0396b21d8a84ab77f2fe9cca89409fa"
        
        # Shared Voice Search settings
        self.shared_voice_gender = ""
        self.shared_voice_language = ""
        self.shared_voice_page_size = 10
        self.selected_shared_voice_id = ""
        self.selected_shared_public_owner_id = ""
        self.selected_shared_model_id = ""
        
        # API settings
        self.max_retries = 3
        self.timeout = 60
        self.retry_delay = 10
        
        # Proxy settings
        self.proxy_rotation_interval = 10  # Rotate proxy every N requests
        self.proxy_test_on_startup = True
        self.auto_proxy_rotation = True
        self.test_api_switching_mode = False # New: For testing API key switching
        self.max_chunk_chars = 1500 # New: Max characters for each audio chunk
        self.api_call_delay_seconds = 1 # New: Delay between API calls in seconds
