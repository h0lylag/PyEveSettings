"""Backup manager for EVE settings profiles."""

import zipfile
from pathlib import Path
from typing import Optional
from datetime import datetime
from .exceptions import ValidationError


class BackupManager:
    """Manages backups of EVE settings profiles."""
    
    BACKUP_DIR_NAME = "backups"
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the backup manager.
        
        Args:
            base_path: Base EVE directory containing settings folders.
        """
        self.base_path = base_path
    
    def set_base_path(self, base_path: Path) -> None:
        """Set or update the base path.
        
        Args:
            base_path: Base EVE directory containing settings folders.
        """
        self.base_path = base_path
    
    def get_backup_directory(self) -> Optional[Path]:
        """Get the backup directory path, creating it if necessary.
        
        Returns:
            Path to backup directory, or None if base_path is not set.
        """
        if not self.base_path:
            return None
        
        backup_dir = self.base_path / self.BACKUP_DIR_NAME
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def create_backup(self, profile_folder: Path) -> tuple[bool, str, Optional[Path]]:
        """Create a backup of a settings profile folder.
        
        Args:
            profile_folder: Path to the settings folder to backup.
            
        Returns:
            Tuple of (success, message, backup_path):
                - success: True if backup was created successfully
                - message: Status message describing the result
                - backup_path: Path to the created backup file, or None if failed
        """
        print(f"[DEBUG] create_backup called with profile_folder: {profile_folder}")
        
        # Validate inputs
        if not self.base_path:
            print("[DEBUG] Base path not set")
            return False, "Base path not set", None
        
        print(f"[DEBUG] Base path: {self.base_path}")
        
        if not profile_folder.exists():
            print(f"[DEBUG] Profile folder does not exist: {profile_folder}")
            return False, f"Profile folder does not exist: {profile_folder.name}", None
        
        if not profile_folder.is_dir():
            print(f"[DEBUG] Not a directory: {profile_folder}")
            return False, f"Not a directory: {profile_folder.name}", None
        
        print("[DEBUG] Profile folder validation passed")
        
        # Get backup directory
        print("[DEBUG] Getting backup directory...")
        backup_dir = self.get_backup_directory()
        if not backup_dir:
            print("[DEBUG] Could not create backup directory")
            return False, "Could not create backup directory", None
        
        print(f"[DEBUG] Backup directory: {backup_dir}")
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_name = profile_folder.name
        backup_filename = f"{profile_name}_{timestamp}.zip"
        backup_path = backup_dir / backup_filename
        
        print(f"[DEBUG] Backup will be created at: {backup_path}")
        
        # Create the backup
        try:
            print("[DEBUG] Starting file collection...", flush=True)
            files_backed_up = 0
            
            print(f"[DEBUG] Opening zip file: {backup_path}", flush=True)
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup all files in the profile folder, including the folder itself
                print(f"[DEBUG] Searching for files in: {profile_folder}", flush=True)
                
                # Collect all files first (to avoid issues during iteration)
                files_to_backup = []
                for file_path in profile_folder.rglob('*'):
                    if file_path.is_file():
                        files_to_backup.append(file_path)
                
                print(f"[DEBUG] Found {len(files_to_backup)} files to backup", flush=True)
                
                # Now add them to the zip
                for file_path in files_to_backup:
                    # Store with profile folder name included in the path
                    arcname = Path(profile_name) / file_path.relative_to(profile_folder)
                    if files_backed_up < 5 or files_backed_up % 20 == 0:
                        print(f"[DEBUG] Adding file {files_backed_up + 1}: {arcname}", flush=True)
                    zipf.write(file_path, arcname)
                    files_backed_up += 1
            
            print(f"[DEBUG] Zip file closed. Total files backed up: {files_backed_up}", flush=True)
            
            if files_backed_up == 0:
                print("[DEBUG] No files found to backup, removing empty zip")
                backup_path.unlink()  # Remove empty backup
                return False, "No files found to backup", None
            
            # Get backup size for status message
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"[DEBUG] Backup complete. Size: {size_mb:.1f} MB")
            
            return True, f"{files_backed_up} files ({size_mb:.1f} MB)", backup_path
            
        except PermissionError as e:
            print(f"[DEBUG] PermissionError: {e}")
            return False, f"Permission denied: {e}", None
        except OSError as e:
            print(f"[DEBUG] OSError: {e}")
            return False, f"Error creating backup: {e}", None
        except Exception as e:
            print(f"[DEBUG] Unexpected exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Unexpected error: {e}", None
    
    def list_backups(self) -> list[tuple[Path, datetime, int]]:
        """List all available backups.
        
        Returns:
            List of tuples (backup_path, creation_time, size_bytes) sorted by creation time (newest first).
        """
        backup_dir = self.get_backup_directory()
        if not backup_dir or not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in backup_dir.glob("*.zip"):
            if backup_file.is_file():
                stat = backup_file.stat()
                creation_time = datetime.fromtimestamp(stat.st_mtime)
                size = stat.st_size
                backups.append((backup_file, creation_time, size))
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x[1], reverse=True)
        return backups
    
    def restore_backup(self, backup_path: Path, restore_to: Optional[Path] = None) -> tuple[bool, str]:
        """Restore a backup to a profile folder.
        
        Args:
            backup_path: Path to the backup zip file.
            restore_to: Optional path to restore to. If None, creates a new folder.
            
        Returns:
            Tuple of (success, message) describing the result.
        """
        if not backup_path.exists() or not backup_path.is_file():
            return False, "Backup file not found"
        
        if not self.base_path:
            return False, "Base path not set"
        
        try:
            # Determine restore location
            if restore_to is None:
                # Create new folder with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"settings_restored_{timestamp}"
                restore_to = self.base_path / folder_name
            
            # Create restore directory
            restore_to.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            files_restored = 0
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(restore_to)
                files_restored = len(zipf.namelist())
            
            return True, f"Restored {files_restored} files to {restore_to.name}"
            
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted backup file"
        except PermissionError as e:
            return False, f"Permission denied: {e}"
        except Exception as e:
            return False, f"Error restoring backup: {e}"
    
    def delete_backup(self, backup_path: Path) -> tuple[bool, str]:
        """Delete a backup file.
        
        Args:
            backup_path: Path to the backup file to delete.
            
        Returns:
            Tuple of (success, message) describing the result.
        """
        if not backup_path.exists():
            return False, "Backup file not found"
        
        try:
            backup_path.unlink()
            return True, f"Deleted backup: {backup_path.name}"
        except PermissionError as e:
            return False, f"Permission denied: {e}"
        except Exception as e:
            return False, f"Error deleting backup: {e}"
    
    def get_backup_stats(self) -> dict:
        """Get statistics about backups.
        
        Returns:
            Dictionary with backup statistics (count, total_size_mb, oldest, newest).
        """
        backups = self.list_backups()
        
        if not backups:
            return {
                'count': 0,
                'total_size_mb': 0.0,
                'oldest': None,
                'newest': None
            }
        
        total_size = sum(size for _, _, size in backups)
        oldest = backups[-1][1] if backups else None
        newest = backups[0][1] if backups else None
        
        return {
            'count': len(backups),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest': oldest,
            'newest': newest
        }
    
    def parse_backup_filename(self, backup_path: Path) -> Optional[dict]:
        """Parse backup filename to extract metadata.
        
        Expected format: {profile_name}_{timestamp}.zip
        Example: settings_Default_20231019_141036.zip
        
        Args:
            backup_path: Path to the backup file.
            
        Returns:
            Dictionary with metadata (profile_name, timestamp, datetime_obj) or None if invalid.
        """
        try:
            filename = backup_path.stem  # Remove .zip extension
            parts = filename.rsplit('_', 2)  # Split from right: name, date, time
            
            if len(parts) >= 3:
                profile_name = '_'.join(parts[:-2])  # Everything before last 2 parts
                date_str = parts[-2]  # YYYYMMDD
                time_str = parts[-1]  # HHMMSS
                timestamp_str = f"{date_str}_{time_str}"
                
                # Parse datetime
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                return {
                    'profile_name': profile_name,
                    'timestamp': timestamp_str,
                    'datetime': dt,
                    'filename': backup_path.name
                }
            return None
        except (ValueError, IndexError):
            return None
    
    def get_backup_metadata(self, backup_path: Path) -> dict:
        """Get comprehensive metadata for a backup file.
        
        Args:
            backup_path: Path to the backup file.
            
        Returns:
            Dictionary with metadata: profile, datetime, size, file_count, is_valid.
        """
        metadata = {
            'path': backup_path,
            'profile_name': 'Unknown',
            'datetime': None,
            'timestamp': None,
            'size_bytes': 0,
            'size_mb': 0.0,
            'file_count': 0,
            'is_valid': False,
            'server': 'Unknown'
        }
        
        # Parse filename
        parsed = self.parse_backup_filename(backup_path)
        if parsed:
            metadata['profile_name'] = parsed['profile_name']
            metadata['datetime'] = parsed['datetime']
            metadata['timestamp'] = parsed['timestamp']
        
        # Get file stats
        if backup_path.exists():
            try:
                stat = backup_path.stat()
                metadata['size_bytes'] = stat.st_size
                metadata['size_mb'] = stat.st_size / (1024 * 1024)
                
                # Try to get file count from zip
                try:
                    with zipfile.ZipFile(backup_path, 'r') as zipf:
                        metadata['file_count'] = len(zipf.namelist())
                        metadata['is_valid'] = True
                except zipfile.BadZipFile:
                    metadata['is_valid'] = False
            except Exception:
                pass
        
        # Try to extract server from parent path
        try:
            # Look for server pattern in path (e.g., c_ccp_eve_tq_tranquility)
            path_parts = backup_path.parts
            for part in path_parts:
                if 'tranquility' in part.lower():
                    metadata['server'] = 'Tranquility'
                    break
                elif 'singularity' in part.lower() or 'sisi' in part.lower():
                    metadata['server'] = 'Singularity'
                    break
                elif 'thunderdome' in part.lower():
                    metadata['server'] = 'Thunderdome'
                    break
        except Exception:
            pass
        
        return metadata
    
    def group_backups_by_profile(self, backups: list) -> dict:
        """Group backups by profile name.
        
        Args:
            backups: List of backup paths.
            
        Returns:
            Dictionary mapping profile names to lists of backup metadata.
        """
        grouped = {}
        
        for backup_path in backups:
            if isinstance(backup_path, tuple):
                backup_path = backup_path[0]  # Extract path from tuple
            
            metadata = self.get_backup_metadata(backup_path)
            profile_name = metadata['profile_name']
            
            if profile_name not in grouped:
                grouped[profile_name] = []
            grouped[profile_name].append(metadata)
        
        # Sort each group by datetime (newest first)
        for profile_name in grouped:
            grouped[profile_name].sort(
                key=lambda x: x['datetime'] if x['datetime'] else datetime.min,
                reverse=True
            )
        
        return grouped
    
    def filter_backups(self, backups: list, profile: Optional[str] = None, server: Optional[str] = None) -> list:
        """Filter backups by profile name and/or server.
        
        Args:
            backups: List of backup paths or tuples.
            profile: Optional profile name to filter by.
            server: Optional server name to filter by.
            
        Returns:
            Filtered list of backups.
        """
        filtered = []
        
        for backup in backups:
            backup_path = backup[0] if isinstance(backup, tuple) else backup
            metadata = self.get_backup_metadata(backup_path)
            
            # Apply filters
            if profile and metadata['profile_name'] != profile:
                continue
            if server and metadata['server'] != server:
                continue
            
            filtered.append(backup)
        
        return filtered
    
    def validate_backup_integrity(self, backup_path: Path) -> tuple[bool, str]:
        """Validate that a backup file is a valid, non-corrupted zip.
        
        Args:
            backup_path: Path to the backup file.
            
        Returns:
            Tuple of (is_valid, message).
        """
        if not backup_path.exists():
            return False, "Backup file does not exist"
        
        if not backup_path.is_file():
            return False, "Path is not a file"
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Test the zip file
                result = zipf.testzip()
                if result is not None:
                    return False, f"Corrupted file in archive: {result}"
                
                # Check if there are any files
                if len(zipf.namelist()) == 0:
                    return False, "Backup is empty"
                
                return True, "Backup is valid"
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted zip file"
        except Exception as e:
            return False, f"Error validating backup: {e}"
    
    def get_profile_name_from_backup(self, backup_path: Path) -> Optional[str]:
        """Extract profile name from backup without extracting the archive.
        
        Args:
            backup_path: Path to the backup file.
            
        Returns:
            Profile name or None if cannot be determined.
        """
        parsed = self.parse_backup_filename(backup_path)
        if parsed:
            return parsed['profile_name']
        return None
    
    @staticmethod
    def discover_all_backup_directories(search_paths: list[Path]) -> list[dict]:
        """Discover all backup directories across multiple EVE installations.
        
        Args:
            search_paths: List of base EVE installation paths to search.
            
        Returns:
            List of dictionaries with keys: backup_dir, installation_path, server_name.
        """
        backup_dirs = []
        
        for base_path in search_paths:
            if not base_path.exists():
                continue
            
            try:
                # Look for backup directories
                for item in base_path.rglob(BackupManager.BACKUP_DIR_NAME):
                    if item.is_dir():
                        # Extract server info from path
                        server_name = 'Unknown'
                        installation_path = base_path
                        
                        # Try to find server folder in path
                        for part in item.parts:
                            if 'tranquility' in part.lower():
                                server_name = 'Tranquility'
                                break
                            elif 'singularity' in part.lower() or 'sisi' in part.lower():
                                server_name = 'Singularity'
                                break
                            elif 'thunderdome' in part.lower():
                                server_name = 'Thunderdome'
                                break
                        
                        backup_dirs.append({
                            'backup_dir': item,
                            'installation_path': installation_path,
                            'server_name': server_name,
                            'parent_dir': item.parent  # The server/installation directory
                        })
            except PermissionError:
                continue
        
        return backup_dirs
    
    @staticmethod
    def list_all_backups_from_directories(backup_directories: list[dict]) -> list[dict]:
        """List all backups from multiple backup directories.
        
        Args:
            backup_directories: List of backup directory info dicts from discover_all_backup_directories.
            
        Returns:
            List of dictionaries with backup metadata including installation and server info.
        """
        all_backups = []
        
        for dir_info in backup_directories:
            backup_dir = dir_info['backup_dir']
            
            if not backup_dir.exists():
                continue
            
            try:
                for backup_file in backup_dir.glob("*.zip"):
                    if backup_file.is_file():
                        # Create temporary BackupManager to use metadata methods
                        temp_manager = BackupManager(dir_info['parent_dir'])
                        metadata = temp_manager.get_backup_metadata(backup_file)
                        
                        # Add installation and server info
                        metadata['installation_path'] = dir_info['installation_path']
                        metadata['server'] = dir_info['server_name']
                        metadata['backup_dir'] = backup_dir
                        
                        all_backups.append(metadata)
            except PermissionError:
                continue
        
        # Sort by datetime (newest first)
        all_backups.sort(
            key=lambda x: x['datetime'] if x['datetime'] else datetime.min,
            reverse=True
        )
        
        return all_backups
