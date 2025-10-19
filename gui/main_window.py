"""Main GUI window for py-eve-settings."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, List
from pathlib import Path

from data import DataFile, WindowSettings, NotesManager
from api import APICache, ESIClient
from platform_utils import EVEPathResolver
from utils.core import SettingsManager
from utils.models import SettingFile
from exceptions import DataFileError, PlatformNotSupportedError
from .widgets import create_main_layout
from .handlers import EventHandlers
from .helpers import center_window, sort_tree


class PyEveSettingsGUI:
    """Main GUI application for py-eve-settings."""
    
    def __init__(self):
        """Initialize the PyEveSettings GUI application."""
        self.root = tk.Tk()
        self.root.title("PyEveSettings")
        
        # Initialize state variables
        self.settings_folders: List[Path] = []
        self.all_char_list: List[SettingFile] = []
        self.all_user_list: List[SettingFile] = []
        self.loading = True
        self.selected_folder: Optional[Path] = None
        self.resize_timer: Optional[str] = None
        
        # Initialize application layers
        self._init_data_layer()
        self._init_managers()
        self._apply_window_geometry()
        self._init_gui()
        self._setup_event_handlers()
        
        # Center window only if no saved position
        if self.window_settings.should_center():
            center_window(self.root)
        
        # Start loading data in background
        self.root.after(100, self.start_loading_data)
    
    def _init_data_layer(self) -> None:
        """Initialize data persistence layer.
        
        Raises:
            SystemExit: If data file cannot be loaded.
        """
        try:
            self.data_file = DataFile()
            data = self.data_file.load()
            
            # Initialize window settings
            self.window_settings = WindowSettings.from_dict(
                self.data_file.get_window_settings()
            )
            
            # Initialize notes manager
            self.notes_manager = NotesManager()
            self.notes_manager.load_from_dict(
                self.data_file.get_character_notes(),
                self.data_file.get_account_notes()
            )
        except DataFileError as e:
            messagebox.showerror(
                "Data File Error",
                f"Failed to load application data:\n\n{e}\n\n"
                "The application will now exit."
            )
            raise SystemExit(1) from e
    
    def _init_managers(self) -> None:
        """Initialize API cache and settings manager.
        
        Raises:
            SystemExit: If platform is not supported.
        """
        try:
            # Initialize API cache
            self.api_cache = APICache(ESIClient())
            # Convert string keys to int for cache loading
            char_names = {int(k): v for k, v in self.data_file.get_character_names().items()}
            invalid_ids = {int(i) for i in self.data_file.get_invalid_ids()}
            self.api_cache.load_cache(char_names, invalid_ids)
            
            # Initialize settings manager with dependencies
            path_resolver = EVEPathResolver()
            self.manager = SettingsManager(path_resolver, self.api_cache)
        except PlatformNotSupportedError as e:
            messagebox.showerror(
                "Platform Not Supported",
                f"{e}\n\nThe application will now exit."
            )
            raise SystemExit(1) from e
    
    def _apply_window_geometry(self) -> None:
        """Apply saved window geometry or default size."""
        if not self.window_settings.should_center():
            # Use saved position
            self.root.geometry(self.window_settings.get_geometry_string())
        else:
            # No saved position, just set size (will be centered later)
            self.root.geometry(f"{self.window_settings.width}x{self.window_settings.height}")
    
    def _init_gui(self) -> None:
        """Initialize GUI widgets and layout."""
        widgets = create_main_layout(self.root)
        
        # Store widget references
        self.status_label = widgets['status_label']
        self.path_var = widgets['path_var']
        self.path_entry = widgets['path_entry']
        self.progress = widgets['progress']
        self.profiles_listbox = widgets['profiles_listbox']
        self.chars_tree = widgets['chars_tree']
        self.accounts_tree = widgets['accounts_tree']
        
        # Store button widgets for event handler binding
        self._widgets = widgets
    
    def _setup_event_handlers(self) -> None:
        """Connect event handlers to GUI widgets."""
        # Initialize event handlers
        self.handlers = EventHandlers(self)
        
        # Connect event handlers to widgets
        self.profiles_listbox.bind('<<ListboxSelect>>', self.handlers.on_profile_selected)
        self._widgets['char_edit_btn'].config(command=self.handlers.edit_char_note)
        self._widgets['char_overwrite_all_btn'].config(command=self.handlers.char_overwrite_all)
        self._widgets['char_overwrite_select_btn'].config(command=self.handlers.char_overwrite_select)
        self._widgets['account_edit_btn'].config(command=self.handlers.edit_account_note)
        self._widgets['account_overwrite_all_btn'].config(command=self.handlers.account_overwrite_all)
        self._widgets['account_overwrite_select_btn'].config(command=self.handlers.account_overwrite_select)
        
        # Bind window resize/move event to save settings
        self.root.bind('<Configure>', self._handle_window_configure)
    
    def _handle_window_configure(self, event: tk.Event) -> None:
        """Handle window resize and move events and save the new settings.
        
        Uses a timer to debounce rapid configure events.
        
        Args:
            event: The configure event from tkinter.
        """
        # Only handle configure events from the root window, not child widgets
        if event.widget != self.root:
            return
        
        # Cancel previous timer if it exists
        if self.resize_timer is not None:
            self.root.after_cancel(self.resize_timer)
        
        # Set a new timer to save the size after 500ms of no resizing
        self.resize_timer = self.root.after(500, self._save_window_state)
    
    def _save_window_state(self) -> None:
        """Save the current window size and position."""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x_pos = self.root.winfo_x()
        y_pos = self.root.winfo_y()
        
        # Update window settings object
        self.window_settings.update(width, height, x_pos, y_pos)
        
        # Save to data file
        self.data_file.set_window_settings(width, height, x_pos, y_pos)
        self.data_file.save()
        
        self.resize_timer = None
    
    def start_loading_data(self) -> None:
        """Start loading data in a background thread."""
        thread = threading.Thread(target=self.load_data_thread, daemon=True)
        thread.start()
        self.root.after(100, self.check_loading_status)
    
    def load_data_thread(self) -> None:
        """Load data in background thread."""
        try:
            # Find settings directories
            self.settings_folders = self.manager.discover_settings_folders()
            
            if not self.settings_folders:
                self.loading = False
                return
            
            # Load settings files and get character IDs that need fetching
            character_ids = self.manager.load_files(self.settings_folders)
            
            # Fetch character names in bulk if needed
            if character_ids:
                self.api_cache.fetch_names_bulk(character_ids)
                
                # Save updated cache to disk
                for char_id, name in self.api_cache.get_all_cached().items():
                    self.data_file.save_character_name(str(char_id), name)
                for invalid_id in self.api_cache.get_all_invalid():
                    self.data_file.add_invalid_id(str(invalid_id))
                self.data_file.save()
            
            # Store full lists for filtering
            self.all_char_list = self.manager.char_list.copy()
            self.all_user_list = self.manager.user_list.copy()
            
            # Check if we have both types of files
            if not self.manager.user_list or not self.manager.char_list:
                self.loading = False
                return
            
            self.loading = False
            
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            self.loading = False
    
    def check_loading_status(self) -> None:
        """Check if data loading is complete and update UI."""
        if self.loading:
            self.root.after(100, self.check_loading_status)
        else:
            self.on_loading_complete()
    
    def on_loading_complete(self) -> None:
        """Called when data loading is complete."""
        self.progress.stop()
        self.progress.grid_remove()
        
        # Check for errors
        if not self.settings_folders:
            self.status_label.config(
                text="No EVE settings directories found. Use 'Custom...' to select a folder.",
                foreground="orange"
            )
            messagebox.showwarning("No Directories Found", 
                               "Could not find EVE settings directories.\n\n"
                               "You can use the 'Custom...' option to manually select\n"
                               "a settings folder containing EVE profile files.")
            # Add Custom option to allow manual selection
            self.profiles_listbox.insert(tk.END, "Custom...")
            return
        
        if not self.manager.user_list or not self.manager.char_list:
            self.status_label.config(
                text="Warning: Missing user or char files in found directories.",
                foreground="orange"
            )
            messagebox.showwarning("Incomplete Data", 
                               "Some directories are missing user or char files.\n\n"
                               f"Searched in:\n" + "\n".join(str(f) for f in self.settings_folders) +
                               "\n\nYou can use 'Custom...' to select a different folder.")
            # Still show the profiles list so user can try Custom
            for folder in self.settings_folders:
                self.profiles_listbox.insert(tk.END, folder.name)
            self.profiles_listbox.insert(tk.END, "Custom...")
            return
        
        # Update status label
        folders_text = f"Found {len(self.settings_folders)} settings folder(s)"
        self.status_label.config(text=folders_text, foreground="gray")
        
        # Populate profiles listbox
        for folder in self.settings_folders:
            self.profiles_listbox.insert(tk.END, folder.name)
        self.profiles_listbox.insert(tk.END, "Custom...")
        
        # Select first profile by default
        self.profiles_listbox.selection_set(0)
        self.selected_folder = self.settings_folders[0]
        self.handlers.update_character_lists()
    
    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()
