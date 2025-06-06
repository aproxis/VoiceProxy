import logging
import pandas as pd
import re
import subprocess
import time
import os
import requests
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from .config import TTSConfig
from .proxy_manager import ProxyRotator
from .api_key_manager import APIKeyManager
from .voice_manager import VoiceManager

logger = logging.getLogger(__name__)

class TTSProcessor:
    """Main text-to-speech processing class"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.proxy_rotator = ProxyRotator(config.proxies_file) # Initialize here to pass to APIKeyManager
        self.api_manager = APIKeyManager(config.csv_file_path, self.proxy_rotator, config) # Pass config here
        self.voice_manager = VoiceManager(config, self.proxy_rotator)
        self.request_count = 0
        
    def text_to_speech(self, api_key: str, text: str, output_file_path: Path, 
                      voice_id: str, model_id: str, public_owner_id: Optional[str] = None,
                      similarity: float = 0.75, stability: float = 0.50) -> str:
        """Convert text to speech with retry logic and proxy rotation"""
        url = f"https://api.us.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        json_data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "similarity_boost": similarity,
                "stability": stability
            }
        }

        if public_owner_id:
            json_data["public_owner_id"] = public_owner_id
        
        
        # Auto-rotate proxy based on interval
        if (self.config.auto_proxy_rotation and 
            self.request_count > 0 and 
            self.request_count % self.config.proxy_rotation_interval == 0):
            self.proxy_rotator.rotate_proxy()
            
        for attempt in range(self.config.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1} of {self.config.max_retries}")
                
                current_proxy = self.proxy_rotator.get_current_proxy()
                start_time = time.time()
                
                # Add configurable delay before API call
                time.sleep(self.config.api_call_delay_seconds)

                response = requests.post(
                    url, headers=headers, json=json_data,
                    proxies=current_proxy, timeout=self.config.timeout
                )
                
                response_time = time.time() - start_time
                self.request_count += 1
                
                if response.status_code == 200:
                    with open(output_file_path, "wb") as audio_file:
                        audio_file.write(response.content)
                    logger.info(f"Audio saved successfully: {output_file_path}")
                    self.proxy_rotator.mark_proxy_success(response_time)
                    return "success"
                
                # Handle API errors
                try:
                    error_data = response.json()
                    error_status = error_data.get("detail", {}).get("status")
                    
                    if error_status == "detected_unusual_activity":
                        logger.warning(f"Unusual activity detected for API key {api_key[:5]}...: {error_data['detail']['message']}. Switching proxy.")
                        self.proxy_rotator.mark_proxy_failed()
                        self.proxy_rotator.rotate_proxy()
                        return "proxy_abuse_detected" # Signal to retry with new proxy
                    elif error_status == "quota_exceeded":
                        logger.warning("Quota exceeded, switching API key")
                        return "quota_exceeded"
                    elif error_status == "voice_limit_reached":
                        logger.warning(f"Voice limit reached for API key {api_key[:5]}...: {error_data['detail']['message']}. Marking key and trying next.")
                        self.api_manager.mark_voice_limit_reached(api_key)
                        return "voice_limit_reached" # Signal to retry with new API key
                    else:
                        logger.error(f"API error: {response.text}")
                        
                except ValueError:
                    logger.error(f"Invalid server response: {response.text}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Proxy/Connection error: {e} (attempt {attempt + 1})")
                self.proxy_rotator.mark_proxy_failed()
                self.proxy_rotator.rotate_proxy()
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
        
        logger.error("All retry attempts exhausted")
        return "error"
    
    def get_starting_row(self) -> int:
        """Determine starting row based on existing files"""
        if not self.config.output_directory.exists():
            return 1
            
        existing_files = list(self.config.output_directory.glob("*.mp3"))
        if not existing_files:
            return 1
            
        numbered_files = []
        for file in existing_files:
            try:
                num = int(file.stem)
                numbered_files.append(num)
            except ValueError:
                continue
                
        return max(numbered_files, default=0) + 1
    
    def load_text_data(self, language: str) -> Tuple[Optional[pd.DataFrame], bool]:
        """Load text data from Excel file"""
        try:
            excel_file = pd.ExcelFile(self.config.xlsx_file_path)
            
            if language not in excel_file.sheet_names:
                logger.error(f"Sheet '{language}' not found in Excel file")
                logger.info(f"Available sheets: {excel_file.sheet_names}")
                return None, False
            # Read specific sheet (--lang code in query param) and use column B (second column in Excel)
            df = pd.read_excel(excel_file, sheet_name=language, header=None, usecols=[1])
            logger.info(f"Loaded {len(df)} rows from sheet '{language}'")
            return df, True
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            return None, False
    
    def process_texts(self, language: str):
        """Main processing loop with sentence splitting and token management."""
        df, success = self.load_text_data(language)
        if not success or df is None:
            return
        
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        starting_row = self.get_starting_row()
        
        logger.info(f"Starting processing from row {starting_row}")
        
        # Iterate through each row (original text entry)
        for original_row_index in range(starting_row - 1, len(df)):
            original_text = str(df.iloc[original_row_index][1]).strip()
            
            logger.debug(f"Processing original text for row {original_row_index + 1}: '{original_text}'")

            if not original_text or original_text.lower() == 'nan':
                logger.info(f"Skipping empty or NaN text at row {original_row_index + 1}.")
                continue

            sentences = self._split_text_into_sentences(original_text)
            logger.debug(f"Split into sentences: {sentences}")
            
            # Chunk sentences based on max_chunk_chars and API key limits
            current_chunk_sentences = []
            current_chunk_chars = 0
            chunk_index = 0 # To differentiate output files for chunks within a row

            for sentence_index, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue

                sentence_chars = len(sentence)

                # If adding the current sentence exceeds the max chunk size, process the current chunk
                if current_chunk_chars + sentence_chars > self.config.max_chunk_chars and current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    output_file_path = self.config.output_directory / f"{original_row_index + 1}_{chunk_index}.mp3"
                    
                    # Process the chunk
                    self._process_chunk(api_key_manager=self.api_manager, 
                                        voice_manager=self.voice_manager,
                                        text_to_speech_func=self.text_to_speech,
                                        config=self.config,
                                        chunk_text=chunk_text, 
                                        chunk_chars=current_chunk_chars, 
                                        output_file_path=output_file_path)
                    
                    current_chunk_sentences = []
                    current_chunk_chars = 0
                    chunk_index += 1

                current_chunk_sentences.append(sentence)
                current_chunk_chars += sentence_chars
            
            # Process any remaining sentences in the last chunk
            if current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences)
                output_file_path = self.config.output_directory / f"{original_row_index + 1}_{chunk_index}.mp3"
                
                self._process_chunk(api_key_manager=self.api_manager, 
                                    voice_manager=self.voice_manager,
                                    text_to_speech_func=self.text_to_speech,
                                    config=self.config,
                                    chunk_text=chunk_text, 
                                    chunk_chars=current_chunk_chars, 
                                    output_file_path=output_file_path)
            
            logger.info(f"Finished processing all chunks for row {original_row_index + 1}.")
            
            # Merge audio files for the current original_row_index
            self._merge_audio_files(original_row_index + 1)
        
        logger.info("Processing completed successfully for all texts.")

    def _process_chunk(self, api_key_manager: APIKeyManager, voice_manager: VoiceManager, text_to_speech_func, config: TTSConfig,
                      chunk_text: str, chunk_chars: int, output_file_path: Path):
        """Helper function to process a single chunk of text, including API key switching."""
        while True:
            api_key = api_key_manager.get_api_key(required_tokens=chunk_chars)
            if not api_key:
                logger.critical(f"No API key available with {chunk_chars} tokens for chunk: '{chunk_text[:50]}...'")
                return # Stop processing if no key is available

            voice_id_to_use = ""
            model_id_to_use = ""
            public_owner_id_to_use = None
            library_voice_id = None # Initialize for library voice cleanup

            if config.voice_selection_mode == "shared":
                voice_id_to_use = config.selected_shared_voice_id
                model_id_to_use = config.selected_shared_model_id
                public_owner_id_to_use = config.selected_shared_public_owner_id
                logger.info(f"Using shared voice: {voice_id_to_use} (Owner: {public_owner_id_to_use}) with model: {model_id_to_use})")
            elif config.voice_selection_mode == "library":
                voice_manager.cleanup_voices(api_key) 
                if voice_manager.add_voice(
                    api_key, config.original_voice_id, 
                    config.public_owner_id, "Library_Copy"
                ):
                    library_voice_id = voice_manager.get_voice_id(
                        api_key, config.original_voice_id, config.public_owner_id
                    )
                if not library_voice_id:
                    logger.error(f"Could not get library voice ID for API key {api_key[:5]}... Skipping chunk.")
                    return # Skip this chunk if library voice setup fails
                voice_id_to_use = library_voice_id
                model_id_to_use = config.selected_model_id
                public_owner_id_to_use = config.public_owner_id
                logger.info(f"Using library voice: {voice_id_to_use} (Owner: {public_owner_id_to_use}) with model: {model_id_to_use})")
            else: # Standard voice
                voice_id_to_use = config.standard_voice_id
                model_id_to_use = config.selected_model_id
                logger.info(f"Using standard voice: {voice_id_to_use} with model: {model_id_to_use})")
            
            logger.info(f"Processing chunk ({chunk_chars} chars) with API key {api_key[:5]}...")
            
            result = text_to_speech_func(
                api_key, chunk_text, output_file_path, 
                voice_id=voice_id_to_use, 
                model_id=model_id_to_use, 
                public_owner_id=public_owner_id_to_use,
                similarity=0.85, stability=0.45
            )
            
            if result == "success":
                api_key_manager.update_token_balance(api_key, chunk_chars)
                # Log current token balance after update
                for key_data in api_key_manager.api_keys_data:
                    if key_data['API'] == api_key:
                        logger.info(f"API key {api_key[:5]}... current available tokens: {key_data['available_tokens']}")
                        break
                if config.voice_selection_mode == "library" and library_voice_id:
                    voice_manager.delete_voice(api_key, library_voice_id)
                break # Chunk processed successfully
            elif result == "quota_exceeded":
                logger.warning(f"API key {api_key[:5]}... reported quota exceeded. Marking as exhausted and trying next key.")
                api_key_manager.update_token_balance(api_key, chunk_chars) # Mark as exhausted
                # Loop will continue to try next API key
            elif result == "voice_limit_reached":
                logger.warning(f"API key {api_key[:5]}... reported voice limit reached. Trying next key for voice creation.")
                # No token update needed here, as it's not a token issue.
                # Loop will continue to try next API key.
            elif result == "critical_error":
                logger.critical("Critical error encountered, stopping processing.")
                return
            elif result == "proxy_abuse_detected":
                logger.warning(f"Proxy abuse detected for API key {api_key[:5]}... Retrying with new proxy.")
                # Loop will continue to try next API key
            elif result == "error":
                logger.error(f"Failed to process chunk: '{chunk_text[:50]}...' with API key {api_key[:5]}... Retrying with next key if available.")
                # Loop will continue to try next API key
            
            # If we reach here, it means the current API key failed for some reason,
            # so we try to get a new one in the next iteration of the while loop.
            # If no new key is available, the loop will eventually break due to `api_key` being None.

    def _split_text_into_sentences(self, text: str) -> List[str]:
        """Splits a given text into sentences."""
        # This regex splits by common sentence-ending punctuation,
        # followed by a space or end of string.
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out any empty strings that might result from the split
        return [s.strip() for s in sentences if s.strip()]

    def _merge_audio_files(self, original_row_number: int):
        """
        Merges all sentence-level MP3 files for a given original row into a single MP3 file.
        Deletes intermediate files after merging.
        """
        # The glob pattern should be relative to the directory it's called on.
        # self.config.output_directory is already the base directory.
        input_files = sorted(list(self.config.output_directory.glob(f"{original_row_number}_*.mp3")))

        if not input_files:
            logger.warning(f"No audio files found for row {original_row_number} to merge.")
            return

        # Create a temporary file list for ffmpeg concat
        file_list_path = self.config.output_directory / f"concat_list_{original_row_number}.txt"
        with open(file_list_path, "w") as f:
            for mp3_file in input_files:
                f.write(f"file '{mp3_file.name}'\n")

        output_merged_file = self.config.output_directory / f"{original_row_number}.mp3"

        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0", # Allows relative paths in file list
            "-i", str(file_list_path),
            "-c", "copy",
            str(output_merged_file)
        ]

        try:
            logger.info(f"Merging audio files for row {original_row_number}...")
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            logger.info(f"Successfully merged audio for row {original_row_number} to {output_merged_file.name}")
            logger.debug(f"FFmpeg stdout: {process.stdout}")
            logger.debug(f"FFmpeg stderr: {process.stderr}")

            # Clean up intermediate files
            for mp3_file in input_files:
                os.remove(mp3_file)
            os.remove(file_list_path)
            logger.info(f"Cleaned up intermediate files for row {original_row_number}.")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error merging audio files for row {original_row_number}: {e}")
            logger.error(f"FFmpeg stdout: {e.stdout}")
            logger.error(f"FFmpeg stderr: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during audio merging for row {original_row_number}: {e}")

def test_proxy_connection(proxy_rotator: ProxyRotator):
    """Test proxy connection"""
    if not proxy_rotator.proxies:
        logger.info("No proxy configuration found, using direct connection")
        return True
        
    logger.info("Testing proxy connections...")
    proxy_rotator.test_all_proxies()
    
    stats = proxy_rotator.get_proxy_stats()
    working_proxies = stats['total_proxies'] - stats['failed_proxies']
    
    if working_proxies > 0:
        logger.info(f"Proxy test complete: {working_proxies}/{stats['total_proxies']} proxies working")
        return True
    else:
        logger.error("No working proxies found")
        return False

def create_sample_proxy_config():
    """Create sample proxy configuration file"""
    sample_content = """ip,port,login,password,type
proxy1.example.com,8080,username1,password1,http
proxy2.example.com,8080,username2,password2,https
"""
    
    proxy_file = Path("proxies.csv")
    if not proxy_file.exists():
        with open(proxy_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        logger.info(f"Sample proxy configuration created: {proxy_file}")

def create_sample_api_config():
    """Create sample API key configuration file"""
    sample_content = """API,Date,available_tokens,last_checked
your_api_key_1,01.01.2024,100000,2024-01-01T00:00:00
your_api_key_2,01.01.2024,100000,2024-01-01T00:00:00
your_api_key_3,01.01.2024,100000,2024-01-01T00:00:00
"""
    
    api_file = Path("BASE.csv")
    if not api_file.exists():
        with open(api_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        logger.info(f"Sample API configuration created: {api_file}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Text-to-Speech conversion script')
    parser.add_argument(
        '--lang', type=str, default='RU',
        help='Language code for Excel sheet selection (default: RU)'
    )
    parser.add_argument(
        '--config', type=str, help='Path to configuration file'
    )
    parser.add_argument(
        '--create-samples', action='store_true',
        help='Create sample configuration files'
    )
    parser.add_argument(
        '--test-proxies', action='store_true',
        help='Test proxy connections only'
    )
    parser.add_argument(
        '--test-api-switching', action='store_true',
        help='Enable test mode for API switching (artificially reduces tokens)'
    )
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Create sample configurations if requested
    if args.create_samples:
        create_sample_proxy_config()
        create_sample_api_config()
        logger.info("Sample configuration files created. Please edit them with your actual values.")
        return
    
    # Initialize configuration
    config = TTSConfig()
    
    # Set test_api_switching_mode based on argument
    if args.test_api_switching:
        config.test_api_switching_mode = True
        logger.info("API switching test mode enabled.")

    # Initialize proxy rotator
    proxy_rotator = ProxyRotator(config.proxies_file)
    
    # Test proxies if requested
    if args.test_proxies:
        test_proxy_connection(proxy_rotator)
        return
    
    # Test proxy connection on startup
    if config.proxy_test_on_startup:
        if not test_proxy_connection(proxy_rotator):
            logger.warning("Continuing without working proxies...")
    
    # Initialize processor and start processing
    processor = TTSProcessor(config)
    language = args.lang.upper()
    processor.process_texts(language)

if __name__ == "__main__":
    main()
