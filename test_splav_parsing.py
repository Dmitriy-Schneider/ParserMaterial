"""Test splav-kharkov parser to see why chemistry is not being parsed"""
import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from parsers.splav_kharkov_advanced import SplavKharkovParser

# Test parsing a known grade
parser = SplavKharkovParser()

# Test Х12МФ (name_id needs to be found)
# Let's test with a direct URL test

print("="*100)
print("TESTING SPLAV-KHARKOV PARSER")
print("="*100)

# Let's check the parse_chemical_composition method directly
test_html = """
<table class="table_chemical">
    <tr>
        <th>C</th>
        <th>Cr</th>
        <th>Mo</th>
        <th>V</th>
    </tr>
    <tr>
        <td>1.45-1.65</td>
        <td>11.0-13.0</td>
        <td>0.40-0.70</td>
        <td>0.15-0.30</td>
    </tr>
</table>
"""

soup = BeautifulSoup(test_html, 'html.parser')
composition = parser.parse_chemical_composition(soup)

print("\nTest 1: Parse test HTML with chemistry:")
print(f"Result: {composition}")

# Now let's fetch a real page
print("\n" + "="*100)
print("TEST 2: Fetch real page for Х12МФ")
print("="*100)

# Try to find Х12МФ
url = "https://www.splav-kharkov.com/choose_type_class.php?type_id=4"
try:
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find link to Х12МФ
    for link in soup.find_all('a', href=True):
        if 'Х12МФ' in link.get_text():
            href = link['href']
            print(f"Found Х12МФ: {href}")

            # Fetch the grade page
            if 'name_id=' in href:
                import re
                match = re.search(r'name_id=(\d+)', href)
                if match:
                    name_id = match.group(1)
                    grade_url = f"https://www.splav-kharkov.com/mat_start.php?name_id={name_id}"
                    print(f"Fetching: {grade_url}")

                    response2 = requests.get(grade_url, timeout=10)
                    response2.encoding = 'utf-8'
                    soup2 = BeautifulSoup(response2.text, 'html.parser')

                    # Parse chemistry
                    composition = parser.parse_chemical_composition(soup2)
                    print(f"\nParsed composition: {composition}")

                    # Check if there's a chemistry table
                    print("\nSearching for chemistry tables...")
                    tables = soup2.find_all('table')
                    print(f"Found {len(tables)} tables")

                    for i, table in enumerate(tables):
                        text = table.get_text()[:100]
                        if 'C' in text or 'Cr' in text or 'хим' in text.lower():
                            print(f"\nTable {i}: {text}")

                    break

except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*100)
print("CONCLUSION:")
print("="*100)
print("If composition is empty, the parser is not finding the chemistry table correctly.")
