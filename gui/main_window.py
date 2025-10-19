"""
Main GUI window for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, List
from pathlib import Path
from utils.core import SettingsManager
from utils.models import SettingFile, get_window_settings, set_window_settings
from .widgets import create_main_layout
from .handlers import EventHandlers
from .helpers import center_window, sort_tree


class PyEveSettingsGUI:
    """Main GUI application for py-eve-settings"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PyEveSettings")
        
        # Load saved window settings from cache
        SettingFile.load_cache()  # Ensure cache is loaded
        settings = get_window_settings()
        
        # Apply window size and position
        width = settings['width']
        height = settings['height']
        x_pos = settings['x_pos']
        y_pos = settings['y_pos']
        
        if x_pos is not None and y_pos is not None:
            # Use saved position
            self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        else:
            # No saved position, just set size (will be centered later)
            self.root.geometry(f"{width}x{height}")
        
        # Initialize settings manager
        self.manager = SettingsManager()
        self.settings_folders: List[Path] = []
        self.all_char_list: List[SettingFile] = []
        self.all_user_list: List[SettingFile] = []
        self.loading = True
        self.selected_folder: Optional[Path] = None
        
        # Create GUI and get widget references
        widgets = create_main_layout(self.root)
        
        # Store widget references
        self.status_label = widgets['status_label']
        self.path_var = widgets['path_var']
        self.path_entry = widgets['path_entry']
        self.progress = widgets['progress']
        self.profiles_listbox = widgets['profiles_listbox']
        self.chars_tree = widgets['chars_tree']
        self.accounts_tree = widgets['accounts_tree']
        
        # Initialize event handlers
        self.handlers = EventHandlers(self)
        
        # Connect event handlers to widgets
        self.profiles_listbox.bind('<<ListboxSelect>>', self.handlers.on_profile_selected)
        widgets['char_edit_btn'].config(command=self.handlers.edit_char_note)
        widgets['char_overwrite_all_btn'].config(command=self.handlers.char_overwrite_all)
        widgets['char_overwrite_select_btn'].config(command=self.handlers.char_overwrite_select)
        widgets['account_edit_btn'].config(command=self.handlers.edit_account_note)
        widgets['account_overwrite_all_btn'].config(command=self.handlers.account_overwrite_all)
        widgets['account_overwrite_select_btn'].config(command=self.handlers.account_overwrite_select)
        
        # Bind window resize/move event to save settings
        self.root.bind('<Configure>', self.on_window_configure)
        self.resize_timer = None  # Timer to debounce resize/move events
        
        # Center window only if no saved position
        if x_pos is None or y_pos is None:
            center_window(self.root)
        
        # Start loading data in background
        self.root.after(100, self.start_loading_data)
    
    def on_window_configure(self, event):
        """
        Handle window resize and move events and save the new settings
        Uses a timer to debounce rapid configure events
        """
        # Only handle configure events from the root window, not child widgets
        if event.widget != self.root:
            return
        
        # Cancel previous timer if it exists
        if self.resize_timer is not None:
            self.root.after_cancel(self.resize_timer)
        
        # Set a new timer to save the size after 500ms of no resizing
        self.resize_timer = self.root.after(500, self.save_window_settings)
    
    def save_window_settings(self):
        """Save the current window size and position to cache"""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x_pos = self.root.winfo_x()
        y_pos = self.root.winfo_y()
        
        # Save window settings (size and position)
        set_window_settings(width, height, x_pos, y_pos)
        self.resize_timer = None
    
    def start_loading_data(self):
        """Start loading data in a background thread"""
        thread = threading.Thread(target=self.load_data_thread, daemon=True)
        thread.start()
        self.root.after(100, self.check_loading_status)
    
    def load_data_thread(self):
        """Load data in background thread"""
        try:
            # Find settings directories
            self.settings_folders = self.manager.find_settings_directories()
            
            if not self.settings_folders:
                self.loading = False
                return
            
            # Load settings files (this calls the API)
            self.manager.load_files(self.settings_folders)
            
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
            self.loading = False
    
    def check_loading_status(self):
        """Check if data loading is complete and update UI"""
        if self.loading:
            self.root.after(100, self.check_loading_status)
        else:
            self.on_loading_complete()
    
    def on_loading_complete(self):
        """Called when data loading is complete"""
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
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()
