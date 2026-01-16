"""
Advanced parser for splav-kharkov.com - Complete grade database scraper
Finds ALL grades including cast iron (чугун) and checks against existing DB
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
from typing import Dict, List, Optional, Set
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('splav_kharkov_advanced.log'),
        logging.StreamHandler()
    ]
)

BASE_URL = 'https://www.splav-kharkov.com'

# All material types from the site
MATERIAL_TYPES = {
    1: 'Heat-resistant steel and alloys',
    2: 'Precision alloys',
    3: 'Structural steel',
    4: 'Tool steel',
    5: 'Steel for castings',
    6: 'Corrosion-resistant steel and alloys',
    7: 'Cast iron',  # ЧУГУН - includes ЧНХМДШ
    8: 'Special-purpose steel',
    9: 'Bronze',
    10: 'Brass',
    11: 'Aluminum and aluminum alloys',
    12: 'Copper and copper alloys',
    13: 'Electrical steel',
    14: 'Nickel and nickel alloys',
    15: 'Zinc and zinc alloys',
    16: 'Magnesium and magnesium alloys',
    17: 'Titanium and titanium alloys',
    18: 'Tin and tin alloys',
    19: 'Lead and lead alloys',
    20: 'Ferroalloys',
    21: 'Silver and silver alloys',
    22: 'Gold and gold alloys',
    23: 'Platinum and platinum alloys',
    24: 'Palladium and palladium alloys',
    25: 'Other metals and alloys',
    26: 'Powder metallurgy',
    27: 'Welding and brazing materials'
}


class SplavKharkovParser:
    """Advanced parser for splav-kharkov.com"""

    def __init__(self, db_path: str = 'steel_grades.db'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Track existing grades to avoid duplicates
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()

        # Statistics
        self.stats = {
            'total_found': 0,
            'new_grades': 0,
            'updated_analogues': 0,
            'skipped_existing': 0,
            'errors': 0
        }

    def load_existing_grades(self):
        """Load all existing grade names from database"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = {row[0] for row in cursor.fetchall()}
        conn.close()
        logging.info(f"Loaded {len(self.existing_grades)} existing grades from database")

    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse page with retries"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                time.sleep(2 * (attempt + 1))

        logging.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def get_all_class_ids(self, type_id: int) -> List[Dict[str, any]]:
        """Get all class IDs for a material type"""
        url = f"{BASE_URL}/choose_type_class.php?type_id={type_id}"
        soup = self.get_page(url)

        if not soup:
            return []

        classes = []

        # Find all links to choose_mat.php
        for link in soup.find_all('a', href=re.compile(r'choose_mat\.php\?class_id=\d+')):
            match = re.search(r'class_id=(\d+)', link['href'])
            if match:
                class_id = int(match.group(1))
                class_name = link.get_text(strip=True)
                classes.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'type_id': type_id
                })

        # If no class links found, check if grades are listed directly
        if not classes:
            direct_grades = soup.find_all('a', href=re.compile(r'mat_start\.php\?name_id=\d+'))
            if direct_grades:
                # Create a virtual class for direct grades
                classes.append({
                    'class_id': -1,  # Special marker for direct grades
                    'class_name': f'{MATERIAL_TYPES.get(type_id)} (direct)',
                    'type_id': type_id,
                    'direct_grades': True
                })

        logging.info(f"Found {len(classes)} classes for type_id={type_id} ({MATERIAL_TYPES.get(type_id)})")
        return classes

    def get_all_grades_in_class(self, class_id: int, type_id: Optional[int] = None) -> List[Dict[str, any]]:
        """Get all grade IDs in a class"""
        # Handle direct grades (no intermediate class page)
        if class_id == -1 and type_id is not None:
            url = f"{BASE_URL}/choose_type_class.php?type_id={type_id}"
        else:
            url = f"{BASE_URL}/choose_mat.php?class_id={class_id}"

        soup = self.get_page(url)

        if not soup:
            return []

        grades = []

        # Find all links to mat_start.php
        for link in soup.find_all('a', href=re.compile(r'mat_start\.php\?name_id=\d+')):
            match = re.search(r'name_id=(\d+)', link['href'])
            if match:
                name_id = int(match.group(1))
                grade_name = link.get_text(strip=True)

                # Skip if already exists in DB
                if grade_name in self.existing_grades:
                    self.stats['skipped_existing'] += 1
                    continue

                # Skip if already processed in this session (avoid duplicates from same page)
                if grade_name in [g['grade'] for g in grades]:
                    continue

                grades.append({
                    'name_id': name_id,
                    'grade': grade_name,
                    'class_id': class_id
                })

        return grades

    def parse_chemical_composition(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract chemical composition from page"""
        composition = {}

        # Find composition table
        table = soup.find('table', class_='table_chemical')
        if not table:
            # Try alternative table structure
            for table in soup.find_all('table'):
                if 'химический состав' in table.get_text().lower():
                    break

        if table:
            # Extract element headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    text = th.get_text(strip=True)
                    if text and len(text) <= 3:  # Element symbols are short
                        headers.append(text.upper())

            # Extract values
            value_rows = table.find_all('tr')[1:]  # Skip header
            if value_rows and headers:
                for row in value_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= len(headers):
                        for i, header in enumerate(headers):
                            if i < len(cells):
                                value = cells[i].get_text(strip=True)
                                # Clean value
                                value = value.replace(',', '.')
                                value = re.sub(r'\s+', ' ', value)

                                if value and value not in ['-', '–', '—', 'не более']:
                                    # Map common element names
                                    element = header.lower()
                                    element_map = {
                                        'c': 'c', 'si': 'si', 'mn': 'mn', 'ni': 'ni',
                                        's': 's', 'p': 'p', 'cr': 'cr', 'cu': 'cu',
                                        'mo': 'mo', 'v': 'v', 'w': 'w', 'co': 'co',
                                        'nb': 'nb', 'n': 'n'
                                    }

                                    if element in element_map:
                                        composition[element_map[element]] = value

        return composition

    def parse_analogues(self, soup: BeautifulSoup) -> str:
        """Extract foreign analogues from page"""
        analogues = []

        # Find analogues section
        # Common patterns: "Зарубежные аналоги", "Foreign analogues", table with country codes

        for table in soup.find_all('table'):
            table_text = table.get_text().lower()
            if 'аналог' in table_text or 'analogue' in table_text or 'usa' in table_text:
                # Extract all grade designations from table
                for cell in table.find_all(['td', 'th']):
                    text = cell.get_text(strip=True)
                    # Skip headers and country names
                    if text and len(text) < 30 and not any(x in text.lower() for x in ['usa', 'germany', 'japan', 'france', 'uk', 'гост', 'аналог']):
                        # Check if looks like a grade (contains numbers and letters)
                        if re.search(r'[A-Za-z]', text) and re.search(r'\d', text):
                            if text not in analogues:
                                analogues.append(text)

        return ' '.join(analogues[:50])  # Limit to 50 analogues

    def parse_standard(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract standard (GOST/DIN/etc) from page with country information"""
        # Look for GOST mentions
        text = soup.get_text()

        # Find ГОСТ references
        gost_matches = re.findall(r'ГОСТ\s+\d+[-–—]\d+', text)
        if gost_matches:
            return f"{gost_matches[0]}, Россия"

        # Look for other standards with countries
        if re.search(r'DIN\s+\d+', text):
            return "DIN, Германия"
        if re.search(r'EN\s+\d+', text):
            return "EN, Европа"
        if re.search(r'ASTM\s+[A-Z]\d+', text):
            return "ASTM, США"

        return 'GOST, Россия'  # Default for splav-kharkov.com (Russian site)

    def parse_grade_page(self, name_id: int, grade_name: str) -> Optional[Dict]:
        """Parse individual grade page"""
        url = f"{BASE_URL}/mat_start.php?name_id={name_id}"
        soup = self.get_page(url)

        if not soup:
            return None

        # Extract data
        composition = self.parse_chemical_composition(soup)
        analogues = self.parse_analogues(soup)
        standard = self.parse_standard(soup)

        return {
            'grade': grade_name,
            'composition': composition,
            'analogues': analogues,
            'standard': standard,
            'source': f'splav-kharkov.com (name_id={name_id})'
        }

    def insert_grade(self, grade_data: Dict) -> bool:
        """Insert or update grade in database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Check if grade exists
            cursor.execute("SELECT grade, analogues FROM steel_grades WHERE grade = ?", (grade_data['grade'],))
            existing = cursor.fetchone()

            if existing:
                # Update analogues if new ones found
                existing_analogues = existing[1] or ''
                new_analogues = grade_data['analogues']

                if new_analogues and new_analogues not in existing_analogues:
                    combined_analogues = f"{existing_analogues} {new_analogues}".strip()
                    cursor.execute("""
                        UPDATE steel_grades
                        SET analogues = ?
                        WHERE grade = ?
                    """, (combined_analogues, grade_data['grade']))
                    conn.commit()
                    conn.close()

                    self.stats['updated_analogues'] += 1
                    logging.info(f"Updated analogues for {grade_data['grade']}")
                    return True
                else:
                    conn.close()
                    return False

            # Insert new grade
            comp = grade_data['composition']

            cursor.execute("""
                INSERT INTO steel_grades
                (grade, standard, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p, analogues, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grade_data['grade'],
                grade_data['standard'],
                comp.get('c'),
                comp.get('cr'),
                comp.get('ni'),
                comp.get('mo'),
                comp.get('v'),
                comp.get('w'),
                comp.get('co'),
                comp.get('mn'),
                comp.get('si'),
                comp.get('cu'),
                comp.get('nb'),
                comp.get('n'),
                comp.get('s'),
                comp.get('p'),
                grade_data['analogues'],
                f"{BASE_URL}/mat_start.php?name_id={grade_data.get('name_id', '')}"
            ))

            conn.commit()
            conn.close()

            self.stats['new_grades'] += 1
            self.existing_grades.add(grade_data['grade'])
            logging.info(f"✓ Added new grade: {grade_data['grade']}")
            return True

        except Exception as e:
            logging.error(f"Error inserting {grade_data['grade']}: {e}")
            self.stats['errors'] += 1
            return False

    def parse_all(self, type_ids: Optional[List[int]] = None, max_grades_per_class: Optional[int] = None):
        """
        Parse all material types

        Args:
            type_ids: List of specific type IDs to parse (default: all)
            max_grades_per_class: Limit grades per class for testing (default: no limit)
        """
        if type_ids is None:
            type_ids = list(MATERIAL_TYPES.keys())

        logging.info(f"Starting advanced parser for {len(type_ids)} material types")
        logging.info(f"Existing grades in DB: {len(self.existing_grades)}")

        for type_id in type_ids:
            material_name = MATERIAL_TYPES.get(type_id, f'Unknown-{type_id}')
            logging.info(f"\n{'='*80}")
            logging.info(f"Processing type_id={type_id}: {material_name}")
            logging.info(f"{'='*80}")

            # Get all classes for this type
            classes = self.get_all_class_ids(type_id)

            for class_info in classes:
                class_id = class_info['class_id']
                class_name = class_info['class_name']

                logging.info(f"\nProcessing class_id={class_id}: {class_name}")

                # Get all grades in this class
                grades = self.get_all_grades_in_class(class_id, type_id=type_id)

                if max_grades_per_class:
                    grades = grades[:max_grades_per_class]

                logging.info(f"Found {len(grades)} new grades to process")

                for i, grade_info in enumerate(grades, 1):
                    self.stats['total_found'] += 1

                    logging.info(f"[{i}/{len(grades)}] Parsing {grade_info['grade']}...")

                    # Parse grade page
                    grade_data = self.parse_grade_page(grade_info['name_id'], grade_info['grade'])

                    if grade_data:
                        grade_data['name_id'] = grade_info['name_id']
                        self.insert_grade(grade_data)
                    else:
                        self.stats['errors'] += 1

                    # Rate limiting
                    time.sleep(1)

                # Pause between classes
                time.sleep(2)

        # Print final statistics
        self.print_statistics()

    def print_statistics(self):
        """Print parsing statistics"""
        logging.info(f"\n{'='*80}")
        logging.info("PARSING STATISTICS")
        logging.info(f"{'='*80}")
        logging.info(f"Total grades found:     {self.stats['total_found']}")
        logging.info(f"New grades added:       {self.stats['new_grades']}")
        logging.info(f"Analogues updated:      {self.stats['updated_analogues']}")
        logging.info(f"Skipped (existing):     {self.stats['skipped_existing']}")
        logging.info(f"Errors:                 {self.stats['errors']}")
        logging.info(f"{'='*80}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Advanced parser for splav-kharkov.com')
    parser.add_argument('--type-ids', type=int, nargs='+', help='Specific type IDs to parse (default: all)')
    parser.add_argument('--test', action='store_true', help='Test mode: parse only 5 grades per class')
    parser.add_argument('--cast-iron-only', action='store_true', help='Parse only cast iron (type_id=7)')

    args = parser.parse_args()

    # Determine type IDs to parse
    if args.cast_iron_only:
        type_ids = [7]  # Cast iron only
    elif args.type_ids:
        type_ids = args.type_ids
    else:
        type_ids = None  # All types

    max_grades = 5 if args.test else None

    # Create parser and run
    scraper = SplavKharkovParser()
    scraper.parse_all(type_ids=type_ids, max_grades_per_class=max_grades)


if __name__ == '__main__':
    main()
