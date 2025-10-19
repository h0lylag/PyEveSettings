"""
Test bulk character name fetching from ESI API
"""

from eanm.models import SettingFile

# Test with a few known character IDs
test_ids = [
    2114794365,  # CCP Falcon (known EVE dev)
    2112000002,  # CCP Guard
    2112625428,  # Another CCP dev
]

print("Testing bulk character name fetch...")
print(f"Fetching names for {len(test_ids)} character IDs")
print(f"IDs: {test_ids}")
print()

names = SettingFile.fetch_character_names_bulk(test_ids)

print("Results:")
for char_id, char_name in names.items():
    print(f"  {char_id}: {char_name}")

print()
print(f"Successfully fetched {len(names)} names out of {len(test_ids)} IDs")

if len(names) == len(test_ids):
    print("✓ All character names fetched successfully!")
else:
    print("⚠ Some character names could not be fetched")
