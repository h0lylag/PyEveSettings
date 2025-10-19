"""Background operations for backup manager.

Contains threaded operations for creating, restoring, and other
long-running backup operations.
"""

import threading
from pathlib import Path
from typing import Optional, Callable
from utils import BackupManager


class BackupOperations:
    """Handles background backup operations."""
    
    @staticmethod
    def create_backup(profile_path: Path, backup_dir: Path, 
                     on_success: Callable, on_error: Callable, on_complete: Callable):
        """Create backup in a background thread.
        
        Args:
            profile_path: Path to the profile folder to backup.
            backup_dir: Directory where backup will be stored.
            on_success: Callback(message) called on success.
            on_error: Callback(message) called on error.
            on_complete: Callback() called when operation finishes.
        """
        def backup_thread():
            try:
                # Create BackupManager with parent directory
                manager = BackupManager(backup_dir.parent)
                success, message, backup_path = manager.create_backup(profile_path)
                
                if success:
                    status_msg = f"✓ Backup created: {message}"
                    on_success(status_msg)
                else:
                    on_error(f"✗ Backup failed: {message}")
            except Exception as e:
                on_error(f"✗ Error creating backup: {e}")
            finally:
                on_complete()
        
        thread = threading.Thread(target=backup_thread, daemon=True)
        thread.start()
    
    @staticmethod
    def restore_backup(backup_path: Path, restore_to: Optional[Path],
                      on_success: Callable, on_error: Callable, on_complete: Callable):
        """Restore backup in a background thread.
        
        Args:
            backup_path: Path to the backup file.
            restore_to: Optional path to restore to. If None, creates new folder.
            on_success: Callback(message) called on success.
            on_error: Callback(message) called on error.
            on_complete: Callback() called when operation finishes.
        """
        def restore_thread():
            try:
                manager = BackupManager(backup_path.parent.parent)
                success, message = manager.restore_backup(backup_path, restore_to)
                
                if success:
                    on_success(f"✓ {message}")
                else:
                    on_error(f"✗ Restore failed: {message}")
            except Exception as e:
                on_error(f"✗ Error restoring backup: {e}")
            finally:
                on_complete()
        
        thread = threading.Thread(target=restore_thread, daemon=True)
        thread.start()
    
    @staticmethod
    def load_backups(search_paths: list, 
                    on_success: Callable, on_error: Callable, on_complete: Callable):
        """Load all backups from installations in a background thread.
        
        Args:
            search_paths: List of paths to search for backups.
            on_success: Callback(backup_directories, all_backups) called on success.
            on_error: Callback(error_message) called on error.
            on_complete: Callback() called when operation finishes.
        """
        def load_thread():
            try:
                # Discover backup directories
                backup_directories = BackupManager.discover_all_backup_directories(search_paths)
                
                # List all backups
                all_backups = BackupManager.list_all_backups_from_directories(backup_directories)
                
                on_success(backup_directories, all_backups)
            except Exception as e:
                on_error(f"Error loading backups: {e}")
            finally:
                on_complete()
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
