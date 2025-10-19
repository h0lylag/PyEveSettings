"""
Test/Example script for EANM
Creates dummy EVE settings files for testing purposes
"""

from pathlib import Path
import time


def create_test_files(count=3):
    """
    Create dummy EVE settings files for testing
    
    Args:
        count: Number of character and account files to create
    """
    test_dir = Path("test_settings")
    test_dir.mkdir(exist_ok=True)
    
    print(f"Creating {count} test character and account files in {test_dir}/")
    
    # Character IDs (fictional EVE character IDs)
    char_ids = [90000001, 90000002, 90000003, 90000004, 90000005]
    user_ids = [80000001, 80000002, 80000003, 80000004, 80000005]
    
    # Create character files
    for i in range(count):
        char_file = test_dir / f"core_char_{char_ids[i]}.dat"
        with open(char_file, 'wb') as f:
            # Write some dummy binary data
            f.write(b'\x00' * 1024)
            f.write(f"Character {i+1} settings data".encode())
        
        # Set different modification times
        timestamp = time.time() - (i * 3600)  # Each file is 1 hour older
        Path(char_file).touch()
        import os
        os.utime(char_file, (timestamp, timestamp))
        
        print(f"  Created: {char_file.name}")
    
    # Create user/account files
    for i in range(count):
        user_file = test_dir / f"core_user_{user_ids[i]}.dat"
        with open(user_file, 'wb') as f:
            # Write some dummy binary data
            f.write(b'\x00' * 512)
            f.write(f"Account {i+1} settings data".encode())
        
        # Set different modification times
        timestamp = time.time() - (i * 3600)  # Each file is 1 hour older
        Path(user_file).touch()
        import os
        os.utime(user_file, (timestamp, timestamp))
        
        print(f"  Created: {user_file.name}")
    
    print(f"\nTest files created! Navigate to {test_dir.absolute()} and run:")
    print(f"  cd {test_dir.absolute()}")
    print(f"  python ../main.py")
    print("\nNote: Character names will show as 'unknown' since these are test IDs")


if __name__ == "__main__":
    create_test_files(3)
