"""
Dialog windows for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from datetime import datetime
from utils.models import SettingFile, get_character_note, get_account_note
from .helpers import sort_tree, center_dialog


def show_character_selection_dialog(parent, source_char: SettingFile, all_chars: List[SettingFile], 
                                    manager, sort_tree_func) -> None:
    """Show dialog to select specific characters to overwrite"""
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
    tree = ttk.Treeview(tree_frame, columns=('id', 'name', 'date', 'note'), 
                       show='tree headings', selectmode='extended')
    tree.heading('#0', text='☐', anchor='w')  # Checkbox column
    tree.heading('id', text='ID', command=lambda: sort_tree(tree, 'id', False))
    tree.heading('name', text='Name', command=lambda: sort_tree(tree, 'name', False))
    tree.heading('date', text='Last Modified', command=lambda: sort_tree(tree, 'date', False))
    tree.heading('note', text='Note', command=lambda: sort_tree(tree, 'note', False))
    
    tree.column('#0', width=30, stretch=False)
    tree.column('id', width=100, anchor='center')
    tree.column('name', width=150, anchor='w')
    tree.column('date', width=140, anchor='center')
    tree.column('note', width=120, anchor='w')
    
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Populate with other characters
    target_chars = []
    for char in all_chars:
        if char.id != source_char.id:  # Skip source
            mtime = char.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            note = get_character_note(char.id)
            
            tree.insert('', 'end', text='☐',
                       values=(char.id, char.get_char_name(), date_str, note),
                       tags=(str(char.id),))
            target_chars.append(char)
    
    # Sort by date initially
    sort_tree(tree, 'date', False)
    
    # Toggle selection on click
    def toggle_selection(event):
        item = tree.identify_row(event.y)
        if item:
            if tree.selection() and item in tree.selection():
                tree.selection_remove(item)
                tree.item(item, text='☐')
            else:
                tree.selection_add(item)
                tree.item(item, text='☑')
    
    tree.bind('<Button-1>', toggle_selection)
    
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


def show_account_selection_dialog(parent, source_user: SettingFile, all_users: List[SettingFile], 
                                  manager, sort_tree_func) -> None:
    """Show dialog to select specific accounts to overwrite"""
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
    tree = ttk.Treeview(tree_frame, columns=('id', 'date', 'note'), 
                       show='tree headings', selectmode='extended')
    tree.heading('#0', text='☐', anchor='w')  # Checkbox column
    tree.heading('id', text='ID', command=lambda: sort_tree(tree, 'id', False))
    tree.heading('date', text='Last Modified', command=lambda: sort_tree(tree, 'date', False))
    tree.heading('note', text='Note', command=lambda: sort_tree(tree, 'note', False))
    
    tree.column('#0', width=30, stretch=False)
    tree.column('id', width=100, anchor='center')
    tree.column('date', width=140, anchor='center')
    tree.column('note', width=120, anchor='w')
    
    tree.grid(row=0, column=0, sticky="nsew")
    
    scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Populate with other accounts
    target_users = []
    for user in all_users:
        if user.id != user_id:  # Skip source
            mtime = user.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            note = get_account_note(user.id)
            
            tree.insert('', 'end', text='☐',
                       values=(user.id, date_str, note),
                       tags=(str(user.id),))
            target_users.append(user)
    
    # Sort by date initially
    sort_tree(tree, 'date', False)
    
    # Toggle selection on click
    def toggle_selection(event):
        item = tree.identify_row(event.y)
        if item:
            if tree.selection() and item in tree.selection():
                tree.selection_remove(item)
                tree.item(item, text='☐')
            else:
                tree.selection_add(item)
                tree.item(item, text='☑')
    
    tree.bind('<Button-1>', toggle_selection)
    
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
