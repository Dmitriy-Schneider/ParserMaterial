import requests
from bs4 import BeautifulSoup
import time
import re
from database_schema import get_connection, create_database
import config


class SteelParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        create_database()
    
    def fetch_page(self, url):
        """Fetch a page with retry logic"""
        for attempt in range(config.RETRY_COUNT):
            try:
                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < config.RETRY_COUNT - 1:
                    time.sleep(config.DELAY_BETWEEN_REQUESTS)
        return None
    
    def parse_value(self, value):
        """Parse value handling intervals, question marks, and ranges"""
        if not value or value == '?' or value == '' or value == '0.00':
            return None
        
        value = value.replace('&nbsp;', ' ').strip()
        
        if '?' in value:
            return None
        
        # Если значение равно 0.00, это обычно означает отсутствие данных
        if value == '0.00':
            return None
        
        return value
    
    def parse_main_table(self):
        """Parse the main steel chart table - extract ALL grades from ALL links"""
        print("Fetching main page...")
        html = self.fetch_page(config.STEEL_CHART_URL)
        if not html:
            print("Failed to fetch main page")
            return
        
        soup = BeautifulSoup(html, 'lxml')
        
        tables = soup.find_all('table')
        table = None
        
        for t in tables:
            rows = t.find_all('tr')
            if len(rows) > 1000:
                table = t
                break
        
        if not table:
            print("Table not found")
            return
        
        print(f"Found table with {len(table.find_all('tr'))} rows")
        rows = table.find_all('tr')[1:]  # Skip header row
        
        conn = get_connection()
        cursor = conn.cursor()
        
        parsed_count = 0
        seen_grades = set()  # Track unique grades
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 20:
                continue
            
            try:
                cell1 = cells[1]
                
                # Extract ALL grades from ALL links in this cell
                all_links = cell1.find_all('a')
                
                for link in all_links:
                    grade = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not grade or grade in seen_grades:
                        continue
                    
                    seen_grades.add(grade)
                    
                    # Build full URL
                    if href and not href.startswith('http'):
                        href = f"https://zknives.com/knives/steels/{href}"
                    elif not href:
                        href = None
                    
                    # Find analogues (all other links in the same cell)
                    analogues = []
                    for other_link in all_links:
                        other_grade = other_link.get_text(strip=True)
                        if other_grade and other_grade != grade:
                            analogues.append(other_grade)
                    
                    analogues_text = ' '.join(analogues) if analogues else None
                    
                    # Extract other data
                    def get_cell_text(i):
                        if i < len(cells):
                            return self.parse_value(cells[i].get_text(strip=True))
                        return None
                    
                    data = {
                        'grade': grade,
                        'analogues': analogues_text,
                        'base': get_cell_text(2),
                        'c': get_cell_text(3),
                        'cr': get_cell_text(4),
                        'mo': get_cell_text(5),
                        'v': get_cell_text(6),
                        'w': get_cell_text(7),
                        'co': get_cell_text(8),
                        'ni': get_cell_text(9),
                        'mn': get_cell_text(10),
                        'si': get_cell_text(11),
                        's': get_cell_text(12),
                        'p': get_cell_text(13),
                        'cu': get_cell_text(14),
                        'nb': get_cell_text(15),
                        'n': get_cell_text(16),
                        'other_elements': None,  # No other elements in main table
                        'link': href
                    }
                    
                    # Insert into database - use INSERT OR IGNORE to avoid duplicates
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO steel_grades 
                            (grade, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, other_elements, link)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            data['grade'], data['analogues'], data['base'], data['c'], data['cr'],
                            data['mo'], data['v'], data['w'], data['co'], data['ni'], data['mn'],
                            data['si'], data['s'], data['p'], data['cu'], data['nb'], data['n'],
                            data.get('other_elements'), data['link']
                        ))
                        parsed_count += 1
                        if parsed_count % 500 == 0:
                            print(f"Parsed {parsed_count} grades...")
                    except Exception as e:
                        print(f"Error inserting {grade}: {e}")
                        
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        conn.commit()
        conn.close()
        print(f"\nParsed {parsed_count} unique steel grades")
        print(f"Expected: ~6127 grades")
    
    def run(self):
        """Run the parser"""
        print("Starting parser...")
        try:
            self.parse_main_table()
            print("Parsing complete!")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    parser = SteelParser()
    parser.run()