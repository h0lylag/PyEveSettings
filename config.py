"""
Configuration file for PyEveSettings.

This file contains all default values, magic numbers, and configuration constants
used throughout the application. Centralizing these values makes them easy to
find, modify, and maintain.
"""

# =============================================================================
# Application Metadata
# =============================================================================
APP_NAME = "PyEveSettings"
APP_VERSION = "1.0.0"


# =============================================================================
# Window Settings - Default Values
# =============================================================================
DEFAULT_WINDOW_WIDTH = 1800
DEFAULT_WINDOW_HEIGHT = 1000
DEFAULT_WINDOW_X = 0  # 0 means centered on first run
DEFAULT_WINDOW_Y = 0  # 0 means centered on first run


# =============================================================================
# Sorting Preferences
# =============================================================================
DEFAULT_SORTING = "name_asc"  # Default sorting: Name A-Z


# =============================================================================
# UI Layout Settings
# =============================================================================
# PanedWindow weights (relative sizes)
PROFILES_PANEL_WEIGHT = 1   # Profiles panel (left)
CHARACTERS_PANEL_WEIGHT = 2  # Characters panel (middle)
ACCOUNTS_PANEL_WEIGHT = 2    # Accounts panel (right)

# Column minimum sizes (pixels)
PROFILES_MIN_WIDTH = 200
CHARACTERS_MIN_WIDTH = 400
ACCOUNTS_MIN_WIDTH = 400

# Font sizes
DEFAULT_FONT_SIZE = 10
HEADING_FONT_SIZE = 10
SMALL_FONT_SIZE = 8
MONOSPACE_FONT_SIZE = 10

# Font families
DEFAULT_FONT = "Segoe UI"
MONOSPACE_FONT = "Consolas"

# Padding values
MAIN_PADDING = 10
PANEL_PADDING = 5
BUTTON_PADDING_X = 2
BUTTON_PADDING_Y = 5


# =============================================================================
# Dialog Settings
# =============================================================================
# Character selection dialog
CHAR_SELECTION_DIALOG_WIDTH = 900
CHAR_SELECTION_DIALOG_HEIGHT = 650

# Account selection dialog
ACCOUNT_SELECTION_DIALOG_WIDTH = 750
ACCOUNT_SELECTION_DIALOG_HEIGHT = 550

# Custom paths dialog
CUSTOM_PATHS_DIALOG_WIDTH = 700
CUSTOM_PATHS_DIALOG_HEIGHT = 400


# =============================================================================
# Data Validation
# =============================================================================
# Maximum note length for characters and accounts
MAX_NOTE_LENGTH = 100

# ESI (EVE Swagger Interface) settings
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_TIMEOUT = 10  # seconds
ESI_MAX_RETRIES = 3


# =============================================================================
# File Paths and Names
# =============================================================================
DATA_FILE_NAME = "pyevesettings_data.json"

# EVE installation folder patterns
EVE_FOLDER_PREFIX = "c_ccp_eve_"
EVE_SETTINGS_FOLDER = "settings_Default"

# Backup settings
BACKUP_FOLDER_NAME = "backups"
BACKUP_FILE_EXTENSION = ".zip"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


# =============================================================================
# Background Task Settings
# =============================================================================
# Progress bar update interval (milliseconds)
PROGRESS_BAR_INTERVAL = 10

# Background thread check interval (milliseconds)
THREAD_CHECK_INTERVAL = 100

# Character name cache refresh delay (milliseconds)
CACHE_REFRESH_DELAY = 100


# =============================================================================
# Tree/List View Settings
# =============================================================================
# Character treeview column widths
CHAR_ID_COLUMN_WIDTH = 100
CHAR_NAME_COLUMN_WIDTH = 250
CHAR_DATE_COLUMN_WIDTH = 150
CHAR_NOTE_COLUMN_WIDTH = 200

# Account treeview column widths
ACCOUNT_ID_COLUMN_WIDTH = 120
ACCOUNT_NAME_COLUMN_WIDTH = 180
ACCOUNT_DATE_COLUMN_WIDTH = 180
ACCOUNT_NOTE_COLUMN_WIDTH = 200


# =============================================================================
# Color Scheme
# =============================================================================
STATUS_COLOR_LOADING = "blue"
STATUS_COLOR_SUCCESS = "green"
STATUS_COLOR_ERROR = "red"
STATUS_COLOR_WARNING = "orange"
STATUS_COLOR_DISABLED = "gray"

HEADER_COLOR = "blue"


# =============================================================================
# Logging Settings
# =============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
