"""
Main GUI window for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, List
from pathlib import Path
from utils.core import SettingsManager
from utils.models import SettingFile
from .widgets import create_main_layout
from .handlers import EventHandlers
from .helpers import center_window, sort_tree


class PyEveSettingsGUI:
    """Main GUI application for py-eve-settings"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PyEveSettings")
        self.root.geometry("1200x600")
        
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
        
        # Center window
        center_window(self.root)
        
        # Start loading data in background
        self.root.after(100, self.start_loading_data)
    
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
                text="Error: Could not find EVE settings directories!",
                foreground="red"
            )
            messagebox.showerror("Error", 
                               "Could not find EVE settings directories!\n\n"
                               "Please run this script from an EVE settings folder or ensure\n"
                               "EVE is installed at the default location.")
            self.root.after(100, self.root.quit)
            return
        
        if not self.manager.user_list or not self.manager.char_list:
            self.status_label.config(
                text="Error: Missing user or char files!",
                foreground="red"
            )
            messagebox.showerror("Error", 
                               "Missing user or char file!\n\n"
                               f"Searched in:\n" + "\n".join(str(f) for f in self.settings_folders))
            self.root.after(100, self.root.quit)
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
