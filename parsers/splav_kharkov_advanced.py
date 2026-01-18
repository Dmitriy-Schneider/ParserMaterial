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

    # Multiple User-Agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
    ]

    def __init__(self, db_path: str = 'steel_grades.db'):
        self.db_path = db_path
        self.session = requests.Session()
        self.user_agent_index = 0
        self.session.headers.update({
            'User-Agent': self.USER_AGENTS[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
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
                # Rotate User-Agent on each retry
                if attempt > 0:
                    self.user_agent_index = (self.user_agent_index + 1) % len(self.USER_AGENTS)
                    self.session.headers['User-Agent'] = self.USER_AGENTS[self.user_agent_index]

                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                time.sleep(3 * (attempt + 1))

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
        """Extract chemical composition from page (handles malformed HTML with orphaned tr elements)"""
        composition = {}

        # Priority 1: Find "Химический состав" heading and look for orphaned <tr> elements after it
        for element in soup.find_all(string=re.compile(r'Химический состав', re.IGNORECASE)):
            parent = element.find_parent()
            if parent:
                # Find all <tr> elements that come after this heading (may be orphaned outside table)
                all_trs = []

                # Look for next <tr> siblings (orphaned rows)
                next_el = parent.find_next('tr')
                while next_el and len(all_trs) < 5:  # Limit to 5 rows
                    all_trs.append(next_el)
                    next_el = next_el.find_next_sibling('tr')

                # If we found orphaned rows, parse them
                if len(all_trs) >= 2:  # Need at least header + values
                    # First tr should be headers
                    header_row = all_trs[0]
                    headers = []
                    for cell in header_row.find_all(['th', 'td', 'b']):
                        text = cell.get_text(strip=True).upper()
                        if text and len(text) <= 3 and text not in ['-', '–']:
                            headers.append(text)

                    # Second tr should be values
                    if len(all_trs) > 1 and headers:
                        value_row = all_trs[1]
                        cells = value_row.find_all(['td', 'th', 'b'])

                        element_map = {
                            'C': 'c', 'SI': 'si', 'MN': 'mn', 'NI': 'ni',
                            'S': 's', 'P': 'p', 'CR': 'cr', 'CU': 'cu',
                            'MO': 'mo', 'V': 'v', 'W': 'w', 'CO': 'co',
                            'NB': 'nb', 'N': 'n', 'TI': 'ti', 'AL': 'al'
                        }

                        for i, header in enumerate(headers):
                            if i < len(cells) and header in element_map:
                                value = cells[i].get_text(strip=True)
                                value = value.replace(',', '.')
                                value = re.sub(r'\s+', ' ', value)

                                if value and value not in ['-', '–', '—', 'не более']:
                                    composition[element_map[header]] = value

                    if composition:  # Found composition, return
                        return composition

        # Priority 2: Try finding table with chemistry data (old method)
        table = soup.find('table', class_='table_chemical')
        if not table:
            for t in soup.find_all('table'):
                if 'химический состав' in t.get_text().lower():
                    table = t
                    break

        if table:
            # Extract element headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    text = th.get_text(strip=True)
                    if text and len(text) <= 3:
                        headers.append(text.upper())

            # Extract values
            value_rows = table.find_all('tr')[1:]
            if value_rows and headers:
                for row in value_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= len(headers):
                        element_map = {
                            'C': 'c', 'SI': 'si', 'MN': 'mn', 'NI': 'ni',
                            'S': 's', 'P': 'p', 'CR': 'cr', 'CU': 'cu',
                            'MO': 'mo', 'V': 'v', 'W': 'w', 'CO': 'co',
                            'NB': 'nb', 'N': 'n'
                        }

                        for i, header in enumerate(headers):
                            if i < len(cells) and header in element_map:
                                value = cells[i].get_text(strip=True)
                                value = value.replace(',', '.')
                                value = re.sub(r'\s+', ' ', value)

                                if value and value not in ['-', '–', '—', 'не более']:
                                    composition[element_map[header]] = value

        return composition

    def parse_analogues(self, soup: BeautifulSoup) -> str:
        """Extract foreign analogues from page and validate against DB"""
        analogues = []

        # Find "Зарубежные аналоги" section specifically
        for element in soup.find_all(text=re.compile(r'Зарубежные аналоги', re.IGNORECASE)):
            # Find parent element and then find next table
            parent = element.find_parent()
            if parent:
                # Look for table after this header
                table = parent.find_next('table')
                if table:
                    # Extract all grade designations from table
                    for cell in table.find_all(['td', 'th']):
                        text = cell.get_text(strip=True)
                        # Skip headers, country names, and empty cells
                        if text and len(text) < 30:
                            # Skip common headers
                            skip_words = ['usa', 'germany', 'japan', 'france', 'uk', 'china',
                                        'гост', 'аналог', 'country', 'страна', 'марка', 'grade',
                                        'россия', 'germany', 'германия', 'япония']
                            if any(x in text.lower() for x in skip_words):
                                continue

                            # Check if looks like a grade (contains letters and/or numbers)
                            if re.search(r'[A-Za-zА-Я0-9]', text):
                                # Clean the text
                                grade = text.strip().replace('®', '').replace('™', '')
                                if grade and grade not in analogues:
                                    analogues.append(grade)

        # Validate analogues against database - only include grades that exist in DB
        if analogues:
            conn = get_connection()
            cursor = conn.cursor()

            validated_analogues = []
            for analogue in analogues:
                cursor.execute("SELECT 1 FROM steel_grades WHERE grade = ?", (analogue,))
                if cursor.fetchone():
                    validated_analogues.append(analogue)

            conn.close()

            return ' '.join(validated_analogues[:50])  # Limit to 50 analogues

        return ''

    def parse_standard(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract standard (GOST/DIN/etc) from chemistry section with country information"""

        # Priority 1: Look for specific GOST link pattern near "Химический состав"
        # Pattern: <a href="...gost_start.php?gost_number=5950">ГОСТ 5950</a>
        for element in soup.find_all(string=re.compile(r'Химический состав', re.IGNORECASE)):
            parent = element.find_parent()
            if parent:
                # Look for GOST link in next few elements
                for sibling in list(parent.find_all_next(limit=10)):
                    if sibling.name == 'a' and sibling.get('href'):
                        href = sibling.get('href')
                        if 'gost_start.php?gost_number=' in href:
                            # Extract GOST number from link
                            match = re.search(r'gost_number=(\d+)', href)
                            if match:
                                gost_number = match.group(1)
                                # Get the link text which should contain full GOST designation
                                link_text = sibling.get_text(strip=True)
                                if 'ГОСТ' in link_text:
                                    # Check next sibling for year (e.g., "-   2000")
                                    next_text = sibling.next_sibling
                                    if next_text and isinstance(next_text, str):
                                        year_match = re.search(r'[-–—]\s*(\d{4})', next_text)
                                        if year_match:
                                            return f"ГОСТ {gost_number}-{year_match.group(1)}, Россия"
                                    return f"ГОСТ {gost_number}, Россия"

                # Also check nearby text for GOST pattern
                for sibling in [parent] + list(parent.find_next_siblings(limit=5)):
                    text = sibling.get_text()
                    gost_matches = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                    if gost_matches:
                        return f"{gost_matches[0]}, Россия"

        # Priority 2: Look for GOST in chemistry table area
        chemistry_table = soup.find('table', class_='table_chemical')
        if not chemistry_table:
            for table in soup.find_all('table'):
                if 'химический состав' in table.get_text().lower():
                    chemistry_table = table
                    break

        if chemistry_table:
            # Look for GOST before the chemistry table
            prev_elements = []
            current = chemistry_table.find_previous_sibling()
            for _ in range(5):
                if current:
                    prev_elements.append(current)
                    current = current.find_previous_sibling()
                else:
                    break

            # Search in previous elements
            for element in prev_elements:
                # Check for GOST link
                gost_link = element.find('a', href=re.compile(r'gost_start\.php\?gost_number='))
                if gost_link:
                    href = gost_link.get('href')
                    match = re.search(r'gost_number=(\d+)', href)
                    if match:
                        gost_number = match.group(1)
                        next_text = gost_link.next_sibling
                        if next_text and isinstance(next_text, str):
                            year_match = re.search(r'[-–—]\s*(\d{4})', next_text)
                            if year_match:
                                return f"ГОСТ {gost_number}-{year_match.group(1)}, Россия"
                        return f"ГОСТ {gost_number}, Россия"

                # Check for GOST in text
                text = element.get_text()
                gost_matches = re.findall(r'ГОСТ\s+\d+[-–—]?\d*', text)
                if gost_matches:
                    return f"{gost_matches[0]}, Россия"

        # Priority 3: Check for other standards
        if chemistry_table:
            nearby_text = []
            current = chemistry_table.find_previous_sibling()
            for _ in range(3):
                if current:
                    nearby_text.append(current.get_text())
                    current = current.find_previous_sibling()

            full_text = ' '.join(nearby_text)

            if re.search(r'DIN\s+\d+', full_text):
                return "DIN, Германия"
            if re.search(r'EN\s+\d+', full_text):
                return "EN, Европа"
            if re.search(r'ASTM\s+[A-Z]\d+', full_text):
                return "ASTM, США"

        # Default: GOST without specific number
        return 'GOST, Россия'

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
                # Update chemistry and analogues for existing grade
                existing_analogues = existing[1] or ''
                new_analogues = grade_data['analogues']

                # Combine analogues
                if new_analogues and new_analogues not in existing_analogues:
                    combined_analogues = f"{existing_analogues} {new_analogues}".strip()
                else:
                    combined_analogues = existing_analogues

                # Update grade with chemistry and analogues
                comp = grade_data['composition']
                cursor.execute("""
                    UPDATE steel_grades
                    SET c = ?, cr = ?, ni = ?, mo = ?, v = ?, w = ?, co = ?,
                        mn = ?, si = ?, cu = ?, nb = ?, n = ?, s = ?, p = ?,
                        analogues = ?, standard = ?
                    WHERE grade = ?
                """, (
                    comp.get('c'), comp.get('cr'), comp.get('ni'), comp.get('mo'),
                    comp.get('v'), comp.get('w'), comp.get('co'), comp.get('mn'),
                    comp.get('si'), comp.get('cu'), comp.get('nb'), comp.get('n'),
                    comp.get('s'), comp.get('p'), combined_analogues,
                    grade_data['standard'], grade_data['grade']
                ))
                conn.commit()
                conn.close()

                self.stats['updated_analogues'] += 1
                logging.info(f"Updated chemistry for {grade_data['grade']}")
                return True

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
            logging.info(f"Added new grade: {grade_data['grade']}")
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
                    time.sleep(2)

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
