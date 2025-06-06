import json
from pathlib import Path

CONFIG_FILE = Path("config.json")

class TTSConfig:
    """Configuration class for TTS script"""
    def __init__(self):
        # Default values
        self.csv_file_path = Path("BASE.csv")
        self.output_directory = Path("Audio")
        self.xlsx_file_path = Path("Base.xlsx")
        self.proxies_file = Path("proxies.csv")
        self.cache_dir = Path("cache/voices")
        
        self.voice_selection_mode = "standard"
        self.standard_voice_id = "nPczCjzI2devNBz1zQrb"
        self.selected_language = "en"
        self.selected_model_id = "eleven_multilingual_v2"
        self.original_voice_id = "repzAAjoKlgcT2oOAIWt"
        self.public_owner_id = "6448d1215d14246fd2c38cdaff7e8840c0396b21d8a84ab77f2fe9cca89409fa"
        
        self.shared_voice_gender = ""
        self.shared_voice_language = ""
        self.shared_voice_page_size = 10
        self.selected_shared_voice_id = ""
        self.selected_shared_public_owner_id = ""
        self.selected_shared_model_id = ""
        
        self.max_retries = 3
        self.timeout = 60
        self.retry_delay = 10
        self.proxy_rotation_interval = 10
        self.proxy_test_on_startup = True
        self.auto_proxy_rotation = True
        self.test_api_switching_mode = False
        self.max_chunk_chars = 1500
        self.api_call_delay_seconds = 1

        self._load_from_json()

    def _load_from_json(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                for key, value in settings.items():
                    if hasattr(self, key):
                        # Convert paths back to Path objects
                        if key in ['csv_file_path', 'output_directory', 'xlsx_file_path', 'proxies_file', 'cache_dir']:
                            setattr(self, key, Path(value))
                        else:
                            setattr(self, key, value)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {CONFIG_FILE}. Using default settings.")
            except Exception as e:
                print(f"An error occurred loading config from {CONFIG_FILE}: {e}. Using default settings.")
        else:
            self.save_to_json() # Create config.json with default values if it doesn't exist

    def save_to_json(self):
        settings = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'): # Exclude private attributes
                # Convert Path objects to strings for JSON serialization
                if isinstance(value, Path):
                    settings[key] = str(value)
                else:
                    settings[key] = value
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config to {CONFIG_FILE}: {e}")
