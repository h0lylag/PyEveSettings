"""Event handlers for py-eve-settings GUI."""

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from typing import Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime
from utils import ValidationError, DataFileError
from .dialogs import show_character_selection_dialog, show_account_selection_dialog
from .helpers import sort_tree

if TYPE_CHECKING:
    from .main_window import PyEveSettingsGUI


class EventHandlers:
    """Handles all GUI events and actions."""
    
    def __init__(self, app: 'PyEveSettingsGUI'):
        """Initialize with reference to main app.
        
        Args:
            app: The main PyEveSettingsGUI application instance.
        """
        self.app = app
    
    def on_profile_selected(self, event: Optional[tk.Event] = None) -> None:
        """Handle profile selection change.
        
        Args:
            event: The selection event (unused, but required by tkinter).
        """
        selection = self.app.profiles_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        profile_name = self.app.profiles_listbox.get(idx)
        
        if profile_name == "Custom...":
            self.select_custom_folder()
        else:
            # Find folder by name
            for folder in self.app.settings_folders:
                if folder.name == profile_name:
                    self.app.selected_folder = folder
                    break
            self.update_character_lists()
            # Apply default sorting after updating lists
            self.app._apply_default_sorting()
    
    def select_custom_folder(self) -> None:
        """Browse for a custom settings folder."""
        folder_path = filedialog.askdirectory(
            title="Select EVE Settings Folder",
            mustexist=True
        )
        
        if not folder_path:
            # Cancelled - revert selection to first profile
            self.app.profiles_listbox.selection_clear(0, tk.END)
            self.app.profiles_listbox.selection_set(0)
            return
        
        custom_folder = Path(folder_path)
        
        # Verify it has settings files
        if not self.app.manager.path_resolver.validate_settings_folder(custom_folder):
            messagebox.showerror(
                "Invalid Folder",
                "The selected folder does not contain EVE settings files!"
            )
            self.app.profiles_listbox.selection_clear(0, tk.END)
            self.app.profiles_listbox.selection_set(0)
            return
        
        # Add to folders list if not already there
        if custom_folder not in self.app.settings_folders:
            self.app.settings_folders.append(custom_folder)
            # Reload files to include new folder
            character_ids = self.app.manager.load_files(self.app.settings_folders)
            
            # Fetch any new character names
            if character_ids:
                self.app.api_cache.fetch_names_bulk(character_ids)
                for char_id, name in self.app.api_cache.get_all_cached().items():
                    self.app.data_file.save_character_name(str(char_id), name)
                self.app.data_file.save()
            
            self.app.all_char_list = self.app.manager.char_list.copy()
            self.app.all_user_list = self.app.manager.user_list.copy()
            
            # Add to profiles listbox before "Custom..."
            size = self.app.profiles_listbox.size()
            self.app.profiles_listbox.insert(size - 1, custom_folder.name)
        
        # Set the selected folder and update view
        self.app.selected_folder = custom_folder
        self.update_character_lists()
        # Apply default sorting after updating lists
        self.app._apply_default_sorting()
    
    def update_character_lists(self) -> None:
        """Update character and account lists based on selected profile."""
        # Update path display
        if self.app.selected_folder:
            self.app.path_var.set(str(self.app.selected_folder))
        
        # Filter by selected folder
        filtered_chars = [
            sf for sf in self.app.all_char_list 
            if self.app.manager.file_to_folder.get(sf.path) == self.app.selected_folder
        ]
        filtered_users = [
            sf for sf in self.app.all_user_list 
            if self.app.manager.file_to_folder.get(sf.path) == self.app.selected_folder
        ]
        
        # Update characters treeview
        self.app.chars_tree.delete(*self.app.chars_tree.get_children())
        for char in filtered_chars:
            # Skip invalid characters
            if self.app.api_cache.is_invalid(char.id):
                continue
            
            mtime = char.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = self.app.notes_manager.get_character_note(str(char.id))
            
            self.app.chars_tree.insert('', 'end', 
                                      values=(char.id, char.get_char_name(), date_str, note),
                                      tags=(str(char.id),))
        
        # Update accounts treeview
        self.app.accounts_tree.delete(*self.app.accounts_tree.get_children())
        for user in filtered_users:
            mtime = user.path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            note = self.app.notes_manager.get_account_note(str(user.id))
            
            self.app.accounts_tree.insert('', 'end',
                                         values=(user.id, date_str, note),
                                         tags=(str(user.id),))
        
        # Store filtered lists for copy operation
        self.app.manager.char_list = filtered_chars
        self.app.manager.user_list = filtered_users
    
    def edit_char_note(self) -> None:
        """Edit note for selected character."""
        selection = self.app.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a character first.")
            return
        
        item = selection[0]
        values = self.app.chars_tree.item(item, 'values')
        char_id = int(values[0])
        char_name = values[1]
        
        char = next((c for c in self.app.manager.char_list if c.id == char_id), None)
        if not char:
            return
        
        current_note = self.app.notes_manager.get_character_note(str(char.id))
        new_note = simpledialog.askstring(
            "Edit Character Note",
            f"Enter note for {char_name} (max 20 characters):",
            initialvalue=current_note,
            parent=self.app.root
        )
        
        if new_note is not None:
            new_note = new_note[:20]
            try:
                self.app.notes_manager.set_character_note(str(char.id), new_note)
                self.app.data_file.set_character_note(str(char.id), new_note)
                self.app.data_file.save()
                self.update_character_lists()
            except (ValidationError, DataFileError) as e:
                messagebox.showerror("Error Saving Note", str(e))
    
    def edit_account_note(self) -> None:
        """Edit note for selected account."""
        selection = self.app.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an account first.")
            return
        
        item = selection[0]
        values = self.app.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        user = next((u for u in self.app.manager.user_list if u.id == user_id), None)
        if not user:
            return
        
        current_note = self.app.notes_manager.get_account_note(str(user.id))
        new_note = simpledialog.askstring(
            "Edit Account Note",
            f"Enter note for account {user_id} (max 20 characters):",
            initialvalue=current_note,
            parent=self.app.root
        )
        
        if new_note is not None:
            new_note = new_note[:20]
            try:
                self.app.notes_manager.set_account_note(str(user.id), new_note)
                self.app.data_file.set_account_note(str(user.id), new_note)
                self.app.data_file.save()
                self.update_character_lists()
            except (ValidationError, DataFileError) as e:
                messagebox.showerror("Error Saving Note", str(e))
    
    def char_overwrite_all(self) -> None:
        """Overwrite settings to all characters in current profile."""
        selection = self.app.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source character first.")
            return
        
        item = selection[0]
        values = self.app.chars_tree.item(item, 'values')
        char_id = int(values[0])
        char_name = values[1]
        
        source_char = next((c for c in self.app.manager.char_list if c.id == char_id), None)
        if not source_char:
            return
        
        result = messagebox.askyesno(
            "Confirm Overwrite All",
            f"Copy settings from {char_name} to ALL characters in this profile?\n\n"
            f"This will affect {len(self.app.manager.char_list)} character(s)."
        )
        
        if result:
            total_copied = self.app.manager.copy_settings(source_char)
            messagebox.showinfo("Success", f"Settings copied to {total_copied} file(s)!")
    
    def account_overwrite_all(self) -> None:
        """Overwrite settings to all accounts in current profile."""
        selection = self.app.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source account first.")
            return
        
        item = selection[0]
        values = self.app.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        source_user = next((u for u in self.app.manager.user_list if u.id == user_id), None)
        if not source_user:
            return
        
        result = messagebox.askyesno(
            "Confirm Overwrite All",
            f"Copy settings from account {user_id} to ALL accounts in this profile?\n\n"
            f"This will affect {len(self.app.manager.user_list)} account(s)."
        )
        
        if result:
            total_copied = self.app.manager.copy_settings(source_user)
            messagebox.showinfo("Success", f"Settings copied to {total_copied} file(s)!")
    
    def char_overwrite_select(self) -> None:
        """Select specific characters to overwrite."""
        selection = self.app.chars_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source character first.")
            return
        
        item = selection[0]
        values = self.app.chars_tree.item(item, 'values')
        char_id = int(values[0])
        
        source_char = next((c for c in self.app.manager.char_list if c.id == char_id), None)
        if not source_char:
            return
        
        show_character_selection_dialog(
            self.app.root, 
            source_char, 
            self.app.manager.char_list,
            self.app.manager,
            sort_tree,
            self.app.notes_manager
        )
    
    def account_overwrite_select(self) -> None:
        """Select specific accounts to overwrite."""
        selection = self.app.accounts_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source account first.")
            return
        
        item = selection[0]
        values = self.app.accounts_tree.item(item, 'values')
        user_id = int(values[0])
        
        source_user = next((u for u in self.app.manager.user_list if u.id == user_id), None)
        if not source_user:
            return
        
        show_account_selection_dialog(
            self.app.root,
            source_user,
            self.app.manager.user_list,
            self.app.manager,
            sort_tree,
            self.app.notes_manager
        )
