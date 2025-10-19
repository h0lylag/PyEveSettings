"""Dialog windows for py-eve-settings."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Callable, Tuple
from datetime import datetime
from pathlib import Path
from utils.models import SettingFile
from data import NotesManager
from .helpers import sort_tree, center_dialog
import config


def _create_selection_tree(
    parent: ttk.Frame,
    columns: Tuple[str, ...],
    headings: Tuple[str, ...],
    widths: Tuple[int, ...],
    sort_tree_func: Callable
) -> Tuple[ttk.Treeview, ttk.Scrollbar]:
    """Create a treeview with sortable columns for selection dialogs.
    
    Args:
        parent: Parent frame to contain the treeview.
        columns: Column identifiers.
        headings: Column heading texts.
        widths: Column widths.
        sort_tree_func: Function to call for sorting.
        
    Returns:
        Tuple of (treeview widget, scrollbar widget).
    """
    # Use extended selectmode for Ctrl/Shift multi-select
    tree = ttk.Treeview(parent, columns=columns, show='headings', selectmode='extended')
    
    # Configure data columns
    for i, (col, heading, width) in enumerate(zip(columns, headings, widths)):
        tree.heading(col, text=heading, command=lambda c=col: sort_tree_func(tree, c, False))
        tree.column(col, width=width, anchor='center' if i == 0 else 'w')
    
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scrollbar.set)
    
    return tree, scrollbar


def show_character_selection_dialog(
    parent: tk.Tk,
    source_char: SettingFile,
    all_chars: List[SettingFile],
    manager,
    sort_tree_func: Callable,
    notes_manager: Optional[NotesManager] = None
) -> None:
    """Show dialog to select specific characters to overwrite.
    
    Args:
        parent: Parent window.
        source_char: Source character whose settings will be copied.
        all_chars: List of all available characters.
        manager: Settings manager instance.
        sort_tree_func: Function for sorting treeview.
        notes_manager: Optional notes manager for displaying notes.
    """
    char_name = source_char.get_char_name()
    
    # Create selection dialog
    dialog = tk.Toplevel(parent)
    dialog.title("Select Characters to Overwrite")
    dialog.transient(parent)
    dialog.grab_set()
    
    # Main container with padding
    main_container = ttk.Frame(dialog, padding="15")
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Header
    tk.Label(main_container, text=f"Copy From: {char_name}", 
            font=("Segoe UI", 12, "bold"), foreground="#0066cc").pack(pady=(0, 5))
    tk.Label(main_container, text="Select target characters (use Ctrl/Shift+Click for multiple):", 
            font=("Segoe UI", 10)).pack(pady=(0, 5))
    
    # Treeview frame
    tree_frame = ttk.Frame(main_container)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)
    
    # Create treeview with sortable columns
    tree, scrollbar = _create_selection_tree(
        tree_frame,
        columns=('id', 'name', 'date', 'note'),
        headings=('ID', 'Name', 'Last Modified', 'Note'),
        widths=(100, 200, 150, 150),
        sort_tree_func=sort_tree_func
    )
    
    # Populate with other characters
    target_chars = []
    for char in all_chars:
        if char.id != source_char.id:  # Skip source
            mtime = char.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = notes_manager.get_character_note(str(char.id)) if notes_manager else ""
            
            tree.insert('', 'end',
                       values=(char.id, char.get_char_name(), date_str, note),
                       tags=(str(char.id),))
            target_chars.append(char)
    
    # Sort by date initially - most recent first
    sort_tree(tree, 'date', True)
    
    # Button frame
    btn_frame = ttk.Frame(main_container)
    btn_frame.pack(pady=(0, 0))
    
    def do_copy():
        selections = tree.selection()
        if not selections:
            messagebox.showwarning("No Selection", "Please select at least one character.")
            return
        
        # Get selected characters by matching IDs
        selected_ids = [int(tree.item(sel, 'values')[0]) for sel in selections]
        targets = [c for c in target_chars if c.id in selected_ids]
        
        # Build confirmation message with clear from/to lists
        target_names = [c.get_char_name() for c in targets]
        confirm_msg = f"Copy settings FROM:\n  • {char_name}\n\n"
        confirm_msg += f"TO these {len(target_names)} character(s):\n"
        for name in target_names:
            confirm_msg += f"  • {name}\n"
        confirm_msg += "\nThis will overwrite their current settings. Continue?"
        
        if not messagebox.askyesno("Confirm Overwrite", confirm_msg):
            return
        
        # Create temporary filtered list for copy operation
        original_list = manager.char_list
        manager.char_list = targets
        total_copied = manager.copy_settings(source_char)
        manager.char_list = original_list
        
        dialog.destroy()
        messagebox.showinfo("Success", f"Settings copied to {len(targets)} character(s)!")
    
    ttk.Button(btn_frame, text="Copy to Selected", command=do_copy).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    # Center dialog above main window
    center_dialog(dialog, parent, config.CHAR_SELECTION_DIALOG_WIDTH, config.CHAR_SELECTION_DIALOG_HEIGHT)


def show_account_selection_dialog(
    parent: tk.Tk,
    source_user: SettingFile,
    all_users: List[SettingFile],
    manager,
    sort_tree_func: Callable,
    notes_manager: Optional[NotesManager] = None
) -> None:
    """Show dialog to select specific accounts to overwrite.
    
    Args:
        parent: Parent window.
        source_user: Source account whose settings will be copied.
        all_users: List of all available accounts.
        manager: Settings manager instance.
        sort_tree_func: Function for sorting treeview.
        notes_manager: Optional notes manager for displaying notes.
    """
    user_id = source_user.id
    
    # Create selection dialog
    dialog = tk.Toplevel(parent)
    dialog.title("Select Accounts to Overwrite")
    dialog.transient(parent)
    dialog.grab_set()
    
    # Main container with padding
    main_container = ttk.Frame(dialog, padding="15")
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Header
    tk.Label(main_container, text=f"Copy From: Account {user_id}", 
            font=("Segoe UI", 12, "bold"), foreground="#0066cc").pack(pady=(0, 5))
    tk.Label(main_container, text="Select target accounts (use Ctrl/Shift+Click for multiple):", 
            font=("Segoe UI", 10)).pack(pady=(0, 5))
    
    # Treeview frame
    tree_frame = ttk.Frame(main_container)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)
    
    # Create treeview with sortable columns
    tree, scrollbar = _create_selection_tree(
        tree_frame,
        columns=('id', 'date', 'note'),
        headings=('ID', 'Last Modified', 'Note'),
        widths=(120, 180, 180),
        sort_tree_func=sort_tree_func
    )
    
    # Populate with other accounts
    target_users = []
    for user in all_users:
        if user.id != user_id:  # Skip source
            mtime = user.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = notes_manager.get_account_note(str(user.id)) if notes_manager else ""
            
            tree.insert('', 'end',
                       values=(user.id, date_str, note),
                       tags=(str(user.id),))
            target_users.append(user)
    
    # Sort by date initially - most recent first
    sort_tree(tree, 'date', True)
    
    # Button frame
    btn_frame = ttk.Frame(main_container)
    btn_frame.pack(pady=(0, 0))
    
    def do_copy():
        selections = tree.selection()
        if not selections:
            messagebox.showwarning("No Selection", "Please select at least one account.")
            return
        
        # Get selected accounts by matching IDs
        selected_ids = [int(tree.item(sel, 'values')[0]) for sel in selections]
        targets = [u for u in target_users if u.id in selected_ids]
        
        # Build confirmation message with clear from/to lists
        target_ids = [str(u.id) for u in targets]
        confirm_msg = f"Copy settings FROM:\n  • Account {user_id}\n\n"
        confirm_msg += f"TO these {len(target_ids)} account(s):\n"
        for tid in target_ids:
            confirm_msg += f"  • Account {tid}\n"
        confirm_msg += "\nThis will overwrite their current settings. Continue?"
        
        if not messagebox.askyesno("Confirm Overwrite", confirm_msg):
            return
        
        # Create temporary filtered list for copy operation
        original_list = manager.user_list
        manager.user_list = targets
        total_copied = manager.copy_settings(source_user)
        manager.user_list = original_list
        
        dialog.destroy()
        messagebox.showinfo("Success", f"Settings copied to {len(targets)} account(s)!")
    
    ttk.Button(btn_frame, text="Copy to Selected", command=do_copy).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    # Center dialog above main window
    center_dialog(dialog, parent, config.ACCOUNT_SELECTION_DIALOG_WIDTH, config.ACCOUNT_SELECTION_DIALOG_HEIGHT)


def show_custom_paths_dialog(parent: tk.Tk, data_file, on_paths_changed: Optional[Callable] = None) -> None:
    """Show dialog to manage custom EVE installation paths.
    
    Args:
        parent: Parent window.
        data_file: DataFile instance for loading/saving custom paths.
        on_paths_changed: Optional callback to call when paths are modified.
    """
    # Create dialog
    dialog = tk.Toplevel(parent)
    dialog.title("Manage Custom Paths")
    dialog.transient(parent)
    dialog.grab_set()
    
    # Main container with padding
    main_container = ttk.Frame(dialog, padding="15")
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Header
    tk.Label(main_container, text="Custom EVE Installation Paths", 
            font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
    tk.Label(main_container, text="Add directories containing EVE settings folders (e.g., c_ccp_eve_tq_tranquility):", 
            font=("Segoe UI", 9)).pack(pady=(0, 10))
    
    # Listbox frame
    list_frame = ttk.Frame(main_container)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)
    
    # Create listbox with scrollbar
    paths_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, font=("Consolas", 9))
    paths_listbox.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=paths_listbox.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    paths_listbox.configure(yscrollcommand=scrollbar.set)
    
    # Load existing custom paths
    custom_paths = data_file.get_custom_paths()
    for path in custom_paths:
        paths_listbox.insert(tk.END, path)
    
    # Button frame
    btn_frame = ttk.Frame(main_container)
    btn_frame.pack(pady=(0, 10))
    
    def add_path():
        """Add a new custom path."""
        directory = filedialog.askdirectory(
            parent=dialog,
            title="Select EVE Installation Directory",
            mustexist=True
        )
        if directory:
            path_obj = Path(directory)
            path_str = str(path_obj)
            
            # Check if path already exists
            if path_str in custom_paths:
                messagebox.showwarning("Duplicate Path", "This path is already in the list.")
                return
            
            # Verify path contains EVE server folders
            server_folders = [d for d in path_obj.iterdir() 
                            if d.is_dir() and d.name.startswith('c_ccp_eve_')]
            
            if not server_folders:
                result = messagebox.askyesno(
                    "No Server Folders Found",
                    f"No EVE server folders (c_ccp_eve_*) found in:\n{path_str}\n\n"
                    "Add this path anyway?"
                )
                if not result:
                    return
            
            # Add to list
            paths_listbox.insert(tk.END, path_str)
            custom_paths.append(path_str)
    
    def remove_path():
        """Remove selected path."""
        selection = paths_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a path to remove.")
            return
        
        index = selection[0]
        path_str = paths_listbox.get(index)
        
        # Confirm removal
        result = messagebox.askyesno(
            "Confirm Removal",
            f"Remove this path?\n\n{path_str}"
        )
        
        if result:
            paths_listbox.delete(index)
            custom_paths.remove(path_str)
    
    def save_and_close():
        """Save custom paths and close dialog."""
        try:
            data_file.set_custom_paths(custom_paths)
            data_file.save()
            dialog.destroy()
            
            # Notify parent that paths changed
            if on_paths_changed:
                on_paths_changed()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save custom paths:\n{e}")
    
    ttk.Button(btn_frame, text="Add Path...", command=add_path).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Remove", command=remove_path).pack(side=tk.LEFT, padx=5)
    
    # Bottom button frame
    bottom_frame = ttk.Frame(main_container)
    bottom_frame.pack()
    
    ttk.Button(bottom_frame, text="Save", command=save_and_close, width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(bottom_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
    
    # Center dialog above main window
    center_dialog(dialog, parent, config.CUSTOM_PATHS_DIALOG_WIDTH, config.CUSTOM_PATHS_DIALOG_HEIGHT)
