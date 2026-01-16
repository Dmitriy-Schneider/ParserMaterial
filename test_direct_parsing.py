"""
Test direct parsing of 4Х3ВМФ using known name_id=649
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser

print("="*100)
print("TESTING DIRECT PARSING OF 4Х3ВМФ (name_id=649)")
print("="*100)

# Create parser
parser = SplavKharkovParser()

# Parse grade page directly
name_id = 649
grade_name = '4Х3ВМФ'

print(f"\nParsing {grade_name} from name_id={name_id}...")
grade_data = parser.parse_grade_page(name_id, grade_name)

if grade_data:
    print("\n" + "="*100)
    print("PARSED DATA:")
    print("="*100)
    print(f"Grade: {grade_data['grade']}")
    print(f"Standard: {grade_data['standard']}")
    print(f"\nComposition:")
    for element, value in grade_data['composition'].items():
        print(f"  {element}: {value}")

    print(f"\nAnalogues: {grade_data['analogues']}")

    # Check if H10 and T20810 are in analogues
    analogues_list = grade_data['analogues'].split() if grade_data['analogues'] else []
    print("\n" + "="*100)
    print("ANALOGUE VERIFICATION:")
    print("="*100)

    target_analogues = ['H10', 'T20810']
    found_count = 0
    for target in target_analogues:
        if target in analogues_list:
            print(f"✓ {target} - FOUND in analogues")
            found_count += 1
        else:
            print(f"✗ {target} - NOT FOUND in analogues")

    print(f"\nResult: {found_count}/{len(target_analogues)} target analogues found")

    if found_count == len(target_analogues):
        print("✓ SUCCESS: All target analogues found and validated!")
    else:
        print("⚠ PARTIAL: Some target analogues missing")
        print("\nAll extracted analogues:")
        for ana in analogues_list:
            print(f"  - {ana}")

else:
    print("ERROR: Failed to parse grade page")

print("\n" + "="*100)
print("TEST COMPLETE")
print("="*100)
