"""
Test analogue parsing for 4Х3ВМФ to verify H10 and T20810 are extracted
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
import requests
from bs4 import BeautifulSoup

print("="*100)
print("TESTING ANALOGUE PARSING FOR 4Х3ВМФ")
print("="*100)

# Create parser
parser = SplavKharkovParser()

# Search for 4Х3ВМФ on splav-kharkov
search_url = "https://www.splav-kharkov.com/choose_type_class.php?type_id=4"
print(f"\nSearching for 4Х3ВМФ on type_id=4 (Tool steel)...")

try:
    response = requests.get(search_url, timeout=10)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find link to 4Х3ВМФ
    import re
    found = False
    for link in soup.find_all('a', href=True):
        if '4Х3ВМФ' in link.get_text():
            href = link['href']
            print(f"Found 4Х3ВМФ: {href}")

            # Extract name_id
            match = re.search(r'name_id=(\d+)', href)
            if match:
                name_id = int(match.group(1))
                grade_url = f"https://www.splav-kharkov.com/mat_start.php?name_id={name_id}"
                print(f"Fetching: {grade_url}")

                # Parse grade page
                grade_data = parser.parse_grade_page(name_id, '4Х3ВМФ')

                if grade_data:
                    print("\n" + "="*100)
                    print("PARSED DATA:")
                    print("="*100)
                    print(f"Grade: {grade_data['grade']}")
                    print(f"Standard: {grade_data['standard']}")
                    print(f"Composition: {grade_data['composition']}")
                    print(f"Analogues: {grade_data['analogues']}")

                    # Check if H10 and T20810 are in analogues
                    analogues_list = grade_data['analogues'].split()
                    print("\n" + "="*100)
                    print("ANALOGUE VERIFICATION:")
                    print("="*100)

                    target_analogues = ['H10', 'T20810']
                    for target in target_analogues:
                        if target in analogues_list:
                            print(f"✓ {target} - FOUND in analogues")
                        else:
                            print(f"✗ {target} - NOT FOUND in analogues")

                    # Check if they exist in DB
                    print("\n" + "="*100)
                    print("DATABASE CHECK:")
                    print("="*100)

                    import sqlite3
                    conn = sqlite3.connect('database/steel_database.db')
                    cursor = conn.cursor()

                    for target in target_analogues:
                        cursor.execute("SELECT grade, standard FROM steel_grades WHERE grade = ?", (target,))
                        result = cursor.fetchone()
                        if result:
                            print(f"✓ {target} - EXISTS in DB (Standard: {result[1]})")
                        else:
                            print(f"✗ {target} - NOT FOUND in DB")

                    conn.close()

                else:
                    print("ERROR: Failed to parse grade page")

                found = True
                break

    if not found:
        print("ERROR: 4Х3ВМФ not found on the page")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*100)
print("TEST COMPLETE")
print("="*100)
