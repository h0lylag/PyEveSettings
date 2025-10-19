"""
Helper functions for GUI operations
"""

import tkinter as tk
from tkinter import ttk


def sort_tree(tree: ttk.Treeview, col: str, reverse: bool):
    """Sort treeview by column and update header with arrow indicator"""
    # Get all items
    items = [(tree.set(child, col), child) for child in tree.get_children('')]
    
    # Sort items - handle numeric IDs specially
    if col == 'id':
        items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=reverse)
    elif col == 'date':
        items.sort(key=lambda x: x[0], reverse=reverse)
    else:
        items.sort(key=lambda x: x[0].lower(), reverse=reverse)
    
    # Rearrange items in sorted positions
    for index, (val, child) in enumerate(items):
        tree.move(child, '', index)
    
    # Update all column headers to remove arrows
    column_names = {
        'id': 'ID',
        'name': 'Name',
        'date': 'Last Modified',
        'note': 'Note'
    }
    
    for column in tree['columns']:
        if column in column_names:
            # Remove any existing arrows from the header
            base_text = column_names[column]
            tree.heading(column, text=base_text)
    
    # Add arrow to the sorted column
    arrow = ' ▼' if reverse else ' ▲'
    tree.heading(col, text=column_names.get(col, col) + arrow)
    
    # Update heading to reverse sort next time
    tree.heading(col, command=lambda: sort_tree(tree, col, not reverse))


def center_window(window: tk.Tk):
    """Center the window on the screen"""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')


def center_dialog(dialog: tk.Toplevel, parent: tk.Tk, width: int, height: int):
    """Center a dialog above its parent window"""
    dialog.update_idletasks()
    
    # Get parent window position and size
    main_x = parent.winfo_x()
    main_y = parent.winfo_y()
    main_width = parent.winfo_width()
    main_height = parent.winfo_height()
    
    # Calculate centered position
    x = main_x + (main_width - width) // 2
    y = main_y + (main_height - height) // 2
    
    dialog.geometry(f"{width}x{height}+{x}+{y}")
