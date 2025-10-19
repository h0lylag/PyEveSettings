"""
Widget creation and layout for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk
from .helpers import sort_tree


def create_main_layout(root: tk.Tk) -> dict:
    """Create main GUI layout and return references to important widgets"""
    # Configure grid weights for responsive layout
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    
    # Main container
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.columnconfigure(0, weight=1, minsize=200)  # Profiles
    main_frame.columnconfigure(1, weight=2, minsize=400)  # Characters
    main_frame.columnconfigure(2, weight=2, minsize=400)  # Accounts
    main_frame.rowconfigure(2, weight=1)
    
    # Status bar at top
    status_label = ttk.Label(main_frame, text="Loading EVE settings...", foreground="blue")
    status_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
    
    # Path display field
    path_frame = ttk.Frame(main_frame)
    path_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
    path_frame.columnconfigure(1, weight=1)
    
    ttk.Label(path_frame, text="Profile Path:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
    path_var = tk.StringVar()
    path_entry = ttk.Entry(path_frame, textvariable=path_var, state='readonly', font=("Consolas", 9))
    path_entry.grid(row=0, column=1, sticky="ew")
    
    # Progress bar
    progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
    progress.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky="ew")
    progress.start(10)
    
    # Create profiles panel
    profiles_widgets = create_profiles_panel(main_frame)
    
    # Create characters panel
    chars_widgets = create_characters_panel(main_frame)
    
    # Create accounts panel
    accounts_widgets = create_accounts_panel(main_frame)
    
    # Return all widget references
    return {
        'status_label': status_label,
        'path_var': path_var,
        'path_entry': path_entry,
        'progress': progress,
        **profiles_widgets,
        **chars_widgets,
        **accounts_widgets
    }


def create_profiles_panel(parent: ttk.Frame) -> dict:
    """Create profiles panel (left column)"""
    profiles_frame = ttk.LabelFrame(parent, text="Profiles", padding="5")
    profiles_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 5))
    profiles_frame.rowconfigure(0, weight=1)
    profiles_frame.columnconfigure(0, weight=1)
    
    # Profiles listbox
    profiles_listbox = tk.Listbox(profiles_frame, selectmode=tk.SINGLE)
    profiles_listbox.grid(row=0, column=0, sticky="nsew")
    
    profiles_scroll = ttk.Scrollbar(profiles_frame, orient=tk.VERTICAL, command=profiles_listbox.yview)
    profiles_scroll.grid(row=0, column=1, sticky="ns")
    profiles_listbox.configure(yscrollcommand=profiles_scroll.set)
    
    return {'profiles_listbox': profiles_listbox}


def create_characters_panel(parent: ttk.Frame) -> dict:
    """Create characters panel (middle column)"""
    chars_frame = ttk.LabelFrame(parent, text="Characters", padding="5")
    chars_frame.grid(row=2, column=1, sticky="nsew", padx=5)
    chars_frame.rowconfigure(0, weight=1)
    chars_frame.columnconfigure(0, weight=1)
    
    # Characters treeview with sortable columns
    chars_tree = ttk.Treeview(chars_frame, columns=('id', 'name', 'date', 'note'), 
                              show='headings', selectmode='browse')
    chars_tree.heading('id', text='ID', command=lambda: sort_tree(chars_tree, 'id', False))
    chars_tree.heading('name', text='Name', command=lambda: sort_tree(chars_tree, 'name', False))
    chars_tree.heading('date', text='Last Modified', command=lambda: sort_tree(chars_tree, 'date', False))
    chars_tree.heading('note', text='Note', command=lambda: sort_tree(chars_tree, 'note', False))
    
    chars_tree.column('id', width=100, anchor='center')
    chars_tree.column('name', width=150, anchor='w')
    chars_tree.column('date', width=140, anchor='center')
    chars_tree.column('note', width=120, anchor='w')
    
    chars_tree.grid(row=0, column=0, sticky="nsew")
    
    chars_scroll = ttk.Scrollbar(chars_frame, orient=tk.VERTICAL, command=chars_tree.yview)
    chars_scroll.grid(row=0, column=1, sticky="ns")
    chars_tree.configure(yscrollcommand=chars_scroll.set)
    
    # Character buttons - will be connected to handlers later
    char_btn_frame = ttk.Frame(chars_frame)
    char_btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
    
    char_edit_btn = ttk.Button(char_btn_frame, text="Edit Note")
    char_edit_btn.pack(side=tk.LEFT, padx=2)
    
    char_overwrite_all_btn = ttk.Button(char_btn_frame, text="Overwrite All")
    char_overwrite_all_btn.pack(side=tk.LEFT, padx=2)
    
    char_overwrite_select_btn = ttk.Button(char_btn_frame, text="Overwrite...")
    char_overwrite_select_btn.pack(side=tk.LEFT, padx=2)
    
    return {
        'chars_tree': chars_tree,
        'char_edit_btn': char_edit_btn,
        'char_overwrite_all_btn': char_overwrite_all_btn,
        'char_overwrite_select_btn': char_overwrite_select_btn
    }


def create_accounts_panel(parent: ttk.Frame) -> dict:
    """Create accounts panel (right column)"""
    accounts_frame = ttk.LabelFrame(parent, text="Accounts", padding="5")
    accounts_frame.grid(row=2, column=2, sticky="nsew", padx=(5, 0))
    accounts_frame.rowconfigure(0, weight=1)
    accounts_frame.columnconfigure(0, weight=1)
    
    # Accounts treeview with sortable columns
    accounts_tree = ttk.Treeview(accounts_frame, columns=('id', 'date', 'note'), 
                                 show='headings', selectmode='browse')
    accounts_tree.heading('id', text='ID', command=lambda: sort_tree(accounts_tree, 'id', False))
    accounts_tree.heading('date', text='Last Modified', command=lambda: sort_tree(accounts_tree, 'date', False))
    accounts_tree.heading('note', text='Note', command=lambda: sort_tree(accounts_tree, 'note', False))
    
    accounts_tree.column('id', width=100, anchor='center')
    accounts_tree.column('date', width=140, anchor='center')
    accounts_tree.column('note', width=120, anchor='w')
    
    accounts_tree.grid(row=0, column=0, sticky="nsew")
    
    accounts_scroll = ttk.Scrollbar(accounts_frame, orient=tk.VERTICAL, command=accounts_tree.yview)
    accounts_scroll.grid(row=0, column=1, sticky="ns")
    accounts_tree.configure(yscrollcommand=accounts_scroll.set)
    
    # Account buttons - will be connected to handlers later
    account_btn_frame = ttk.Frame(accounts_frame)
    account_btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
    
    account_edit_btn = ttk.Button(account_btn_frame, text="Edit Note")
    account_edit_btn.pack(side=tk.LEFT, padx=2)
    
    account_overwrite_all_btn = ttk.Button(account_btn_frame, text="Overwrite All")
    account_overwrite_all_btn.pack(side=tk.LEFT, padx=2)
    
    account_overwrite_select_btn = ttk.Button(account_btn_frame, text="Overwrite...")
    account_overwrite_select_btn.pack(side=tk.LEFT, padx=2)
    
    return {
        'accounts_tree': accounts_tree,
        'account_edit_btn': account_edit_btn,
        'account_overwrite_all_btn': account_overwrite_all_btn,
        'account_overwrite_select_btn': account_overwrite_select_btn
    }
