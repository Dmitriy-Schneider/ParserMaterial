"""
Test standard extraction for 4Х5МФС
Should get ГОСТ 5950 from chemical composition section
"""
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re

sys.path.append(str(Path(__file__).parent))

print("="*100)
print("TESTING STANDARD EXTRACTION FOR 4Х5МФС")
print("="*100)

# Find 4Х5МФС in database
import sqlite3
conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

cursor.execute("SELECT grade, link, standard FROM steel_grades WHERE grade = ?", ('4Х5МФС',))
result = cursor.fetchone()

if result:
    grade, link, current_standard = result
    print(f"\nCurrent in DB:")
    print(f"  Grade: {grade}")
    print(f"  Link: {link}")
    print(f"  Standard: {current_standard}")

    # Extract name_id
    match = re.search(r'name_id=(\d+)', link)
    if match:
        name_id = match.group(1)
        url = f"https://www.splav-kharkov.com/mat_start.php?name_id={name_id}"

        print(f"\nFetching page: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            # Save HTML to file for analysis
            with open('4х5мфс_page.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print("Page saved to: 4х5мфс_page.html")

            # Find all ГОСТ mentions
            text = soup.get_text()
            gost_matches = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
            print(f"\nAll ГОСТ mentions on page:")
            for i, gost in enumerate(gost_matches, 1):
                print(f"  {i}. {gost}")

            # Find "Химический состав" section
            print("\n" + "="*100)
            print("SEARCHING FOR ГОСТ IN 'Химический состав' SECTION:")
            print("="*100)

            # Method 1: Find text "Химический состав" and look nearby
            for element in soup.find_all(text=re.compile(r'Химический состав', re.IGNORECASE)):
                print(f"\nFound 'Химический состав' in: {element.parent.name}")

                # Get parent and siblings
                parent = element.find_parent()
                if parent:
                    # Look in the same block
                    text = parent.get_text()
                    gost_in_section = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                    if gost_in_section:
                        print(f"  ГОСТ in this section: {gost_in_section}")

                    # Look in next siblings
                    for sibling in parent.find_next_siblings(limit=5):
                        text = sibling.get_text()
                        gost_in_sibling = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                        if gost_in_sibling:
                            print(f"  ГОСТ in next sibling ({sibling.name}): {gost_in_sibling}")

            # Method 2: Find chemistry table and look for GOST nearby
            print("\n" + "="*100)
            print("SEARCHING IN CHEMISTRY TABLE:")
            print("="*100)

            for table in soup.find_all('table'):
                table_text = table.get_text().lower()
                # Check if this is chemistry table
                if any(elem in table_text for elem in ['si', 'mn', 'cr', 'c,', 'углерод']):
                    print(f"\nFound chemistry table")

                    # Look before table
                    prev_sibling = table.find_previous_sibling()
                    if prev_sibling:
                        text = prev_sibling.get_text()
                        gost = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                        if gost:
                            print(f"  ГОСТ before table: {gost}")

                    # Look in table caption or headers
                    caption = table.find('caption')
                    if caption:
                        text = caption.get_text()
                        gost = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                        if gost:
                            print(f"  ГОСТ in caption: {gost}")

                    # Look after table
                    next_sibling = table.find_next_sibling()
                    if next_sibling:
                        text = next_sibling.get_text()
                        gost = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                        if gost:
                            print(f"  ГОСТ after table: {gost}")

                    break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
else:
    print("4Х5МФС not found in database")

conn.close()

print("\n" + "="*100)
print("EXPECTED: ГОСТ 5950")
print("="*100)
