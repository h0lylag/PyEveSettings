"""Dialog windows for py-eve-settings."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable, Tuple
from datetime import datetime
from utils.models import SettingFile
from data import NotesManager
from .helpers import sort_tree, center_dialog


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
    tree = ttk.Treeview(parent, columns=columns, show='tree headings', selectmode='extended')
    
    # Configure checkbox column
    tree.heading('#0', text='☐', anchor='w')
    tree.column('#0', width=30, stretch=False)
    
    # Configure data columns
    for i, (col, heading, width) in enumerate(zip(columns, headings, widths)):
        tree.heading(col, text=heading, command=lambda c=col: sort_tree_func(tree, c, False))
        tree.column(col, width=width, anchor='center' if i == 0 else 'w')
    
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scrollbar.set)
    
    return tree, scrollbar


def _bind_toggle_selection(tree: ttk.Treeview) -> None:
    """Bind click handler to toggle selection in treeview.
    
    Args:
        tree: The treeview widget to bind to.
    """
    def toggle_selection(event: tk.Event) -> None:
        item = tree.identify_row(event.y)
        if item:
            if tree.selection() and item in tree.selection():
                tree.selection_remove(item)
                tree.item(item, text='☐')
            else:
                tree.selection_add(item)
                tree.item(item, text='☑')
    
    tree.bind('<Button-1>', toggle_selection)


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
    tk.Label(main_container, text=f"Source: {char_name}", 
            font=("Segoe UI", 10, "bold")).pack(pady=(0, 5))
    tk.Label(main_container, text="Select characters to receive settings:", 
            font=("Segoe UI", 9)).pack(pady=(0, 10))
    
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
        widths=(100, 150, 140, 120),
        sort_tree_func=sort_tree_func
    )
    
    # Populate with other characters
    target_chars = []
    for char in all_chars:
        if char.id != source_char.id:  # Skip source
            mtime = char.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = notes_manager.get_character_note(str(char.id)) if notes_manager else ""
            
            tree.insert('', 'end', text='☐',
                       values=(char.id, char.get_char_name(), date_str, note),
                       tags=(str(char.id),))
            target_chars.append(char)
    
    # Sort by date initially - most recent first
    sort_tree(tree, 'date', True)
    
    # Bind toggle selection handler
    _bind_toggle_selection(tree)
    
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
    center_dialog(dialog, parent, 650, 450)


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
    tk.Label(main_container, text=f"Source: Account {user_id}", 
            font=("Segoe UI", 10, "bold")).pack(pady=(0, 5))
    tk.Label(main_container, text="Select accounts to receive settings:", 
            font=("Segoe UI", 9)).pack(pady=(0, 10))
    
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
        widths=(100, 140, 120),
        sort_tree_func=sort_tree_func
    )
    
    # Populate with other accounts
    target_users = []
    for user in all_users:
        if user.id != user_id:  # Skip source
            mtime = user.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = notes_manager.get_account_note(str(user.id)) if notes_manager else ""
            
            tree.insert('', 'end', text='☐',
                       values=(user.id, date_str, note),
                       tags=(str(user.id),))
            target_users.append(user)
    
    # Sort by date initially - most recent first
    sort_tree(tree, 'date', True)
    
    # Bind toggle selection handler
    _bind_toggle_selection(tree)
    
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
    center_dialog(dialog, parent, 500, 450)
