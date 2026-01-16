"""
Run full splav-kharkov parser with updated analogue extraction
- Updates chemistry for existing grades
- Extracts and validates analogues from "Зарубежные аналоги" section
- Only includes analogues that exist in database
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
import logging

# Setup logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('splav_full_update.log'),
        logging.StreamHandler()
    ]
)

print("="*100)
print("FULL SPLAV-KHARKOV PARSER - UPDATED VERSION")
print("="*100)
print("\nFeatures:")
print("  ✓ Updates chemistry for existing grades")
print("  ✓ Extracts analogues from 'Зарубежные аналоги' section")
print("  ✓ Validates analogues against database")
print("  ✓ Only includes existing grades as analogues")
print("\n" + "="*100)

# Create parser
parser = SplavKharkovParser()

# Parse all types
# You can limit to specific types for testing:
# type_ids = [4]  # Tool steel only
# Or parse all:
type_ids = None  # All types

print(f"\nStarting parser...")
print(f"Existing grades in DB: {len(parser.existing_grades)}")
print("\nThis will take several hours...")
print("Progress will be logged to: splav_full_update.log")
print("\n" + "="*100 + "\n")

# Run parser
parser.parse_all(type_ids=type_ids)

print("\n" + "="*100)
print("PARSER COMPLETE")
print("="*100)
