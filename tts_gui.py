import sys
from PyQt5.QtWidgets import QGridLayout, QApplication, QWidget, QVBoxLayout, QTabWidget, QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QHBoxLayout, QCheckBox, QMessageBox, QComboBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl # Added QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent # Added for audio playback
import logging
from pathlib import Path
import os
import time
import shutil
import tempfile
import requests # Added requests for downloading preview MP3
import subprocess # Added for system audio playback

# Import core TTS classes from new modules
from tts_modules.config import TTSConfig
from tts_modules.processor import TTSProcessor
from tts_modules.proxy_manager import ProxyRotator
from tts_modules.api_key_manager import APIKeyManager
from tts_modules.voice_manager import VoiceManager

# Configure logging for the GUI
# We'll redirect this to the QTextEdit later
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Worker(QThread):
    """Worker thread to run long-running tasks without freezing the GUI."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    voices_loaded = pyqtSignal(list) # Signal for standard voices
    shared_voices_loaded = pyqtSignal(list) # New signal for shared voices

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.task_type = kwargs.pop('task_type', None) # Extract task_type
        self.kwargs = kwargs # Remaining kwargs to pass to task_func

    def run(self):
        try:
            # Temporarily redirect logger output to the signal
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    logger.removeHandler(handler)
            
            # Create a custom handler to emit log messages as signals
            class SignalHandler(logging.Handler):
                def __init__(self, signal_emitter):
                    super().__init__()
                    self.signal_emitter = signal_emitter
                def emit(self, record):
                    msg = self.format(record)
                    self.signal_emitter.emit(msg)
            
            signal_handler = SignalHandler(self.log_message)
            logger.addHandler(signal_handler)

            # Ensure task_type is not passed to the task_func
            # It should already be popped in __init__, but as a last resort
            if 'task_type' in self.kwargs:
                del self.kwargs['task_type']

            result = self.task_func(*self.args, **self.kwargs)
            
            # Emit voices_loaded signal if this worker's task_type is 'load_voices' and result is available
            if self.task_type == 'load_voices' and result is not None:
                self.voices_loaded.emit(result)
            elif self.task_type == 'search_shared_voices' and result is not None:
                self.shared_voices_loaded.emit(result)
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Restore original logger handlers
            logger.removeHandler(signal_handler)
            logger.addHandler(logging.StreamHandler()) # Re-add default stream handler

class TTSGui(QWidget):
    def __init__(self):
        super().__init__()
        self.config = TTSConfig()
        self.processor = TTSProcessor(self.config) # Initialize processor with config
        self.config.cache_dir.mkdir(parents=True, exist_ok=True) # Ensure cache directory exists

        self.init_ui()
        self.load_config_to_ui()
        self.load_voices_to_combo_box() # Initial load of voices

    def init_ui(self):
        self.setWindowTitle('ElevenLabs TTS Processor')
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

        main_layout = QVBoxLayout()

        # --- File Paths Section ---
        file_paths_group = QGridLayout()
        file_paths_group.addWidget(QLabel("<h3>File Paths</h3>"), 0, 0, 1, 6) # Span across all 6 columns

        # API Keys CSV
        file_paths_group.addWidget(QLabel("API Keys CSV:"), 1, 0)
        self.csv_line_edit, self.csv_browse_button = self._create_file_input(self.config.csv_file_path, self.browse_csv_file)
        file_paths_group.addWidget(self.csv_line_edit, 1, 1)
        file_paths_group.addWidget(self.csv_browse_button, 1, 2)

        # Excel File
        file_paths_group.addWidget(QLabel("Excel File:"), 1, 3)
        self.xlsx_line_edit, self.xlsx_browse_button = self._create_file_input(self.config.xlsx_file_path, self.browse_xlsx_file)
        file_paths_group.addWidget(self.xlsx_line_edit, 1, 4)
        file_paths_group.addWidget(self.xlsx_browse_button, 1, 5)

        # Output Directory
        file_paths_group.addWidget(QLabel("Output Directory:"), 2, 0)
        self.output_dir_line_edit, self.output_dir_browse_button = self._create_file_input(self.config.output_directory, self.browse_output_directory, is_dir=True)
        file_paths_group.addWidget(self.output_dir_line_edit, 2, 1)
        file_paths_group.addWidget(self.output_dir_browse_button, 2, 2)

        # Proxies CSV
        file_paths_group.addWidget(QLabel("Proxies CSV:"), 2, 3)
        self.proxies_line_edit, self.proxies_browse_button = self._create_file_input(self.config.proxies_file, self.browse_proxies_file)
        file_paths_group.addWidget(self.proxies_line_edit, 2, 4)
        file_paths_group.addWidget(self.proxies_browse_button, 2, 5)
        
        main_layout.addLayout(file_paths_group)

        # --- Voice Settings Section ---
        voice_settings_group = QVBoxLayout()
        voice_settings_group.addWidget(QLabel("<h3>Voice Selection</h3>"))

        # Voice Selection Tabs
        self.voice_tabs = QTabWidget()
        self.voice_tabs.currentChanged.connect(self._on_voice_tab_changed) # Connect signal

        # Group for Standard Voice Settings
        self.standard_voice_settings_frame = QWidget()
        standard_voice_layout = QVBoxLayout(self.standard_voice_settings_frame)
        standard_voice_layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins

        # Standard Voice: Voice, Language, Play, Refresh (compacted)
        standard_voice_compact_layout = QGridLayout()
        standard_voice_compact_layout.addWidget(QLabel("Voice:"), 0, 0)
        self.standard_voice_combobox = QComboBox()
        standard_voice_compact_layout.addWidget(self.standard_voice_combobox, 0, 1, 1, 2) # Span 2 columns
        self.standard_voice_combobox.currentIndexChanged.connect(self._on_voice_selection_changed)

        standard_voice_compact_layout.addWidget(QLabel("Language:"), 1, 0)
        self.language_combobox = QComboBox()
        standard_voice_compact_layout.addWidget(self.language_combobox, 1, 1, 1, 2) # Span 2 columns

        self.play_preview_button = QPushButton("Play Preview")
        standard_voice_compact_layout.addWidget(self.play_preview_button, 0, 3)
        self.play_preview_button.clicked.connect(self.play_voice_preview)

        self.refresh_voices_button = QPushButton("Refresh Voices")
        standard_voice_compact_layout.addWidget(self.refresh_voices_button, 1, 3)
        self.refresh_voices_button.clicked.connect(self._on_refresh_voices_clicked)
        
        standard_voice_layout.addLayout(standard_voice_compact_layout)
        standard_voice_layout.addStretch(1) # Push content to top
        self.voice_tabs.addTab(self.standard_voice_settings_frame, "Standard Voice") # Add as tab

        # Group for Library Voice Settings
        self.library_voice_settings_frame = QWidget()
        library_voice_layout = QVBoxLayout(self.library_voice_settings_frame)
        library_voice_layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins
        # Removed: library_voice_layout.addWidget(QLabel("<h3>Library Voice by ID</h3>"))

        self.original_voice_id_input = self._create_text_input("Original Voice ID (Library):", self.config.original_voice_id)
        library_voice_layout.addLayout(self.original_voice_id_input)

        self.public_owner_id_input = self._create_text_input("Public Owner ID (Library):", self.config.public_owner_id)
        library_voice_layout.addLayout(self.public_owner_id_input)
        self.voice_tabs.addTab(self.library_voice_settings_frame, "Library Voice by ID") # Add as tab

        library_voice_layout.addStretch(1) # Push content to top
        self.voice_tabs.addTab(self.library_voice_settings_frame, "Library Voice by ID") # Add as tab

        # Group for Shared Voice Search Settings
        self.shared_voices_group_widget = QWidget()
        shared_voices_group_layout = QGridLayout(self.shared_voices_group_widget) # Changed to QGridLayout
        shared_voices_group_layout.setContentsMargins(0, 0, 0, 0) # Remove extra margins
        # Removed: shared_voices_group_layout.addWidget(QLabel("<h3>Shared Voice Search</h3>"), 0, 0, 1, 2) # Span 2 columns

        # Gender Filter
        gender_layout = QHBoxLayout()
        gender_layout.addWidget(QLabel("Gender:"))
        self.shared_voice_gender_combobox = QComboBox()
        self.shared_voice_gender_combobox.addItems(["", "female", "male"]) # Empty string for "any"
        gender_layout.addWidget(self.shared_voice_gender_combobox)
        shared_voices_group_layout.addLayout(gender_layout, 1, 0) # Row 1, Col 0

        # Language Filter
        shared_lang_layout = QHBoxLayout()
        shared_lang_layout.addWidget(QLabel("Language:"))
        self.shared_voice_language_combobox = QComboBox()
        # Populate with common languages, or fetch from API if needed
        self.shared_voice_language_combobox.addItems(["", "en", "ru", "de", "fr", "es", "it", "pt", "pl", "zh", "ja", "ko"])
        shared_lang_layout.addWidget(self.shared_voice_language_combobox)
        shared_voices_group_layout.addLayout(shared_lang_layout, 1, 1) # Row 1, Col 1

        # Page Size
        page_size_layout = QHBoxLayout()
        page_size_layout.addWidget(QLabel("Results per page:"))
        self.shared_voice_page_size_input = QLineEdit(str(self.config.shared_voice_page_size))
        page_size_layout.addWidget(self.shared_voice_page_size_input)
        shared_voices_group_layout.addLayout(page_size_layout, 2, 0) # Row 2, Col 0

        # Search Button
        self.search_shared_voices_button = QPushButton("Search Shared Voices")
        self.search_shared_voices_button.clicked.connect(self.search_shared_voices)
        shared_voices_group_layout.addWidget(self.search_shared_voices_button, 2, 1) # Row 2, Col 1

        # Shared Voices Results
        shared_voice_results_layout = QHBoxLayout()
        shared_voice_results_layout.addWidget(QLabel("Shared Voice Results:"))
        self.shared_voice_combobox = QComboBox()
        shared_voice_results_layout.addWidget(self.shared_voice_combobox)
        self.shared_voice_combobox.currentIndexChanged.connect(self._on_shared_voice_selection_changed)
        shared_voices_group_layout.addLayout(shared_voice_results_layout, 3, 0, 1, 2) # Row 3, Col 0, Span 2 columns

        # Shared Voice Language/Model selection
        shared_voice_lang_model_layout = QHBoxLayout()
        shared_voice_lang_model_layout.addWidget(QLabel("Shared Voice Language/Model:"))
        self.shared_voice_language_model_combobox = QComboBox()
        shared_voice_lang_model_layout.addWidget(self.shared_voice_language_model_combobox)
        shared_voices_group_layout.addLayout(shared_voice_lang_model_layout, 4, 0, 1, 2) # Row 4, Col 0, Span 2 columns

        # Copyable Voice IDs
        shared_voices_group_layout.addWidget(QLabel("Selected Voice ID:"), 5, 0)
        self.selected_shared_voice_id_display = QLineEdit("")
        self.selected_shared_voice_id_display.setReadOnly(True)
        shared_voices_group_layout.addWidget(self.selected_shared_voice_id_display, 5, 1)

        shared_voices_group_layout.addWidget(QLabel("Selected Owner ID:"), 6, 0)
        self.selected_shared_public_owner_id_display = QLineEdit("")
        self.selected_shared_public_owner_id_display.setReadOnly(True)
        shared_voices_group_layout.addWidget(self.selected_shared_public_owner_id_display, 6, 1)

        # Play Shared Voice Preview
        self.play_shared_preview_button = QPushButton("Play Shared Voice Preview")
        self.play_shared_preview_button.clicked.connect(self.play_shared_voice_preview)
        shared_voices_group_layout.addWidget(self.play_shared_preview_button, 7, 0, 1, 2) # Row 7, Col 0, Span 2 columns
        shared_voices_group_layout.setRowStretch(8, 1) # Add stretch to the last row to push content to top

        self.voice_tabs.addTab(self.shared_voices_group_widget, "Shared Voice") # Add as tab
        voice_settings_group.addWidget(self.voice_tabs) # Add the tab widget to the voice settings group
        main_layout.addLayout(voice_settings_group)
        
        # Connect the signal for shared voice language/model combobox once in init_ui
        self.shared_voice_language_model_combobox.currentIndexChanged.connect(self._on_shared_voice_language_model_changed)

        # --- API and Proxy Settings Section (Two Columns) ---
        api_proxy_layout = QHBoxLayout()

        # API Settings Section
        api_settings_group = QVBoxLayout()
        api_settings_group.addWidget(QLabel("<h3>API Settings</h3>"))

        self.max_retries_input = self._create_text_input("Max Retries:", str(self.config.max_retries))
        api_settings_group.addLayout(self.max_retries_input)

        self.timeout_input = self._create_text_input("Timeout (s):", str(self.config.timeout))
        api_settings_group.addLayout(self.timeout_input)

        self.retry_delay_input = self._create_text_input("Retry Delay (s):", str(self.config.retry_delay))
        api_settings_group.addLayout(self.retry_delay_input)

        self.api_call_delay_input = self._create_text_input("API Call Delay (s):", str(self.config.api_call_delay_seconds))
        api_settings_group.addLayout(self.api_call_delay_input)

        self.max_chunk_chars_input = self._create_text_input("Max Chunk Characters:", str(self.config.max_chunk_chars))
        api_settings_group.addLayout(self.max_chunk_chars_input)
        
        api_proxy_layout.addLayout(api_settings_group)

        # Proxy Settings Section
        proxy_settings_group = QVBoxLayout()
        proxy_settings_group.addWidget(QLabel("<h3>Proxy Settings</h3>"))

        self.proxy_test_on_startup_checkbox = QCheckBox("Test Proxy on Startup")
        self.proxy_test_on_startup_checkbox.setChecked(self.config.proxy_test_on_startup)
        proxy_settings_group.addWidget(self.proxy_test_on_startup_checkbox)

        self.auto_proxy_rotation_checkbox = QCheckBox("Auto Proxy Rotation")
        self.auto_proxy_rotation_checkbox.setChecked(self.config.auto_proxy_rotation)
        proxy_settings_group.addWidget(self.auto_proxy_rotation_checkbox)

        self.proxy_rotation_interval_input = self._create_text_input("Proxy Rotation Interval:", str(self.config.proxy_rotation_interval))
        proxy_settings_group.addLayout(self.proxy_rotation_interval_input)

        self.test_api_switching_checkbox = QCheckBox("Enable API Switching Test Mode")
        self.test_api_switching_checkbox.setChecked(self.config.test_api_switching_mode)
        proxy_settings_group.addWidget(self.test_api_switching_checkbox)
        
        api_proxy_layout.addLayout(proxy_settings_group)
        main_layout.addLayout(api_proxy_layout)

        # --- Language Selection ---
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language (Excel Sheet Name):"))
        self.lang_input = QLineEdit("RU") # Default language
        lang_layout.addWidget(self.lang_input)
        main_layout.addLayout(lang_layout)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        self.process_button = QPushButton("Process Texts")
        self.process_button.clicked.connect(self.process_texts)
        button_layout.addWidget(self.process_button)

        self.test_proxies_button = QPushButton("Test Proxies")
        self.test_proxies_button.clicked.connect(self.test_proxies)
        button_layout.addWidget(self.test_proxies_button)

        self.clear_output_button = QPushButton("Clear Output Dir")
        self.clear_output_button.clicked.connect(self.clear_output_directory)
        button_layout.addWidget(self.clear_output_button)

        main_layout.addLayout(button_layout)

        # --- Log Display ---
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        main_layout.addWidget(QLabel("<h3>Logs</h3>"))
        main_layout.addWidget(self.log_text_edit)

        self.setLayout(main_layout)

        # Redirect logger output to QTextEdit
        self.log_handler = self.LogTextEditHandler(self.log_text_edit)
        logger.addHandler(self.log_handler)

    def _create_file_input(self, default_path, browse_func, is_dir=False):
        line_edit = QLineEdit(str(default_path))
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: browse_func(line_edit, is_dir))
        return line_edit, browse_button

    def _create_text_input(self, label_text, default_value):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit(default_value)
        layout.addWidget(line_edit)
        return layout

    def browse_csv_file(self, line_edit, is_dir):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select API Keys CSV", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)

    def browse_xlsx_file(self, line_edit, is_dir):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx)")
        if file_path:
            line_edit.setText(file_path)

    def browse_output_directory(self, line_edit, is_dir):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            line_edit.setText(dir_path)

    def browse_proxies_file(self, line_edit, is_dir):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Proxies CSV", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)

    def load_config_to_ui(self):
        # Load current config values into UI elements
        self.csv_line_edit.setText(str(self.config.csv_file_path))
        self.xlsx_line_edit.setText(str(self.config.xlsx_file_path))
        self.output_dir_line_edit.setText(str(self.config.output_directory))
        self.proxies_line_edit.setText(str(self.config.proxies_file))
        
        # The standard_voice_combobox is populated by load_voices_to_combo_box
        # We will select the voice after it's loaded.
        self.original_voice_id_input.itemAt(1).widget().setText(self.config.original_voice_id)
        self.public_owner_id_input.itemAt(1).widget().setText(self.config.public_owner_id)

        self.max_retries_input.itemAt(1).widget().setText(str(self.config.max_retries))
        self.timeout_input.itemAt(1).widget().setText(str(self.config.timeout))
        self.retry_delay_input.itemAt(1).widget().setText(str(self.config.retry_delay))
        self.api_call_delay_input.itemAt(1).widget().setText(str(self.config.api_call_delay_seconds))

        self.proxy_test_on_startup_checkbox.setChecked(self.config.proxy_test_on_startup)
        self.auto_proxy_rotation_checkbox.setChecked(self.config.auto_proxy_rotation)
        self.proxy_rotation_interval_input.itemAt(1).widget().setText(str(self.config.proxy_rotation_interval))
        self.test_api_switching_checkbox.setChecked(self.config.test_api_switching_mode)

        self.max_chunk_chars_input.itemAt(1).widget().setText(str(self.config.max_chunk_chars))

        # Load shared voice search settings
        self.shared_voice_gender_combobox.setCurrentText(self.config.shared_voice_gender)
        self.shared_voice_language_combobox.setCurrentText(self.config.shared_voice_language)
        self.shared_voice_page_size_input.setText(str(self.config.shared_voice_page_size))
        
        # Load selected shared voice (if any) - this will be populated after search
        # For now, just ensure the combobox is clear or has a default
        self.shared_voice_combobox.clear()
        self.shared_voice_combobox.addItem("Select a shared voice", "")
        if self.config.selected_shared_voice_id:
            # Attempt to pre-select if ID is known, though usually populated by search
            pass # Logic to find and select the item would go here if needed

        # Set initial tab based on config
        mode_to_index = {
            "standard": 0,
            "library": 1,
            "shared": 2
        }
        self.voice_tabs.setCurrentIndex(mode_to_index.get(self.config.voice_selection_mode, 0))
        # Manually trigger the tab changed signal to ensure initial state is set
        self._on_voice_tab_changed(self.voice_tabs.currentIndex())

    def update_config_from_ui(self):
        # Update config object from UI elements
        self.config.csv_file_path = Path(self.csv_line_edit.text())
        self.config.xlsx_file_path = Path(self.xlsx_line_edit.text())
        self.config.output_directory = Path(self.output_dir_line_edit.text())
        self.config.proxies_file = Path(self.proxies_line_edit.text())

        # Get selected voice ID from combobox
        selected_voice_index = self.standard_voice_combobox.currentIndex()
        if selected_voice_index >= 0:
            self.config.standard_voice_id = self.standard_voice_combobox.itemData(selected_voice_index).get("voice_id")
        else:
            self.config.standard_voice_id = "" # Or a default value if nothing is selected

        selected_lang_index = self.language_combobox.currentIndex()
        if selected_lang_index >= 0:
            lang_info = self.language_combobox.itemData(selected_lang_index)
            self.config.selected_language = lang_info.get("language", "en")
            self.config.selected_model_id = lang_info.get("model_id", "eleven_multilingual_v2")
        else:
            self.config.selected_language = "en"
            self.config.selected_model_id = "eleven_multilingual_v2"

        self.config.original_voice_id = self.original_voice_id_input.itemAt(1).widget().text()
        self.config.public_owner_id = self.public_owner_id_input.itemAt(1).widget().text()

        self.config.max_retries = int(self.max_retries_input.itemAt(1).widget().text())
        self.config.timeout = int(self.timeout_input.itemAt(1).widget().text())
        self.config.retry_delay = int(self.retry_delay_input.itemAt(1).widget().text())
        self.config.api_call_delay_seconds = int(self.api_call_delay_input.itemAt(1).widget().text())

        self.config.proxy_test_on_startup = self.proxy_test_on_startup_checkbox.isChecked()
        self.config.auto_proxy_rotation = self.auto_proxy_rotation_checkbox.isChecked()
        self.config.proxy_rotation_interval = int(self.proxy_rotation_interval_input.itemAt(1).widget().text())
        self.config.test_api_switching_mode = self.test_api_switching_checkbox.isChecked()

        self.config.max_chunk_chars = int(self.max_chunk_chars_input.itemAt(1).widget().text())

        # Update shared voice search parameters
        self.config.shared_voice_gender = self.shared_voice_gender_combobox.currentText()
        self.config.shared_voice_language = self.shared_voice_language_combobox.currentText()
        self.config.shared_voice_page_size = int(self.shared_voice_page_size_input.text())

        # Update selected shared voice details
        selected_shared_voice_index = self.shared_voice_combobox.currentIndex()
        shared_voice_data = self.shared_voice_combobox.itemData(selected_shared_voice_index, Qt.UserRole)
        
        # Ensure shared_voice_data is a dictionary before trying to access its keys
        if selected_shared_voice_index >= 0 and isinstance(shared_voice_data, dict):
            self.config.selected_shared_voice_id = shared_voice_data.get("voice_id", "")
            self.config.selected_shared_public_owner_id = shared_voice_data.get("public_owner_id", "")
            
            # Determine selected_shared_model_id from the shared_voice_language_model_combobox
            selected_shared_lang_model_index = self.shared_voice_language_model_combobox.currentIndex()
            if selected_shared_lang_model_index >= 0:
                selected_lang_info = self.shared_voice_language_model_combobox.itemData(selected_shared_lang_model_index, Qt.UserRole)
                if isinstance(selected_lang_info, dict):
                    self.config.selected_shared_model_id = selected_lang_info.get("model_id", "")
                else:
                    self.config.selected_shared_model_id = ""
            else:
                self.config.selected_shared_model_id = "" # Default if no language/model selected for shared voice

            # Update voice_selection_mode based on current tab
            mode_map = {
                0: "standard",
                1: "library",
                2: "shared"
            }
            self.config.voice_selection_mode = mode_map.get(self.voice_tabs.currentIndex(), "standard")
        else:
            self.config.selected_shared_voice_id = ""
            self.config.selected_shared_public_owner_id = ""
            self.config.selected_shared_model_id = ""
            # Update voice_selection_mode based on current tab even if no shared voice is selected
            mode_map = {
                0: "standard",
                1: "library",
                2: "shared"
            }
            self.config.voice_selection_mode = mode_map.get(self.voice_tabs.currentIndex(), "standard")

        # Re-initialize processor with updated config
        # The TTSProcessor now handles its internal dependencies (ProxyRotator, APIKeyManager, VoiceManager)
        # so we just need to pass the config.
        self.processor = TTSProcessor(self.config)

    def load_voices_to_combo_box(self, force_refresh: bool = False):
        self.update_config_from_ui() # Ensure config is up-to-date for API key
        api_key = self.processor.api_manager.get_api_key(required_tokens=1) # Get any valid API key
        if not api_key:
            logger.warning("No API key available to fetch voices. Please configure API keys.")
            self.standard_voice_combobox.clear()
            self.standard_voice_combobox.addItem("No API Key", "")
            return

        self.standard_voice_combobox.clear()
        self.standard_voice_combobox.addItem("Loading voices...", "")
        self.refresh_voices_button.setEnabled(False)
        self.play_preview_button.setEnabled(False)

        # Pass force_refresh to the worker
        self.worker = Worker(self.processor.voice_manager.get_available_voices, api_key, force_refresh=force_refresh, task_type='load_voices')
        self.worker.voices_loaded.connect(self.on_voices_loaded)
        self.worker.finished.connect(lambda: self.refresh_voices_button.setEnabled(True))
        self.worker.error.connect(self.on_load_voices_error)
        self.worker.log_message.connect(self.log_text_edit.append)
        self.worker.start()

    def on_voices_loaded(self, voices_data):
        self.standard_voice_combobox.clear()
        if not voices_data:
            self.standard_voice_combobox.addItem("No voices found", "")
            logger.warning("No voices found for the provided API key.")
            return

        current_voice_id = self.config.standard_voice_id
        selected_index = 0
        for i, voice in enumerate(voices_data):
            self.standard_voice_combobox.addItem(voice.get("name", "Unnamed Voice"))
            self.standard_voice_combobox.setItemData(i, voice, Qt.UserRole) # Store entire voice dict
            if voice.get("voice_id") == current_voice_id:
                selected_index = i
        
        self.standard_voice_combobox.setCurrentIndex(selected_index)
        # Explicitly call _on_voice_selection_changed to populate languages for the initially selected voice
        self._on_voice_selection_changed(selected_index)
        self.play_preview_button.setEnabled(True)
        logger.info(f"Loaded {len(voices_data)} voices into dropdown.")

    def on_load_voices_error(self, error_message):
        logger.error(f"Failed to load voices: {error_message}")
        self.standard_voice_combobox.clear()
        self.standard_voice_combobox.addItem("Error loading voices", "")
        self.play_preview_button.setEnabled(False)

    def _on_refresh_voices_clicked(self):
        reply = QMessageBox.question(self, 'Refresh Voices', 
                                     "Refreshing voices will clear the local cache and download all voice data and previews again. Continue?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._clear_voice_cache()
            self.load_voices_to_combo_box(force_refresh=True) # Pass force_refresh to VoiceManager

    def _clear_voice_cache(self):
        """Clears all cached voice JSON data and preview MP3s."""
        try:
            if self.config.cache_dir.exists():
                shutil.rmtree(self.config.cache_dir)
                self.config.cache_dir.mkdir(parents=True, exist_ok=True) # Recreate empty directory
                logger.info(f"Cleared voice cache at {self.config.cache_dir}")
            else:
                logger.info("Voice cache directory does not exist, no need to clear.")
        except Exception as e:
            logger.error(f"Error clearing voice cache: {e}")

    def _on_voice_selection_changed(self, index):
        self.language_combobox.clear()
        if index < 0:
            return

        voice_data = self.standard_voice_combobox.itemData(index, Qt.UserRole)
        if not voice_data:
            return

        verified_languages = voice_data.get("verified_languages", [])
        if not verified_languages:
            self.language_combobox.addItem("No languages available", "")
            return

        default_lang_index = 0
        for i, lang_info in enumerate(verified_languages):
            lang_display = f"{lang_info.get('language', 'Unknown')}"
            if lang_info.get('locale'):
                lang_display += f" ({lang_info['locale']})"
            if lang_info.get('model_id'):
                lang_display += f" [{lang_info['model_id']}]"
            
            self.language_combobox.addItem(lang_display, lang_info) # Store full lang_info as itemData
            
            if lang_info.get('language') == 'en': # Set 'en' as default if available
                default_lang_index = i
        
        self.language_combobox.setCurrentIndex(default_lang_index)
        logger.info(f"Populated languages for voice: {voice_data.get('name')}")

    def play_voice_preview(self):
        selected_voice_index = self.standard_voice_combobox.currentIndex()
        selected_lang_index = self.language_combobox.currentIndex()

        if selected_voice_index < 0 or selected_lang_index < 0:
            logger.warning("No voice or language selected for preview.")
            return

        # Get the full language info from the language combobox's itemData
        lang_info = self.language_combobox.itemData(selected_lang_index, Qt.UserRole)
        if not lang_info or not lang_info.get("preview_url"):
            logger.warning("No preview URL available for the selected language.")
            return
        
        preview_url = lang_info["preview_url"]

        logger.info(f"Playing preview from: {preview_url}")
        self.play_preview_button.setEnabled(False) # Disable button during playback

        if not hasattr(self, 'media_player'):
            self.media_player = QMediaPlayer()
            self.media_player.stateChanged.connect(self._on_media_state_changed)
            self.media_player.error.connect(self._on_media_error)

        # Stop any currently playing audio
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()

        # Set media content and play
        # Ensure the path is absolute for QUrl.fromLocalFile
        absolute_preview_path = Path(preview_url).resolve()
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(absolute_preview_path))))
        self.media_player.play()
        logger.info("Audio playback initiated.")

    def _on_media_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            self.play_preview_button.setEnabled(True) # Re-enable standard preview button
            self.play_shared_preview_button.setEnabled(True) # Re-enable shared preview button

    def _on_media_error(self, error):
        logger.error(f"Media player error: {self.media_player.errorString()}")
        self.play_preview_button.setEnabled(True) # Re-enable button on error
        self.play_shared_preview_button.setEnabled(True) # Re-enable shared preview button on error

    def _on_voice_tab_changed(self, index):
        # Map tab index to voice selection mode
        mode_map = {
            0: "standard",
            1: "library",
            2: "shared"
        }
        self.config.voice_selection_mode = mode_map.get(index, "standard")
        logger.info(f"Voice selection mode changed to: {self.config.voice_selection_mode}")

    def search_shared_voices(self):
        self.update_config_from_ui() # Ensure config is up-to-date for API key
        api_key = self.processor.api_manager.get_api_key(required_tokens=1) # Get any valid API key
        if not api_key:
            logger.warning("No API key available to fetch shared voices. Please configure API keys.")
            self.shared_voice_combobox.clear()
            self.shared_voice_combobox.addItem("No API Key", "")
            return

        gender = self.shared_voice_gender_combobox.currentText()
        language = self.shared_voice_language_combobox.currentText()
        page_size = int(self.shared_voice_page_size_input.text())

        self.shared_voice_combobox.clear()
        self.shared_voice_combobox.addItem("Searching shared voices...", "")
        self.search_shared_voices_button.setEnabled(False)
        self.play_shared_preview_button.setEnabled(False)

        self.worker = Worker(self.processor.voice_manager.get_shared_voices, api_key, gender=gender, language=language, page_size=page_size, task_type='search_shared_voices')
        self.worker.shared_voices_loaded.connect(self.on_shared_voices_loaded)
        self.worker.finished.connect(lambda: self.search_shared_voices_button.setEnabled(True))
        self.worker.error.connect(self.on_search_shared_voices_error)
        self.worker.log_message.connect(self.log_text_edit.append)
        self.worker.start()

    def on_shared_voices_loaded(self, voices_data):
        self.shared_voice_combobox.clear()
        if not voices_data:
            self.shared_voice_combobox.addItem("No shared voices found", "")
            logger.warning("No shared voices found for the specified criteria.")
            return

        for i, voice in enumerate(voices_data):
            self.shared_voice_combobox.addItem(voice.get("name", "Unnamed Shared Voice"))
            self.shared_voice_combobox.setItemData(i, voice, Qt.UserRole) # Store entire voice dict
        
        self.shared_voice_combobox.setCurrentIndex(0) # Select the first one by default
        self.play_shared_preview_button.setEnabled(True)
        logger.info(f"Loaded {len(voices_data)} shared voices into dropdown.")

    def on_search_shared_voices_error(self, error_message):
        logger.error(f"Failed to search shared voices: {error_message}")
        self.shared_voice_combobox.clear()
        self.shared_voice_combobox.addItem("Error searching shared voices", "")
        self.play_shared_preview_button.setEnabled(False)

    def _on_shared_voice_selection_changed(self, index):
        self.shared_voice_language_model_combobox.clear()
        self.selected_shared_voice_id_display.clear()
        self.selected_shared_public_owner_id_display.clear()

        if index < 0:
            return
        
        voice_data = self.shared_voice_combobox.itemData(index, Qt.UserRole)
        if not voice_data:
            return

        # Populate copyable ID fields
        self.selected_shared_voice_id_display.setText(voice_data.get("voice_id", ""))
        self.selected_shared_public_owner_id_display.setText(voice_data.get("public_owner_id", ""))

        verified_languages = voice_data.get("verified_languages", [])
        if not verified_languages:
            self.shared_voice_language_model_combobox.addItem("No languages available", "")
            return

        default_lang_index = 0
        for i, lang_info in enumerate(verified_languages):
            lang_display = f"{lang_info.get('language', 'Unknown')}"
            if lang_info.get('locale'):
                lang_display += f" ({lang_info['locale']})"
            if lang_info.get('model_id'):
                lang_display += f" [{lang_info['model_id']}]"
            
            self.shared_voice_language_model_combobox.addItem(lang_display, lang_info) # Store full lang_info as itemData
            
            if lang_info.get('language') == 'en': # Set 'en' as default if available
                default_lang_index = i
        
        self.shared_voice_language_model_combobox.setCurrentIndex(default_lang_index)
        logger.info(f"Populated languages/models for shared voice: {voice_data.get('name')}")
        
        # The signal is now connected in init_ui, so no need to connect here.
        # Manually trigger for initial selection, as setCurrentIndex might not trigger if index is already 0
        # or if the combobox was empty before.
        self._on_shared_voice_language_model_changed(default_lang_index) 

    def _on_shared_voice_language_model_changed(self, index):
        # This method is called when a language/model is selected for a shared voice
        # It ensures the config is updated with the correct model_id for the selected shared voice
        self.update_config_from_ui()
        logger.info(f"Shared voice language/model changed to index: {index}")

    def play_shared_voice_preview(self):
        selected_voice_index = self.shared_voice_combobox.currentIndex()
        if selected_voice_index < 0:
            logger.warning("No shared voice selected for preview.")
            return

        voice_data = self.shared_voice_combobox.itemData(selected_voice_index, Qt.UserRole)
        if not voice_data or not voice_data.get("preview_url"):
            logger.warning("No preview URL available for the selected shared voice.")
            return
        
        preview_url = voice_data["preview_url"]

        logger.info(f"Playing shared voice preview from: {preview_url}")
        self.play_shared_preview_button.setEnabled(False) # Disable button during playback

        if not hasattr(self, 'media_player'):
            self.media_player = QMediaPlayer()
            self.media_player.stateChanged.connect(self._on_media_state_changed)
            self.media_player.error.connect(self._on_media_error)

        # Stop any currently playing audio
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()

        # Set media content and play
        # Check if it's a local file path or a remote URL
        if Path(preview_url).exists(): # Assuming local cached files exist
            absolute_preview_path = Path(preview_url).resolve()
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(absolute_preview_path))))
        else: # Assume it's a remote URL
            self.media_player.setMedia(QMediaContent(QUrl(preview_url)))
        self.media_player.play()
        logger.info("Shared voice audio playback initiated.")

    def process_texts(self):
        self.update_config_from_ui()
        lang = self.lang_input.text()
        self.log_text_edit.clear()
        logger.info(f"Starting text processing for language: {lang}...")
        
        self.worker = Worker(self.processor.process_texts, lang)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.error.connect(self.on_process_error)
        self.worker.log_message.connect(self.log_text_edit.append)
        self.worker.start()

    def on_process_finished(self):
        logger.info("Text processing completed.")

    def on_process_error(self, error_message):
        logger.error(f"Text processing failed: {error_message}")

    def test_proxies(self):
        self.update_config_from_ui()
        self.log_text_edit.clear()
        logger.info("Testing proxies...")
        
        # Re-initialize proxy_rotator with updated config
        # The ProxyRotator is now instantiated directly from its module
        proxy_rotator_instance = ProxyRotator(self.config.proxies_file)
        
        self.worker = Worker(proxy_rotator_instance.test_all_proxies)
        self.worker.finished.connect(self.on_test_proxies_finished)
        self.worker.error.connect(self.on_test_proxies_error)
        self.worker.log_message.connect(self.log_text_edit.append)
        self.worker.start()

    def on_test_proxies_finished(self):
        stats = self.processor.proxy_rotator.get_proxy_stats()
        logger.info(f"Proxy test complete: {stats['total_proxies'] - stats['failed_proxies']}/{stats['total_proxies']} proxies working.")
        logger.info(f"Proxy details: {stats['proxy_details']}")

    def on_test_proxies_error(self, error_message):
        logger.error(f"Proxy test failed: {error_message}")

    def clear_output_directory(self):
        self.update_config_from_ui()
        output_dir = self.config.output_directory
        if output_dir.exists() and output_dir.is_dir():
            reply = QMessageBox.question(self, 'Clear Directory', 
                                         f"Are you sure you want to delete all contents of '{output_dir}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    for item in output_dir.iterdir():
                        if item.is_file():
                            os.remove(item)
                        elif item.is_dir():
                            shutil.rmtree(item)
                    logger.info(f"Cleared contents of {output_dir}")
                except Exception as e:
                    logger.error(f"Error clearing output directory: {e}")
        else:
            logger.warning(f"Output directory does not exist or is not a directory: {output_dir}")

    def closeEvent(self, event):
        """Event handler for when the window is closed."""
        logger.info("Saving configuration before closing...")
        self.update_config_from_ui() # Ensure config object is up-to-date
        self.config.save_to_json() # Save current settings to config.json
        event.accept() # Accept the close event

    class LogTextEditHandler(logging.Handler):
        def __init__(self, text_edit):
            super().__init__()
            self.text_edit = text_edit
            self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        def emit(self, record):
            msg = self.format(record)
            self.text_edit.append(msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TTSGui()
    ex.show()
    sys.exit(app.exec_())
