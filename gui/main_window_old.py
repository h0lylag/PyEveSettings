"""
Main GUI window for py-eve-settings
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
from typing import Optional, List, Dict
from pathlib import Path
from utils.core import SettingsManager
from utils.models import (SettingFile, get_character_note, set_character_note, 
                          get_account_note, set_account_note,
                          get_all_character_notes, get_all_account_notes)


class PyEveSettingsGUI:
    """Main GUI application for py-eve-settings"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PyEveSettings")
        self.root.geometry("1200x700")
        
        # Initialize settings manager
        self.manager = SettingsManager()
        self.settings_folders: List[Path] = []
        self.all_char_list: List[SettingFile] = []
        self.all_user_list: List[SettingFile] = []
        self.loading = True
        self.selected_folder: Optional[Path] = None
        
        # Create GUI first (before loading data)
        self.create_widgets()
        
        # Center window
        self.center_window()
        
        # Start loading data in background
        self.root.after(100, self.start_loading_data)
    
    def create_widgets(self):
        """Create GUI widgets with 3-column layout"""
        # Configure grid weights for responsive layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1, minsize=200)  # Profiles
        main_frame.columnconfigure(1, weight=2, minsize=400)  # Characters
        main_frame.columnconfigure(2, weight=2, minsize=400)  # Accounts
        main_frame.rowconfigure(2, weight=1)
        
        # Status bar at top
        self.status_label = ttk.Label(main_frame, text="Loading EVE settings...", foreground="blue")
        self.status_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Path display field
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="Profile Path:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, state='readonly', font=("Consolas", 9))
        self.path_entry.grid(row=0, column=1, sticky="ew")
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky="ew")
        self.progress.start(10)
        
        # LEFT COLUMN - Profiles
        profiles_frame = ttk.LabelFrame(main_frame, text="Profiles", padding="5")
        profiles_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 5))
        profiles_frame.rowconfigure(0, weight=1)
        profiles_frame.columnconfigure(0, weight=1)
        
        # Profiles listbox
        self.profiles_listbox = tk.Listbox(profiles_frame, selectmode=tk.SINGLE)
        self.profiles_listbox.grid(row=0, column=0, sticky="nsew")
        self.profiles_listbox.bind('<<ListboxSelect>>', self.on_profile_selected)
        
        profiles_scroll = ttk.Scrollbar(profiles_frame, orient=tk.VERTICAL, command=self.profiles_listbox.yview)
        profiles_scroll.grid(row=0, column=1, sticky="ns")
        self.profiles_listbox.configure(yscrollcommand=profiles_scroll.set)
        
        # MIDDLE COLUMN - Characters
        chars_frame = ttk.LabelFrame(main_frame, text="Characters", padding="5")
        chars_frame.grid(row=2, column=1, sticky="nsew", padx=5)
        chars_frame.rowconfigure(0, weight=1)
        chars_frame.columnconfigure(0, weight=1)
        
        # Characters treeview with sortable columns
        self.chars_tree = ttk.Treeview(chars_frame, columns=('id', 'name', 'date', 'note'), 
                                       show='headings', selectmode='browse')
        self.chars_tree.heading('id', text='ID', command=lambda: self.sort_tree(self.chars_tree, 'id', False))
        self.chars_tree.heading('name', text='Name', command=lambda: self.sort_tree(self.chars_tree, 'name', False))
        self.chars_tree.heading('date', text='Last Modified', command=lambda: self.sort_tree(self.chars_tree, 'date', False))
        self.chars_tree.heading('note', text='Note', command=lambda: self.sort_tree(self.chars_tree, 'note', False))
        
        self.chars_tree.column('id', width=100, anchor='e')
        self.chars_tree.column('name', width=150, anchor='w')
        self.chars_tree.column('date', width=140, anchor='w')
        self.chars_tree.column('note', width=120, anchor='w')
        
        self.chars_tree.grid(row=0, column=0, sticky="nsew")
        
        chars_scroll = ttk.Scrollbar(chars_frame, orient=tk.VERTICAL, command=self.chars_tree.yview)
        chars_scroll.grid(row=0, column=1, sticky="ns")
        self.chars_tree.configure(yscrollcommand=chars_scroll.set)
        
        # Character buttons
        char_btn_frame = ttk.Frame(chars_frame)
        char_btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        ttk.Button(char_btn_frame, text="Edit Note", command=self.edit_char_note).pack(side=tk.LEFT, padx=2)
        ttk.Button(char_btn_frame, text="Overwrite All", command=self.char_overwrite_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(char_btn_frame, text="Overwrite...", command=self.char_overwrite_select).pack(side=tk.LEFT, padx=2)
        
        # RIGHT COLUMN - Accounts
        accounts_frame = ttk.LabelFrame(main_frame, text="Accounts", padding="5")
        accounts_frame.grid(row=2, column=2, sticky="nsew", padx=(5, 0))
        accounts_frame.rowconfigure(0, weight=1)
        accounts_frame.columnconfigure(0, weight=1)
        
        # Accounts treeview with sortable columns
        self.accounts_tree = ttk.Treeview(accounts_frame, columns=('id', 'date', 'note'), 
                                         show='headings', selectmode='browse')
        self.accounts_tree.heading('id', text='ID', command=lambda: self.sort_tree(self.accounts_tree, 'id', False))
        self.accounts_tree.heading('date', text='Last Modified', command=lambda: self.sort_tree(self.accounts_tree, 'date', False))
        self.accounts_tree.heading('note', text='Note', command=lambda: self.sort_tree(self.accounts_tree, 'note', False))
        
        self.accounts_tree.column('id', width=100, anchor='e')
        self.accounts_tree.column('date', width=140, anchor='w')
        self.accounts_tree.column('note', width=120, anchor='w')
        
        self.accounts_tree.grid(row=0, column=0, sticky="nsew")
        
        accounts_scroll = ttk.Scrollbar(accounts_frame, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        accounts_scroll.grid(row=0, column=1, sticky="ns")
        self.accounts_tree.configure(yscrollcommand=accounts_scroll.set)
        
        # Account buttons
        account_btn_frame = ttk.Frame(accounts_frame)
        account_btn_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        ttk.Button(account_btn_frame, text="Edit Note", command=self.edit_account_note).pack(side=tk.LEFT, padx=2)
        ttk.Button(account_btn_frame, text="Overwrite All", command=self.account_overwrite_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(account_btn_frame, text="Overwrite...", command=self.account_overwrite_select).pack(side=tk.LEFT, padx=2)
    
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
        self.update_character_lists()
    
    def on_profile_selected(self, event=None):
        """Handle profile selection change"""
        selection = self.profiles_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        profile_name = self.profiles_listbox.get(idx)
        
        if profile_name == "Custom...":
            self.select_custom_folder()
        else:
            # Find folder by name
            for folder in self.settings_folders:
                if folder.name == profile_name:
                    self.selected_folder = folder
                    break
            self.update_character_lists()
    
    def select_custom_folder(self):
        """Browse for a custom settings folder"""
        folder_path = filedialog.askdirectory(
            title="Select EVE Settings Folder",
            mustexist=True
        )
        
        if not folder_path:
            # Cancelled - revert selection to first profile
            self.profiles_listbox.selection_clear(0, tk.END)
            self.profiles_listbox.selection_set(0)
            return
        
        custom_folder = Path(folder_path)
        
        # Verify it has settings files
        if not self.manager.has_settings_files(custom_folder):
            messagebox.showerror(
                "Invalid Folder",
                "The selected folder does not contain EVE settings files!"
            )
            self.profiles_listbox.selection_clear(0, tk.END)
            self.profiles_listbox.selection_set(0)
            return
        
        # Add to folders list if not already there
        if custom_folder not in self.settings_folders:
            self.settings_folders.append(custom_folder)
            # Reload files to include new folder
            self.manager.load_files(self.settings_folders)
            self.all_char_list = self.manager.char_list.copy()
            self.all_user_list = self.manager.user_list.copy()
            
            # Add to profiles listbox before "Custom..."
            size = self.profiles_listbox.size()
            self.profiles_listbox.insert(size - 1, custom_folder.name)
        
        # Set the selected folder and update view
        self.selected_folder = custom_folder
        self.update_character_lists()
    
    def update_character_lists(self):
        """Update character and account lists based on selected profile"""
        # Update path display
        if self.selected_folder:
            self.path_var.set(str(self.selected_folder))
        
        # Filter by selected folder
        filtered_chars = [
            sf for sf in self.all_char_list 
            if self.manager.file_to_folder.get(sf.path) == self.selected_folder
        ]
        filtered_users = [
            sf for sf in self.all_user_list 
            if self.manager.file_to_folder.get(sf.path) == self.selected_folder
        ]
        
        # Update characters treeview
        self.chars_tree.delete(*self.chars_tree.get_children())
        for char in filtered_chars:
            # Get formatted date
            from datetime import datetime
            mtime = char.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            
            # Get note
            note = get_character_note(char.id)
            
            # Insert with char object as tag for reference
            self.chars_tree.insert('', 'end', 
                                  values=(char.id, char.get_char_name(), date_str, note),
                                  tags=(str(char.id),))
        
        # Update accounts treeview
        self.accounts_tree.delete(*self.accounts_tree.get_children())
        for user in filtered_users:
            # Get formatted date
            from datetime import datetime
            mtime = user.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            
            # Get note
            note = get_account_note(user.id)
            
            # Insert with user object as tag for reference
            self.accounts_tree.insert('', 'end',
                                     values=(user.id, date_str, note),
                                     tags=(str(user.id),))
        
        # Store filtered lists for copy operation
        self.manager.char_list = filtered_chars
        self.manager.user_list = filtered_users
        
        # Sort by date (default)
        self.sort_tree(self.chars_tree, 'date', False)
        self.sort_tree(self.accounts_tree, 'date', False)
    
    def edit_char_note(self):
        """Edit note for selected character"""
        selection = self.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a character first.")
            return
        
        # Get the item and extract char ID from values
        item = selection[0]
        values = self.chars_tree.item(item, 'values')
        char_id = int(values[0])
        char_name = values[1]
        
        # Find the character object
        char = next((c for c in self.manager.char_list if c.id == char_id), None)
        if not char:
            return
        
        current_note = get_character_note(char.id)
        new_note = simpledialog.askstring(
            "Edit Character Note",
            f"Enter note for {char_name} (max 20 characters):",
            initialvalue=current_note,
            parent=self.root
        )
        
        if new_note is not None:  # Not cancelled
            new_note = new_note[:20]  # Limit to 20 chars
            set_character_note(char.id, new_note)
            self.update_character_lists()
    
    def edit_account_note(self):
        """Edit note for selected account"""
        selection = self.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an account first.")
            return
        
        # Get the item and extract user ID from values
        item = selection[0]
        values = self.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        # Find the user object
        user = next((u for u in self.manager.user_list if u.id == user_id), None)
        if not user:
            return
        
        current_note = get_account_note(user.id)
        new_note = simpledialog.askstring(
            "Edit Account Note",
            f"Enter note for account {user_id} (max 20 characters):",
            initialvalue=current_note,
            parent=self.root
        )
        
        if new_note is not None:  # Not cancelled
            new_note = new_note[:20]  # Limit to 20 chars
            set_account_note(user.id, new_note)
            self.update_character_lists()
    
    def char_overwrite_all(self):
        """Overwrite settings to all characters in current profile"""
        selection = self.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source character first.")
            return
        
        # Get the item and extract char ID
        item = selection[0]
        values = self.chars_tree.item(item, 'values')
        char_id = int(values[0])
        char_name = values[1]
        
        # Find the character object
        source_char = next((c for c in self.manager.char_list if c.id == char_id), None)
        if not source_char:
            return
        
        # Confirm action
        result = messagebox.askyesno(
            "Confirm Overwrite All",
            f"Copy settings from {char_name} to ALL characters in this profile?\n\n"
            f"This will affect {len(self.manager.char_list)} character(s)."
        )
        
        if result:
            total_copied = self.manager.copy_settings(source_char)
            messagebox.showinfo("Success", 
                              f"Settings copied to {total_copied} file(s)!")
    
    def account_overwrite_all(self):
        """Overwrite settings to all accounts in current profile"""
        selection = self.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source account first.")
            return
        
        # Get the item and extract user ID
        item = selection[0]
        values = self.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        # Find the user object
        source_user = next((u for u in self.manager.user_list if u.id == user_id), None)
        if not source_user:
            return
        
        # Confirm action
        result = messagebox.askyesno(
            "Confirm Overwrite All",
            f"Copy settings from account {user_id} to ALL accounts in this profile?\n\n"
            f"This will affect {len(self.manager.user_list)} account(s)."
        )
        
        if result:
            total_copied = self.manager.copy_settings(source_user)
            messagebox.showinfo("Success", 
                              f"Settings copied to {total_copied} file(s)!")
    
    def char_overwrite_select(self):
        """Select specific characters to overwrite"""
        selection = self.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source character first.")
            return
        
        # Get the item and extract char ID
        item = selection[0]
        values = self.chars_tree.item(item, 'values')
        char_id = int(values[0])
        char_name = values[1]
        
        # Find the character object
        source_char = next((c for c in self.manager.char_list if c.id == char_id), None)
        if not source_char:
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Characters to Overwrite")
        dialog.transient(self.root)
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
        tree.heading('id', text='ID', command=lambda: self.sort_tree(tree, 'id', False))
        tree.heading('name', text='Name', command=lambda: self.sort_tree(tree, 'name', False))
        tree.heading('date', text='Last Modified', command=lambda: self.sort_tree(tree, 'date', False))
        tree.heading('note', text='Note', command=lambda: self.sort_tree(tree, 'note', False))
        
        tree.column('#0', width=30, stretch=False)
        tree.column('id', width=100, anchor='e')
        tree.column('name', width=150, anchor='w')
        tree.column('date', width=140, anchor='w')
        tree.column('note', width=120, anchor='w')
        
        tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Populate with other characters
        from datetime import datetime
        target_chars = []
        for char in self.manager.char_list:
            if char.id != char_id:  # Skip source
                mtime = char.path.stat().st_mtime
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                note = get_character_note(char.id)
                
                tree.insert('', 'end', text='☐',
                           values=(char.id, char.get_char_name(), date_str, note),
                           tags=(str(char.id),))
                target_chars.append(char)
        
        # Sort by date initially
        self.sort_tree(tree, 'date', False)
        
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
            original_list = self.manager.char_list
            self.manager.char_list = targets
            total_copied = self.manager.copy_settings(source_char)
            self.manager.char_list = original_list
            
            dialog.destroy()
            messagebox.showinfo("Success", f"Settings copied to {len(targets)} character(s)!")
        
        ttk.Button(btn_frame, text="Copy to Selected", command=do_copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Set dialog size and center it above main window
        dialog.update_idletasks()
        dialog.geometry("650x450")
        
        # Center dialog above main window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        dialog_width = 650
        dialog_height = 450
        
        x = main_x + (main_width - dialog_width) // 2
        y = main_y + (main_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def account_overwrite_select(self):
        """Select specific accounts to overwrite"""
        selection = self.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source account first.")
            return
        
        # Get the item and extract user ID
        item = selection[0]
        values = self.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        # Find the user object
        source_user = next((u for u in self.manager.user_list if u.id == user_id), None)
        if not source_user:
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Accounts to Overwrite")
        dialog.transient(self.root)
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
        tree.heading('id', text='ID', command=lambda: self.sort_tree(tree, 'id', False))
        tree.heading('date', text='Last Modified', command=lambda: self.sort_tree(tree, 'date', False))
        tree.heading('note', text='Note', command=lambda: self.sort_tree(tree, 'note', False))
        
        tree.column('#0', width=30, stretch=False)
        tree.column('id', width=100, anchor='e')
        tree.column('date', width=140, anchor='w')
        tree.column('note', width=120, anchor='w')
        
        tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Populate with other accounts
        from datetime import datetime
        target_users = []
        for user in self.manager.user_list:
            if user.id != user_id:  # Skip source
                mtime = user.path.stat().st_mtime
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                note = get_account_note(user.id)
                
                tree.insert('', 'end', text='☐',
                           values=(user.id, date_str, note),
                           tags=(str(user.id),))
                target_users.append(user)
        
        # Sort by date initially
        self.sort_tree(tree, 'date', False)
        
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
            original_list = self.manager.user_list
            self.manager.user_list = targets
            total_copied = self.manager.copy_settings(source_user)
            self.manager.user_list = original_list
            
            dialog.destroy()
            messagebox.showinfo("Success", f"Settings copied to {len(targets)} account(s)!")
        
        ttk.Button(btn_frame, text="Copy to Selected", command=do_copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Set dialog size and center it above main window
        dialog.update_idletasks()
        dialog.geometry("500x450")
        
        # Center dialog above main window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        dialog_width = 500
        dialog_height = 450
        
        x = main_x + (main_width - dialog_width) // 2
        y = main_y + (main_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def sort_tree(self, tree, col, reverse):
        """Sort treeview by column"""
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
        
        # Update heading to reverse sort next time
        tree.heading(col, command=lambda: self.sort_tree(tree, col, not reverse))
    
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()
