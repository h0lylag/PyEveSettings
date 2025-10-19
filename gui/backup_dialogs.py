"""Dialog windows for backup manager.

Contains dialog classes for creating, restoring, and viewing backup details.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List, Dict, Callable
import zipfile

import config
from utils import BackupManager
from .helpers import center_dialog


class CreateBackupDialog:
    """Dialog for selecting a profile to backup."""
    
    def __init__(self, parent, backup_directories: List[Dict], on_create: Callable):
        """Initialize create backup dialog.
        
        Args:
            parent: Parent window.
            backup_directories: List of backup directory info dicts.
            on_create: Callback(profile_path, backup_dir) called when user confirms.
        """
        self.on_create = on_create
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Create Backup")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Main frame
        frame = ttk.Frame(self.dialog, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Instructions
        ttk.Label(frame, text="Select a profile to backup:", 
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Listbox with profiles
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.listbox = tk.Listbox(list_frame, selectmode='single')
        self.listbox.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # Populate with profiles
        self.profiles = []
        for backup_dir_info in backup_directories:
            parent_dir = backup_dir_info['parent_dir']
            server_name = backup_dir_info['server_name']
            
            # Find settings folders
            if parent_dir.exists():
                for item in parent_dir.iterdir():
                    if item.is_dir() and item.name.startswith('settings'):
                        profile_display = f"{item.name} ({server_name})"
                        self.profiles.append((profile_display, item, backup_dir_info['backup_dir']))
                        self.listbox.insert(tk.END, profile_display)
        
        if not self.profiles:
            self.listbox.insert(tk.END, "No profiles found")
            self.listbox.config(state='disabled')
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, sticky="e", pady=(10, 0))
        
        ttk.Button(button_frame, text="Create Backup", command=self._on_create, 
                  width=15).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy, 
                  width=10).grid(row=0, column=1)
        
        # Center dialog
        self._center_dialog(parent, 500, 400)
    
    def _on_create(self):
        """Handle Create button click."""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a profile to backup.")
            return
        
        profile_display, profile_path, backup_dir = self.profiles[selection[0]]
        self.dialog.destroy()
        self.on_create(profile_path, backup_dir)
    
    def _center_dialog(self, parent, width: int, height: int):
        """Center dialog over parent."""
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")


class RestoreBackupDialog:
    """Dialog for restoring a backup."""
    
    def __init__(self, parent, backup_meta: Dict, on_restore: Callable):
        """Initialize restore backup dialog.
        
        Args:
            parent: Parent window.
            backup_meta: Backup metadata dictionary.
            on_restore: Callback(restore_to_path) called when user confirms.
        """
        self.backup_meta = backup_meta
        self.on_restore = on_restore

        default_width = config.RESTORE_DIALOG_WIDTH
        default_height = config.RESTORE_DIALOG_HEIGHT

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Restore Backup")
        self.dialog.geometry(f"{default_width}x{default_height}")
        self.dialog.minsize(default_width, default_height)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding="12")
        frame.grid(row=0, column=0, sticky="nsew")
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Show backup info
        info_text = "Restore backup:\n\n"
        info_text += f"Profile: {backup_meta.get('profile_name', 'Unknown')}\n"
        dt = backup_meta.get('datetime')
        info_text += f"Date: {dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'Unknown'}\n"
        info_text += f"Size: {backup_meta.get('size_mb', 0):.1f} MB\n"
        info_text += f"Files: {backup_meta.get('file_count', 0)}\n\n"
        info_text += "Choose restore location:"

        ttk.Label(frame, text=info_text, justify="left", anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.restore_option = tk.StringVar(value="new")
        ttk.Radiobutton(
            frame,
            text="Restore to new profile (recommended)",
            variable=self.restore_option,
            value="new"
        ).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(
            frame,
            text="Overwrite original profile (⚠ Warning: will replace existing files)",
            variable=self.restore_option,
            value="overwrite"
        ).grid(row=2, column=0, sticky="w", pady=(5, 0))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, sticky="e", pady=(20, 0))

        ttk.Button(button_frame, text="Restore", command=self._on_restore, width=12).grid(
            row=0, column=0, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy, width=10).grid(
            row=0, column=1
        )

        # Center dialog
        self._center_dialog(parent, default_width, default_height)
    
    def _on_restore(self):
        """Handle Restore button click."""
        backup_path = self.backup_meta.get('path')
        if not backup_path:
            messagebox.showerror("Error", "Backup path not found.")
            return
        
        restore_to = None
        
        if self.restore_option.get() == "overwrite":
            # Confirm overwrite
            confirm = messagebox.askyesno("Confirm Overwrite", 
                "Are you sure you want to overwrite the existing profile?\n\n"
                "This will replace all files in the profile folder.")
            if not confirm:
                return
            
            # Set restore path to original location
            restore_to = backup_path.parent.parent / self.backup_meta.get('profile_name', 'settings_Default')
        
        self.dialog.destroy()
        self.on_restore(restore_to)
    
    def _center_dialog(self, parent, width: int, height: int):
        """Center dialog over parent."""
        center_dialog(self.dialog, parent, width, height)


class ViewDetailsDialog:
    """Dialog for viewing backup details."""
    
    def __init__(self, parent, backup_meta: Dict):
        """Initialize view details dialog.
        
        Args:
            parent: Parent window.
            backup_meta: Backup metadata dictionary.
        """
        self.backup_meta = backup_meta
        backup_path = backup_meta.get('path')
        
        if not backup_path:
            messagebox.showerror("Error", "Backup path not found.")
            return
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Backup Details")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        frame = ttk.Frame(self.dialog, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(frame)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text = tk.Text(text_frame, wrap=tk.WORD, width=70, height=25)
        self.text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scrollbar.set)
        
        # Build details text
        if isinstance(backup_path, Path):
            details = self._build_details_text(backup_path)
            self.text.insert('1.0', details)
        else:
            self.text.insert('1.0', "Error: Invalid backup path")
        self.text.config(state='disabled')
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, sticky="e", pady=(10, 0))
        
        ttk.Button(button_frame, text="Copy Path", command=self._copy_path, 
                  width=12).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy, 
                  width=10).grid(row=0, column=1)
        
        # Center dialog
        self._center_dialog(parent, 600, 500)
    
    def _build_details_text(self, backup_path: Path) -> str:
        """Build the details text content."""
        details = "BACKUP DETAILS\n"
        details += "=" * 60 + "\n\n"
        details += f"Filename: {backup_path.name}\n"
        details += f"Profile Name: {self.backup_meta.get('profile_name', 'Unknown')}\n"
        details += f"Server: {self.backup_meta.get('server', 'Unknown')}\n"
        details += f"Installation: {self.backup_meta.get('installation_path', 'Unknown')}\n\n"
        
        if self.backup_meta.get('datetime'):
            details += f"Created: {self.backup_meta['datetime'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        details += f"Size: {self.backup_meta.get('size_mb', 0):.2f} MB ({self.backup_meta.get('size_bytes', 0):,} bytes)\n"
        details += f"File Count: {self.backup_meta.get('file_count', 0)}\n"
        details += f"Valid: {'Yes' if self.backup_meta.get('is_valid') else 'No'}\n\n"
        
        details += f"Full Path:\n{backup_path}\n\n"
        
        # Try to list files in backup
        details += "=" * 60 + "\n"
        details += "FILES IN BACKUP (first 50):\n"
        details += "=" * 60 + "\n\n"
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                files = zipf.namelist()[:50]
                for file in files:
                    details += f"  {file}\n"
                if len(zipf.namelist()) > 50:
                    details += f"\n  ... and {len(zipf.namelist()) - 50} more files\n"
        except Exception as e:
            details += f"  Error reading backup contents: {e}\n"
        
        return details
    
    def _copy_path(self):
        """Copy backup path to clipboard."""
        backup_path = self.backup_meta.get('path')
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(str(backup_path))
        messagebox.showinfo("Copied", "Backup path copied to clipboard.")
    
    def _center_dialog(self, parent, width: int, height: int):
        """Center dialog over parent."""
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
