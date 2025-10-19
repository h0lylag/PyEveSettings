"""Backup Manager window for PyEveSettings.

Provides comprehensive backup management including:
- View all backups across installations and servers
- Create new backups
- Restore existing backups
- Delete old backups
- Filter by installation, server, and profile
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import threading
import platform
import subprocess
import queue

from utils import BackupManager, EVEPathResolver
from .helpers import center_dialog
from .backup_dialogs import CreateBackupDialog, RestoreBackupDialog, ViewDetailsDialog
from .backup_operations import BackupOperations
import config


class BackupManagerWindow:
    """Backup Manager dialog window."""
    
    def __init__(self, parent: tk.Tk, path_resolver: EVEPathResolver, current_server: Optional[str] = None):
        """Initialize the Backup Manager window.
        
        Args:
            parent: Parent window.
            path_resolver: EVEPathResolver instance for discovering installations.
            current_server: Currently selected server in main window.
        """
        self.parent = parent
        self.path_resolver = path_resolver
        self.current_server = current_server or 'Tranquility'
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title("Backup Manager - PyEveSettings")

        default_width = config.BACKUP_MANAGER_WINDOW_WIDTH
        default_height = config.BACKUP_MANAGER_WINDOW_HEIGHT

        self.window.geometry(f"{default_width}x{default_height}")
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Data storage
        self.all_backups: List[Dict] = []
        self.filtered_backups: List[Dict] = []
        self.backup_directories: List[Dict] = []
        self.installations: List[Path] = []
        
        # Operation state
        self.operation_in_progress = False
        self.operation_thread: Optional[threading.Thread] = None
        self._result_queue: queue.Queue = queue.Queue()
        
        # Create GUI
        self._create_widgets()
        self._setup_event_handlers()
        self._start_result_poller()
        
        # Center window
        self.window.update_idletasks()
        center_dialog(self.window, parent, default_width, default_height)
        
        # Load initial data
        self.window.after(100, self._load_backups)
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Treeview row expands
        
        # Create sections
        self._create_filter_section(main_frame)
        self._create_stats_section(main_frame)
        self._create_backup_list_section(main_frame)
        self._create_button_section(main_frame)
        self._create_status_section(main_frame)
    
    def _create_filter_section(self, parent: ttk.Frame):
        """Create the filter controls section."""
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding="5")
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        filter_frame.columnconfigure(5, weight=1)
        
        # Installation filter
        ttk.Label(filter_frame, text="Installation:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.installation_var = tk.StringVar(value="All")
        self.installation_combo = ttk.Combobox(filter_frame, textvariable=self.installation_var, 
                                               state='readonly', width=30)
        self.installation_combo.grid(row=0, column=1, padx=(0, 10), sticky="ew")
        
        # Server filter
        ttk.Label(filter_frame, text="Server:").grid(row=0, column=2, padx=(0, 5), sticky="w")
        self.server_var = tk.StringVar(value="All")
        self.server_combo = ttk.Combobox(filter_frame, textvariable=self.server_var, 
                                         state='readonly', width=20)
        self.server_combo.grid(row=0, column=3, padx=(0, 10), sticky="ew")
        
        # Profile filter
        ttk.Label(filter_frame, text="Profile:").grid(row=0, column=4, padx=(0, 5), sticky="w")
        self.profile_var = tk.StringVar(value="All")
        self.profile_combo = ttk.Combobox(filter_frame, textvariable=self.profile_var, 
                                          state='readonly', width=20)
        self.profile_combo.grid(row=0, column=5, padx=(0, 10), sticky="ew")
        
        # Buttons
        button_frame = ttk.Frame(filter_frame)
        button_frame.grid(row=0, column=6, padx=(10, 0))
        
        self.refresh_btn = ttk.Button(button_frame, text="Refresh", width=10)
        self.refresh_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.clear_filters_btn = ttk.Button(button_frame, text="Clear Filters", width=12)
        self.clear_filters_btn.grid(row=0, column=1)
    
    def _create_stats_section(self, parent: ttk.Frame):
        """Create the statistics display section."""
        stats_frame = ttk.Frame(parent)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        self.stats_label = ttk.Label(stats_frame, text="Loading backups...", foreground="blue")
        self.stats_label.grid(row=0, column=0, sticky="w")
    
    def _create_backup_list_section(self, parent: ttk.Frame):
        """Create the backup list treeview section."""
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Create Treeview
        columns = ('profile', 'datetime', 'size', 'files', 'server', 'installation')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        
        # Define column headings and widths
        self.tree.heading('profile', text='Profile Name')
        self.tree.heading('datetime', text='Backup Date/Time')
        self.tree.heading('size', text='Size')
        self.tree.heading('files', text='Files')
        self.tree.heading('server', text='Server')
        self.tree.heading('installation', text='Installation Path')
        
        self.tree.column('profile', width=150)
        self.tree.column('datetime', width=140)
        self.tree.column('size', width=80)
        self.tree.column('files', width=60)
        self.tree.column('server', width=100)
        self.tree.column('installation', width=250)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=hsb.set)
    
    def _create_button_section(self, parent: ttk.Frame):
        """Create the action buttons section."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.grid(row=0, column=0, sticky="w")
        
        self.create_btn = ttk.Button(left_buttons, text="Create Backup", width=15)
        self.create_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.restore_btn = ttk.Button(left_buttons, text="Restore Backup", width=15, state='disabled')
        self.restore_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.delete_btn = ttk.Button(left_buttons, text="Delete Backup", width=15, state='disabled')
        self.delete_btn.grid(row=0, column=2, padx=(0, 5))
        
        self.details_btn = ttk.Button(left_buttons, text="View Details", width=15, state='disabled')
        self.details_btn.grid(row=0, column=3, padx=(0, 5))
        
        self.open_folder_btn = ttk.Button(left_buttons, text="Open Folder", width=15, state='disabled')
        self.open_folder_btn.grid(row=0, column=4)
        
        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.grid(row=0, column=1, sticky="e")
        button_frame.columnconfigure(1, weight=1)
        
        self.close_btn = ttk.Button(right_buttons, text="Close", width=10)
        self.close_btn.grid(row=0, column=0)
    
    def _create_status_section(self, parent: ttk.Frame):
        """Create the status bar section."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, sticky="ew")
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, sticky="ew")
    
    def _setup_event_handlers(self):
        """Connect event handlers to widgets."""
        # Filter combobox events
        self.installation_combo.bind('<<ComboboxSelected>>', self._on_filter_changed)
        self.server_combo.bind('<<ComboboxSelected>>', self._on_filter_changed)
        self.profile_combo.bind('<<ComboboxSelected>>', self._on_filter_changed)
        
        # Button events
        self.refresh_btn.config(command=self._on_refresh)
        self.clear_filters_btn.config(command=self._on_clear_filters)
        self.create_btn.config(command=self._on_create_backup)
        self.restore_btn.config(command=self._on_restore_backup)
        self.delete_btn.config(command=self._on_delete_backup)
        self.details_btn.config(command=self._on_view_details)
        self.open_folder_btn.config(command=self._on_open_folder)
        self.close_btn.config(command=self._on_close)
        
        # Treeview events
        self.tree.bind('<<TreeviewSelect>>', self._on_selection_changed)
        self.tree.bind('<Double-Button-1>', self._on_double_click)
        
        # Window close event
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    # Event Handlers
    
    def _on_filter_changed(self, event=None):
        """Handle filter selection change."""
        self._apply_filters()
    
    def _on_clear_filters(self):
        """Clear all filters."""
        self.installation_var.set("All")
        self.server_var.set("All")
        self.profile_var.set("All")
        self._apply_filters()
    
    def _on_refresh(self):
        """Refresh the backup list."""
        self._load_backups()
    
    def _on_selection_changed(self, event=None):
        """Handle treeview selection change."""
        selection = self.tree.selection()
        has_selection = len(selection) > 0
        
        # Enable/disable buttons based on selection
        state = 'normal' if has_selection else 'disabled'
        self.restore_btn.config(state=state)
        self.delete_btn.config(state=state)
        self.details_btn.config(state=state)
        self.open_folder_btn.config(state=state)
    
    def _on_double_click(self, event=None):
        """Handle double-click on backup item."""
        if self.tree.selection():
            self._on_view_details()
    
    def _on_create_backup(self):
        """Handle Create Backup button."""
        if not self.backup_directories:
            messagebox.showerror("No Backup Directories", 
                               "No backup directories found. Please ensure you have EVE installations configured.")
            return
        
        # Show dialog using CreateBackupDialog
        CreateBackupDialog(self.window, self.backup_directories, self._start_backup_creation)
    
    def _start_backup_creation(self, profile_path: Path, backup_dir: Path):
        """Start backup creation process."""
        self._set_status("Creating backup...", "blue")
        self.progress.start(10)
        self._set_controls_state('disabled')
        
        def on_success(message: str):
            self._enqueue_result(self._on_create_success, message)
        
        def on_error(error: str):
            self._enqueue_result(self._on_create_error, error)
        
        def on_complete():
            self._enqueue_result(self._on_create_complete)
        
        BackupOperations.create_backup(profile_path, backup_dir, on_success, on_error, on_complete)
    
    def _on_create_success(self, message: str):
        """Handle successful backup creation (main thread)."""
        # Message expected to already contain success prefix (e.g., "✓ Backup created: ...")
        self._set_status(message, "green")
        self.window.after(150, self._load_backups)

    def _on_create_error(self, error: str):
        """Handle backup creation errors (main thread)."""
        self._set_status(error, "red")

    def _on_create_complete(self):
        """Handle create backup completion."""
        self.progress.stop()
        self._set_controls_state('normal')
    
    def _on_restore_backup(self):
        """Handle Restore Backup button."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected backup
        item = selection[0]
        backup_path_str = self.tree.item(item, 'tags')[0]
        backup_path = Path(backup_path_str)
        
        # Find the backup metadata
        backup_meta = None
        for backup in self.filtered_backups:
            if backup.get('path') == backup_path:
                backup_meta = backup
                break
        
        if not backup_meta:
            messagebox.showerror("Error", "Could not find backup metadata.")
            return
        
        # Validate backup integrity first
        manager = BackupManager()
        is_valid, msg = manager.validate_backup_integrity(backup_path)
        
        if not is_valid:
            messagebox.showerror("Invalid Backup", f"Backup file is invalid or corrupted:\n\n{msg}")
            return
        
        # Show restore dialog using RestoreBackupDialog
        RestoreBackupDialog(self.window, backup_meta, lambda restore_to: self._start_backup_restore(backup_path, restore_to))
    
    def _start_backup_restore(self, backup_path: Path, restore_to: Optional[Path]):
        """Start backup restore process."""
        self._set_status("Restoring backup...", "blue")
        self.progress.start(10)
        self._set_controls_state('disabled')
        
        def on_success(message: str):
            self._enqueue_result(self._on_restore_success, message)
        
        def on_error(error: str):
            self._enqueue_result(self._on_restore_error, error)
        
        def on_complete():
            self._enqueue_result(self._on_restore_complete)
        
        BackupOperations.restore_backup(backup_path, restore_to, on_success, on_error, on_complete)
    
    def _on_restore_success(self, message: str):
        """Handle successful backup restore (main thread)."""
        self._set_status(message, "green")
        messagebox.showinfo("Restore Complete", message)

    def _on_restore_error(self, error: str):
        """Handle backup restore errors (main thread)."""
        self._set_status(error, "red")
        messagebox.showerror("Restore Failed", error)

    def _on_restore_complete(self):
        """Handle restore backup completion."""
        self.progress.stop()
        self._set_controls_state('normal')
    
    def _on_delete_backup(self):
        """Handle Delete Backup button."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected backup
        item = selection[0]
        values = self.tree.item(item, 'values')
        backup_path_str = self.tree.item(item, 'tags')[0]
        backup_path = Path(backup_path_str)
        
        # Find the backup metadata
        backup_meta = None
        for backup in self.filtered_backups:
            if backup.get('path') == backup_path:
                backup_meta = backup
                break
        
        # Confirmation dialog
        confirm_msg = f"Are you sure you want to delete this backup?\n\n"
        confirm_msg += f"Profile: {values[0]}\n"
        confirm_msg += f"Date: {values[1]}\n"
        confirm_msg += f"Size: {values[2]}\n\n"
        confirm_msg += "This action cannot be undone."
        
        if not messagebox.askyesno("Confirm Delete", confirm_msg):
            return
        
        # Delete the backup
        manager = BackupManager()
        success, message = manager.delete_backup(backup_path)
        
        if success:
            self._set_status(f"✓ {message}", "green")
            # Reload backups
            self._load_backups()
        else:
            self._set_status(f"✗ {message}", "red")
            messagebox.showerror("Delete Failed", message)
    
    def _on_view_details(self):
        """Handle View Details button."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected backup
        item = selection[0]
        backup_path_str = self.tree.item(item, 'tags')[0]
        backup_path = Path(backup_path_str)
        
        # Find the backup metadata
        backup_meta = None
        for backup in self.filtered_backups:
            if backup.get('path') == backup_path:
                backup_meta = backup
                break
        
        if not backup_meta:
            messagebox.showerror("Error", "Could not find backup metadata.")
            return
        
        # Show details dialog using ViewDetailsDialog
        ViewDetailsDialog(self.window, backup_meta)
    
    def _on_open_folder(self):
        """Handle Open Folder button."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected backup
        item = selection[0]
        backup_path_str = self.tree.item(item, 'tags')[0]
        backup_path = Path(backup_path_str)
        
        # Open the folder containing the backup
        import subprocess
        import sys
        
        folder_path = backup_path.parent
        
        try:
            if sys.platform == 'win32':
                subprocess.run(['explorer', '/select,', str(backup_path)])
            elif sys.platform == 'darwin':
                subprocess.run(['open', '-R', str(backup_path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(folder_path)])
            self._set_status(f"Opened folder: {folder_path.name}", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")
    
    def _on_close(self):
        """Handle Close button and window close."""
        self.window.grab_release()
        self.window.destroy()
    
    # Data Loading and Display
    
    def _load_backups(self):
        """Load all backups from all installations."""
        print("[DEBUG] _load_backups() called", flush=True)
        self._set_status("Loading backups...", "blue")
        self.progress.start(10)
        self._set_controls_state('disabled')
        
        # Get search paths
        base_path = self.path_resolver.get_base_path()
        search_paths = [base_path] if base_path else []
        if hasattr(self.path_resolver, 'custom_paths'):
            search_paths.extend(self.path_resolver.custom_paths)
        
        def on_success(backup_data: tuple):
            self._enqueue_result(self._on_backups_loaded, backup_data)
        
        def on_error(error: str):
            self._enqueue_result(self._set_status, error, "red")
        
        def on_complete():
            self._enqueue_result(self._on_load_complete)
        
        print("[DEBUG] Starting BackupOperations.load_backups()", flush=True)
        BackupOperations.load_backups(search_paths, on_success, on_error, on_complete)
    
    def _enqueue_result(self, callback, *args):
        """Enqueue a callback to be executed on the main thread."""
        self._result_queue.put((callback, args))

    def _start_result_poller(self) -> None:
        """Start polling the result queue for background thread callbacks."""
        self.window.after(50, self._poll_result_queue)

    def _poll_result_queue(self) -> None:
        """Process queued callbacks from background threads."""
        try:
            while True:
                callback, args = self._result_queue.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        finally:
            self.window.after(50, self._poll_result_queue)
    
    def _on_backups_loaded(self, backup_data: tuple):
        """Handle backups loaded successfully (called on main thread)."""
        print(f"[DEBUG] _on_backups_loaded called, data type: {type(backup_data)}", flush=True)
        backup_directories, all_backups = backup_data
        print(f"[DEBUG] Unpacked: {len(backup_directories)} dirs, {len(all_backups)} backups", flush=True)
        self.backup_directories = backup_directories
        self.all_backups = all_backups
        print("[DEBUG] Calling _update_backup_display()", flush=True)
        self._update_backup_display()
        print("[DEBUG] _update_backup_display() returned", flush=True)
    
    def _on_load_complete(self):
        """Handle load operation complete (called on main thread)."""
        print("[DEBUG] _on_load_complete called", flush=True)
        self.progress.stop()
        self._set_controls_state('normal')
        print("[DEBUG] Progress stopped, controls enabled", flush=True)
    
    def _update_backup_display(self):
        """Update the display with loaded backups."""
        try:
            # Update filter options
            self._update_filter_options()
            
            # Apply current filters
            self._apply_filters()
            
            # Update stats
            self._update_stats()
            
            self._set_status(f"Loaded {len(self.all_backups)} backup(s)", "green")
        except Exception as e:
            self._set_status(f"Error updating display: {e}", "red")
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
    
    def _update_filter_options(self):
        """Update filter combobox options based on loaded data."""
        # Extract unique installations
        installations = set()
        for backup in self.all_backups:
            if 'installation_path' in backup:
                installations.add(str(backup['installation_path']))
        
        installation_list = ['All'] + sorted(list(installations))
        self.installation_combo['values'] = installation_list
        
        # Extract unique servers
        servers = set()
        for backup in self.all_backups:
            if 'server' in backup:
                servers.add(backup['server'])
        
        server_list = ['All'] + sorted(list(servers))
        self.server_combo['values'] = server_list
        
        # Extract unique profiles
        profiles = set()
        for backup in self.all_backups:
            if 'profile_name' in backup:
                profiles.add(backup['profile_name'])
        
        profile_list = ['All'] + sorted(list(profiles))
        self.profile_combo['values'] = profile_list
    
    def _apply_filters(self):
        """Apply current filters and update treeview."""
        installation = self.installation_var.get()
        server = self.server_var.get()
        profile = self.profile_var.get()
        
        # Filter backups
        self.filtered_backups = []
        for backup in self.all_backups:
            # Check filters
            if installation != "All" and str(backup.get('installation_path', '')) != installation:
                continue
            if server != "All" and backup.get('server', '') != server:
                continue
            if profile != "All" and backup.get('profile_name', '') != profile:
                continue
            
            self.filtered_backups.append(backup)
        
        # Update treeview
        self._populate_treeview()
        
        # Update stats
        self._update_stats()
    
    def _populate_treeview(self):
        """Populate treeview with filtered backups."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered backups
        for backup in self.filtered_backups:
            # Format datetime
            dt_str = ""
            if backup.get('datetime'):
                dt_str = backup['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            
            # Format size
            size_str = f"{backup.get('size_mb', 0):.1f} MB"
            
            # Format file count
            files_str = str(backup.get('file_count', 0))
            
            # Get installation path (show basename only)
            inst_path = backup.get('installation_path', 'Unknown')
            if isinstance(inst_path, Path):
                inst_path = str(inst_path.name) if inst_path.name else str(inst_path)
            
            self.tree.insert('', 'end', values=(
                backup.get('profile_name', 'Unknown'),
                dt_str,
                size_str,
                files_str,
                backup.get('server', 'Unknown'),
                inst_path
            ), tags=(str(backup.get('path', '')),))
    
    def _update_stats(self):
        """Update statistics display."""
        count = len(self.filtered_backups)
        total_size = sum(b.get('size_mb', 0) for b in self.filtered_backups)
        
        if count == 0:
            self.stats_label.config(text="No backups found", foreground="gray")
        else:
            stats_text = f"{count} backup(s) | Total size: {total_size:.1f} MB"
            self.stats_label.config(text=stats_text, foreground="black")
    
    def _set_status(self, message: str, color: str = "black"):
        """Update status label.
        
        Args:
            message: Status message to display.
            color: Text color (blue, green, red, gray, black).
        """
        self.status_label.config(text=message, foreground=color)
    
    def _set_controls_state(self, state: str):
        """Enable or disable controls.
        
        Args:
            state: 'normal' or 'disabled'.
        """
        self.installation_combo.config(state='readonly' if state == 'normal' else 'disabled')
        self.server_combo.config(state='readonly' if state == 'normal' else 'disabled')
        self.profile_combo.config(state='readonly' if state == 'normal' else 'disabled')
        self.refresh_btn.config(state=state)
        self.clear_filters_btn.config(state=state)
        self.create_btn.config(state=state)
        self.close_btn.config(state=state)


def show_backup_manager(parent: tk.Tk, path_resolver: EVEPathResolver, current_server: Optional[str] = None):
    """Show the Backup Manager window.
    
    Args:
        parent: Parent window.
        path_resolver: EVEPathResolver instance.
        current_server: Currently selected server.
    """
    BackupManagerWindow(parent, path_resolver, current_server)
