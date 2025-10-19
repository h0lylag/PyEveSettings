"""Main GUI window for py-eve-settings."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, List
from pathlib import Path

from data import DataFile, WindowSettings, NotesManager
from esi import ESICache, ESIClient
from utils import EVEPathResolver, BackupManager
from utils.core import SettingsManager
from utils.models import SettingFile
from utils import DataFileError, PlatformNotSupportedError, ValidationError
from .widgets import create_main_layout, create_menu_bar
from .handlers import EventHandlers
from .helpers import center_window, sort_tree
from .dialogs import show_custom_paths_dialog


class PyEveSettingsGUI:
    """Main GUI application for py-eve-settings."""
    
    def __init__(self):
        """Initialize the PyEveSettings GUI application."""
        self.root = tk.Tk()
        self.root.title("PyEveSettings")
        
        # Configure default fonts for the application
        self._configure_fonts()
        
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
    
    def _configure_fonts(self) -> None:
        """Configure default fonts for the entire application."""
        import tkinter.font as tkfont
        
        # Get the default font and increase its size
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        
        # Configure text font (used in Entry, Text, etc.)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(size=10)
        
        # Configure fixed-width font (used in monospace displays)
        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(size=10)
        
        # Configure menu font
        menu_font = tkfont.nametofont("TkMenuFont")
        menu_font.configure(size=10)
        
        # Configure heading font for treeview headers
        heading_font = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        style = ttk.Style()
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=38)
    
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
            self.api_cache = ESICache(ESIClient())
            # Convert string keys to int for cache loading
            char_names = {int(k): v for k, v in self.data_file.get_character_names().items()}
            invalid_ids = {int(i) for i in self.data_file.get_invalid_ids()}
            self.api_cache.load_cache(char_names, invalid_ids)
            
            # Initialize path resolver with custom paths
            custom_paths = self.data_file.get_custom_paths()
            self.path_resolver = EVEPathResolver(custom_paths=custom_paths)
            
            # Discover available servers
            self.available_servers = self.path_resolver.discover_servers()
            
            # Set default server (first discovered or tranquility)
            if self.available_servers:
                self.current_server = list(self.available_servers.keys())[0]
            else:
                self.current_server = 'Tranquility'
            
            # Initialize backup manager
            self.backup_manager = BackupManager()
            
            # Initialize settings manager with dependencies
            self.manager = SettingsManager(self.path_resolver, self.api_cache)
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
        # Create menu bar first
        menu_widgets = create_menu_bar(self.root)
        self.sort_var = menu_widgets['sort_var']
        
        # Load saved sorting preference
        saved_sort = self.data_file.get_default_sorting()
        self.sort_var.set(saved_sort)
        
        # Connect menu handlers
        menu_widgets['file_menu'].entryconfigure("Exit", command=self._on_exit)
        menu_widgets['settings_menu'].entryconfigure("Manage Paths...", command=self._on_manage_paths)
        
        # Connect sort var trace to save preference
        self.sort_var.trace_add('write', self._on_sort_changed)
        
        # Create main layout
        widgets = create_main_layout(self.root)
        
        # Store widget references
        self.server_var = widgets['server_var']
        self.server_combo = widgets['server_combo']
        self.status_label = widgets['status_label']
        self.path_var = widgets['path_var']
        self.path_entry = widgets['path_entry']
        self.progress = widgets['progress']
        self.profiles_listbox = widgets['profiles_listbox']
        self.chars_tree = widgets['chars_tree']
        self.accounts_tree = widgets['accounts_tree']
        self.backup_status_var = widgets['backup_status_var']
        
        # Store button widgets for event handler binding
        self._widgets = widgets
    
    def _setup_event_handlers(self) -> None:
        """Connect event handlers to GUI widgets."""
        # Initialize event handlers
        self.handlers = EventHandlers(self)
        
        # Populate server dropdown and set current selection
        server_names = sorted(self.available_servers.keys()) if self.available_servers else ['Tranquility']
        self.server_combo['values'] = server_names
        self.server_var.set(self.current_server)
        
        # Connect server selection handler
        self.server_combo.bind('<<ComboboxSelected>>', self._on_server_changed)
        
        # Connect backup button handler
        self._widgets['backup_btn'].config(command=self._on_backup_profile)
        
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
    
    def _on_server_changed(self, event: Optional[tk.Event] = None) -> None:
        """Handle server selection change.
        
        Args:
            event: The combobox selection event.
        """
        selected_server = self.server_var.get()
        if selected_server and selected_server != self.current_server:
            self.current_server = selected_server
            
            # Update path resolver with new server
            server_name_lower = selected_server.lower()
            self.path_resolver.server = server_name_lower
            
            # Reload data for the new server
            self.status_label.config(text=f"Switching to {selected_server} server...", foreground="blue")
            self.progress.grid()  # Show progress bar
            self.progress.start(10)
            
            # Clear current data
            self.profiles_listbox.delete(0, tk.END)
            self.chars_tree.delete(*self.chars_tree.get_children())
            self.accounts_tree.delete(*self.accounts_tree.get_children())
            self.path_var.set("")
            
            # Reload in background
            self.loading = True
            self.root.after(100, self.start_loading_data)
    
    def _on_backup_profile(self) -> None:
        """Handle backup button click."""
        print("[DEBUG GUI] _on_backup_profile called")
        
        # Check if a profile is selected
        selection = self.profiles_listbox.curselection()
        print(f"[DEBUG GUI] Selection: {selection}")
        
        if not selection:
            print("[DEBUG GUI] No profile selected")
            self.backup_status_var.set("Please select a profile first")
            self._widgets['backup_status_label'].config(foreground="red")
            return
        
        # Get selected profile folder
        folder_index = selection[0]
        print(f"[DEBUG GUI] Folder index: {folder_index}, total folders: {len(self.settings_folders)}")
        
        if folder_index >= len(self.settings_folders):
            print("[DEBUG GUI] Invalid folder index")
            self.backup_status_var.set("Invalid profile selection")
            self._widgets['backup_status_label'].config(foreground="red")
            return
        
        profile_folder = self.settings_folders[folder_index]
        print(f"[DEBUG GUI] Profile folder: {profile_folder}")
        
        # Update backup manager base path
        base_path = self.path_resolver.get_base_path()
        print(f"[DEBUG GUI] Base path: {base_path}")
        
        if not base_path:
            print("[DEBUG GUI] Could not determine base path")
            self.backup_status_var.set("Could not determine base path")
            self._widgets['backup_status_label'].config(foreground="red")
            return
        
        print("[DEBUG GUI] Setting backup manager base path")
        self.backup_manager.set_base_path(base_path)
        
        # Show in-progress status
        print("[DEBUG GUI] Updating UI to show 'Creating backup...'")
        self.backup_status_var.set("Creating backup...")
        self._widgets['backup_status_label'].config(foreground="blue")
        self.root.update_idletasks()
        
        # Store result in instance variable for periodic checking
        self._backup_result = None
        
        # Create backup in background thread
        def backup_thread():
            print("[DEBUG GUI] Backup thread started", flush=True)
            try:
                print("[DEBUG GUI] Calling backup_manager.create_backup...", flush=True)
                success, message, backup_path = self.backup_manager.create_backup(profile_folder)
                print(f"[DEBUG GUI] Backup result: success={success}, message={message}", flush=True)
                
                # Store result for main thread to pick up
                if success:
                    status_msg = f"✓ Completed: {message}"
                    self._backup_result = (status_msg, "green")
                else:
                    status_msg = f"✗ Failed: {message}"
                    self._backup_result = (status_msg, "red")
                
                print(f"[DEBUG GUI] Result stored: {self._backup_result}", flush=True)
                
            except Exception as e:
                print(f"[DEBUG GUI] Exception in backup thread: {type(e).__name__}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                error_msg = f"✗ Error: {str(e)[:50]}"
                self._backup_result = (error_msg, "red")
            finally:
                print("[DEBUG GUI] Backup thread finishing", flush=True)
        
        # Start checking for result
        def check_backup_result():
            print(f"[DEBUG GUI] Checking backup result: {self._backup_result}", flush=True)
            if self._backup_result is not None:
                status_msg, color = self._backup_result
                print(f"[DEBUG GUI] Updating UI: {status_msg} ({color})", flush=True)
                self.backup_status_var.set(status_msg)
                self._widgets['backup_status_label'].config(foreground=color)
                self._backup_result = None  # Reset
                print("[DEBUG GUI] UI updated successfully", flush=True)
            else:
                # Keep checking every 100ms
                self.root.after(100, check_backup_result)
        
        print("[DEBUG GUI] Starting backup thread", flush=True)
        thread = threading.Thread(target=backup_thread, daemon=True)
        thread.start()
        
        # Start checking for results after 100ms
        self.root.after(100, check_backup_result)
        print("[DEBUG GUI] Backup thread started, periodic check scheduled", flush=True)
    
    def _on_exit(self) -> None:
        """Handle Exit menu command."""
        self.root.quit()
    
    def _on_manage_paths(self) -> None:
        """Handle Manage Paths menu command."""
        show_custom_paths_dialog(self.root, self.data_file, self._on_custom_paths_changed)
    
    def _on_custom_paths_changed(self) -> None:
        """Handle custom paths being changed - reinitialize path resolver and reload data."""
        # Reinitialize path resolver with new custom paths
        custom_paths = self.data_file.get_custom_paths()
        self.path_resolver = EVEPathResolver(custom_paths=custom_paths)
        
        # Rediscover servers
        self.available_servers = self.path_resolver.discover_servers()
        
        # Update server dropdown
        server_names = sorted(self.available_servers.keys()) if self.available_servers else ['Tranquility']
        self.server_combo['values'] = server_names
        
        # Keep current server if still available, otherwise switch to first available
        if self.current_server not in self.available_servers:
            if self.available_servers:
                self.current_server = server_names[0]
                self.server_var.set(self.current_server)
        
        # Reload data
        self.status_label.config(text="Reloading after path changes...", foreground="blue")
        self.progress.grid()
        self.progress.start(10)
        
        # Clear current data
        self.profiles_listbox.delete(0, tk.END)
        self.chars_tree.delete(*self.chars_tree.get_children())
        self.accounts_tree.delete(*self.accounts_tree.get_children())
        self.path_var.set("")
        
        # Reload in background
        self.loading = True
        self.root.after(100, self.start_loading_data)
    
    def _on_sort_changed(self, *args) -> None:
        """Handle default sorting preference change."""
        sort_pref = self.sort_var.get()
        try:
            self.data_file.set_default_sorting(sort_pref)
            self.data_file.save()
            
            # Apply sorting to current view
            self._apply_default_sorting()
        except ValidationError as e:
            messagebox.showerror("Invalid Sort Option", str(e))
    
    def _apply_default_sorting(self) -> None:
        """Apply default sorting to treeviews based on saved preference."""
        sort_pref = self.sort_var.get()
        
        # Parse the sorting preference
        if sort_pref.startswith('name_'):
            column = 'name'
            reverse = sort_pref.endswith('_desc')
        elif sort_pref.startswith('id_'):
            column = 'id'
            reverse = sort_pref.endswith('_desc')
        elif sort_pref.startswith('date_'):
            column = 'date'
            reverse = sort_pref.endswith('_desc')
        else:
            column = 'name'
            reverse = False
        
        # Apply to characters tree
        sort_tree(self.chars_tree, column, reverse)
        
        # For accounts tree, only id and date are available
        if column in ['id', 'date']:
            sort_tree(self.accounts_tree, column, reverse)
    
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
                text="No EVE settings directories found. Use Settings → Manage Paths to add custom paths.",
                foreground="orange"
            )
            messagebox.showwarning("No Directories Found", 
                               "Could not find EVE settings directories.\n\n"
                               "Use Settings → Manage Paths to add custom EVE installation paths.")
            return
        
        if not self.manager.user_list or not self.manager.char_list:
            self.status_label.config(
                text="Warning: Missing user or char files in found directories.",
                foreground="orange"
            )
            messagebox.showwarning("Incomplete Data", 
                               "Some directories are missing user or char files.\n\n"
                               f"Searched in:\n" + "\n".join(str(f) for f in self.settings_folders) +
                               "\n\nUse Settings → Manage Paths to add different paths.")
            # Still show the profiles list
            for folder in self.settings_folders:
                self.profiles_listbox.insert(tk.END, folder.name)
            return
        
        # Update status label
        folders_text = f"Found {len(self.settings_folders)} settings folder(s)"
        self.status_label.config(text=folders_text, foreground="gray")
        
        # Populate profiles listbox
        for folder in self.settings_folders:
            self.profiles_listbox.insert(tk.END, folder.name)
        
        # Select first profile by default
        self.profiles_listbox.selection_set(0)
        self.selected_folder = self.settings_folders[0]
        self.handlers.update_character_lists()
        
        # Apply default sorting after data is loaded
        self._apply_default_sorting()
    
    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()
