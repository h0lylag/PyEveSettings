"""
Widget creation and layout for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk
from .helpers import sort_tree
import config


def create_menu_bar(root: tk.Tk) -> dict:
    """Create menu bar and return references to important menu items"""
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Exit")
    
    # Settings menu
    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Settings", menu=settings_menu)
    settings_menu.add_command(label="Manage Paths...")
    settings_menu.add_separator()
    
    # Default Sorting submenu
    sort_menu = tk.Menu(settings_menu, tearoff=0)
    settings_menu.add_cascade(label="Default Sorting", menu=sort_menu)
    
    # Sorting options
    sort_var = tk.StringVar(value="name_asc")
    sort_menu.add_radiobutton(label="Name (A-Z)", value="name_asc", variable=sort_var)
    sort_menu.add_radiobutton(label="Name (Z-A)", value="name_desc", variable=sort_var)
    sort_menu.add_separator()
    sort_menu.add_radiobutton(label="ID (Ascending)", value="id_asc", variable=sort_var)
    sort_menu.add_radiobutton(label="ID (Descending)", value="id_desc", variable=sort_var)
    sort_menu.add_separator()
    sort_menu.add_radiobutton(label="Date (Oldest First)", value="date_asc", variable=sort_var)
    sort_menu.add_radiobutton(label="Date (Newest First)", value="date_desc", variable=sort_var)
    
    return {
        'menubar': menubar,
        'file_menu': file_menu,
        'settings_menu': settings_menu,
        'sort_menu': sort_menu,
        'sort_var': sort_var
    }


def create_main_layout(root: tk.Tk, sash_positions=None) -> dict:
    """Create main GUI layout and return references to important widgets
    
    Args:
        root: The root Tk window
        sash_positions: Optional list of [sash0_pos, sash1_pos] for PanedWindow dividers.
                       If None, uses default positions from config.
    
    Returns:
        Dictionary of widget references including 'paned_window' reference
    """
    # Configure grid weights for responsive layout
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    
    # Main container
    main_frame = ttk.Frame(root, padding=str(config.MAIN_PADDING))
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(3, weight=1)  # Adjusted for server selector
    
    # Server selector at the very top
    server_frame = ttk.Frame(main_frame)
    server_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
    server_frame.columnconfigure(1, weight=1)
    
    ttk.Label(server_frame, text="Server:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
    server_var = tk.StringVar()
    server_combo = ttk.Combobox(server_frame, textvariable=server_var, state='readonly', font=("Segoe UI", 10), width=20)
    server_combo.grid(row=0, column=1, sticky=tk.W)
    
    # Status bar
    status_label = ttk.Label(main_frame, text="Loading EVE settings...", foreground="blue")
    status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
    
    # Path display field
    path_frame = ttk.Frame(main_frame)
    path_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
    path_frame.columnconfigure(1, weight=1)
    
    ttk.Label(path_frame, text="Profile Path:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
    path_var = tk.StringVar()
    path_entry = ttk.Entry(path_frame, textvariable=path_var, state='readonly', font=("Consolas", 10))
    path_entry.grid(row=0, column=1, sticky="ew")
    
    # Progress bar
    progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
    progress.grid(row=2, column=0, columnspan=3, pady=(0, 10), sticky="ew")
    progress.start(10)
    
    # Create PanedWindow for resizable panels
    paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned_window.grid(row=3, column=0, columnspan=3, sticky="nsew")
    
    # Create container frames for each panel
    profiles_container = ttk.Frame(paned_window)
    chars_container = ttk.Frame(paned_window)
    accounts_container = ttk.Frame(paned_window)
    
    # Add containers to paned window
    paned_window.add(profiles_container, weight=config.PROFILES_PANEL_WEIGHT)
    paned_window.add(chars_container, weight=config.CHARACTERS_PANEL_WEIGHT)
    paned_window.add(accounts_container, weight=config.ACCOUNTS_PANEL_WEIGHT)
    
    # Apply saved sash positions if provided
    if sash_positions:
        # Schedule sash position setting after window is fully rendered
        # This is necessary because sash positions can't be set until the widget is mapped
        # Using a longer delay (100ms) to ensure window is fully laid out
        root.after(100, lambda: _apply_sash_positions(paned_window, sash_positions))
    
    # Create panels inside their containers
    profiles_widgets = create_profiles_panel(profiles_container)
    chars_widgets = create_characters_panel(chars_container)
    accounts_widgets = create_accounts_panel(accounts_container)
    
    # Return all widget references including paned_window for saving positions later
    return {
        'server_var': server_var,
        'server_combo': server_combo,
        'status_label': status_label,
        'path_var': path_var,
        'path_entry': path_entry,
        'progress': progress,
        'paned_window': paned_window,
        **profiles_widgets,
        **chars_widgets,
        **accounts_widgets
    }


def _apply_sash_positions(paned_window, positions):
    """Apply sash positions to a PanedWindow.
    
    Args:
        paned_window: The ttk.PanedWindow widget
        positions: List of [sash0_pos, sash1_pos] positions in pixels
    """
    try:
        if len(positions) >= 2:
            paned_window.sashpos(0, positions[0])
            paned_window.sashpos(1, positions[1])
    except Exception:
        # Silently ignore errors (e.g., if window not yet mapped)
        pass


def create_profiles_panel(parent: ttk.Frame) -> dict:
    """Create profiles panel (left column)"""
    # Configure parent to expand
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    
    profiles_frame = ttk.LabelFrame(parent, text="Profiles", padding="5")
    profiles_frame.grid(row=0, column=0, sticky="nsew")
    profiles_frame.rowconfigure(0, weight=1)
    profiles_frame.columnconfigure(0, weight=1)
    
    # Profiles listbox
    profiles_listbox = tk.Listbox(profiles_frame, selectmode=tk.SINGLE)
    profiles_listbox.grid(row=0, column=0, sticky="nsew")
    
    profiles_scroll = ttk.Scrollbar(profiles_frame, orient=tk.VERTICAL, command=profiles_listbox.yview)
    profiles_scroll.grid(row=0, column=1, sticky="ns")
    profiles_listbox.configure(yscrollcommand=profiles_scroll.set)
    
    # Backup button
    backup_btn = ttk.Button(profiles_frame, text="Backup Profile")
    backup_btn.grid(row=1, column=0, columnspan=2, pady=(5, 2), sticky="ew")
    
    # Backup status label (fixed 2-line height, wraps text)
    backup_status_var = tk.StringVar()
    backup_status_var.set("Ready")
    backup_status_label = ttk.Label(profiles_frame, textvariable=backup_status_var, 
                                    font=("Segoe UI", 8), foreground="gray", anchor="center",
                                    wraplength=280, justify="center")
    backup_status_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 5), ipady=8)
    
    return {
        'profiles_listbox': profiles_listbox,
        'backup_btn': backup_btn,
        'backup_status_var': backup_status_var,
        'backup_status_label': backup_status_label
    }


def create_characters_panel(parent: ttk.Frame) -> dict:
    """Create characters panel (middle column)"""
    # Configure parent to expand
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    
    chars_frame = ttk.LabelFrame(parent, text="Characters", padding="5")
    chars_frame.grid(row=0, column=0, sticky="nsew")
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
    # Configure parent to expand
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    
    accounts_frame = ttk.LabelFrame(parent, text="Accounts", padding="5")
    accounts_frame.grid(row=0, column=0, sticky="nsew")
    accounts_frame.rowconfigure(0, weight=1)
    accounts_frame.columnconfigure(0, weight=1)
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
