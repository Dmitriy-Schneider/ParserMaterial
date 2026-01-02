"""
Steel Tables Importer
Импорт марок стали из табличных CSV файлов (Аустенитные, Дуплексные и т.д.)
"""

import csv
import sqlite3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database_schema import get_connection
import config


class SteelTablesImporter:
    """Импортер марок стали из табличных CSV"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_FILE
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def import_csv(self, csv_path: str, standard: str = None) -> Dict[str, int]:
        """
        Import steel grades from CSV file

        Args:
            csv_path: Path to CSV file
            standard: Source/standard name (auto-detect from filename if None)

        Returns:
            Dictionary with import statistics
        """
        # Auto-detect standard from filename
        if not standard:
            filename = Path(csv_path).stem
            if "Аустенит" in filename:
                standard = "AISI (Austenitic)"
            elif "Дуплекс" in filename:
                standard = "AISI (Duplex)"
            elif "Ферритн" in filename:
                standard = "AISI (Ferritic)"
            elif "Мартенсит" in filename:
                standard = "AISI (Martensitic)"
            elif "ВЭМ" in filename:
                standard = "VEM"
            elif "Ножев" in filename:
                standard = "Knife Steel"
            elif "Спец" in filename:
                standard = "Special Alloys"
            else:
                standard = "AISI"

        print(f"Importing {csv_path} as '{standard}'...")

        if not os.path.exists(csv_path):
            print(f"ERROR: File not found: {csv_path}")
            return {"imported": 0, "skipped": 0, "errors": 1}

        conn = get_connection()
        cursor = conn.cursor()

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                # Detect delimiter
                first_line = f.readline()
                delimiter = ';' if ';' in first_line else ','
                f.seek(0)

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    try:
                        # Skip empty rows or header rows
                        grade = self._extract_grade(row)
                        if not grade or grade in ['Аустенитные', 'Дуплексные', 'Ферритные', 'Мартенситные']:
                            continue

                        self._import_row(cursor, row, standard)

                    except Exception as e:
                        print(f"Error importing row: {e}")
                        print(f"Row data: {row}")
                        self.error_count += 1
                        continue

                # Commit all changes
                conn.commit()
                print(f"[OK] Imported: {self.imported_count}, Skipped: {self.skipped_count}, Errors: {self.error_count}")

        except Exception as e:
            print(f"ERROR: {e}")
            conn.rollback()
            self.error_count += 1

        finally:
            conn.close()

        return {
            "imported": self.imported_count,
            "skipped": self.skipped_count,
            "errors": self.error_count
        }

    def _extract_grade(self, row: Dict[str, str]) -> Optional[str]:
        """Extract grade name from row"""
        # Try common column names
        for col in ['Марка AISI и брендовые', 'Grade', 'Марка', 'AISI']:
            if col in row and row[col].strip():
                return row[col].strip()
        return None

    def _import_row(self, cursor: sqlite3.Cursor, row: Dict[str, str], standard: str):
        """Import single row from CSV"""

        # Get grade name
        grade = self._extract_grade(row)
        if not grade:
            self.skipped_count += 1
            return

        # Clean multiline grades (take only first line)
        if '\n' in grade:
            grade = grade.split('\n')[0].strip()

        # Check if grade already exists (exact match with standard)
        cursor.execute("SELECT id FROM steel_grades WHERE grade = ? AND standard = ?", (grade, standard))
        if cursor.fetchone():
            self.skipped_count += 1
            return

        # Extract chemical composition
        c = self._clean_value(row.get('C'))
        cr = self._clean_value(row.get('Cr'))
        ni = self._clean_value(row.get('Ni'))
        mo = self._clean_value(row.get('Mo'))
        mn = self._clean_value(row.get('Mn'))
        si = self._clean_value(row.get('Si'))
        s = self._clean_value(row.get('S'))
        p = self._clean_value(row.get('P'))
        n = self._clean_value(row.get('N'))
        cu = self._clean_value(row.get('Cu'))

        # Try to detect base element
        base = 'Fe'  # Default
        if ni and self._to_float(ni) > 50:
            base = 'Ni'
        elif cr and self._to_float(cr) > 50:
            base = 'Cr'

        # Get UNS and EN standards as analogues
        analogues_parts = []
        uns = row.get('UNS', '').strip()
        en = row.get('EN', '').strip()
        if uns:
            analogues_parts.append(uns)
        if en:
            analogues_parts.append(en)
        analogues = ' '.join(analogues_parts) if analogues_parts else None

        # Prepare data
        data = {
            'grade': grade,
            'base': base,
            'c': c,
            'cr': cr,
            'mo': mo,
            'v': None,  # Not in these CSVs
            'w': None,
            'co': None,
            'ni': ni,
            'mn': mn,
            'si': si,
            's': s,
            'p': p,
            'cu': cu,
            'nb': None,
            'n': n,
            'tech': None,
            'standard': standard,
            'manufacturer': None,
            'analogues': analogues,
            'link': None
        }

        # Insert into database
        cursor.execute("""
            INSERT INTO steel_grades (
                grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n,
                tech, standard, manufacturer, analogues, link
            ) VALUES (
                :grade, :base, :c, :cr, :mo, :v, :w, :co, :ni, :mn, :si, :s, :p, :cu, :nb, :n,
                :tech, :standard, :manufacturer, :analogues, :link
            )
        """, data)

        self.imported_count += 1

        if self.imported_count % 100 == 0:
            print(f"  Imported {self.imported_count} grades...")

    def _clean_value(self, value: str) -> Optional[str]:
        """Clean and normalize value"""
        if not value:
            return None

        value = str(value).strip()

        # Remove BOM and special characters
        value = value.replace('\ufeff', '')

        # Skip empty, dashes, or "—"
        if value in ['', '-', '—', 'N/A', 'n/a']:
            return None

        # Remove extra spaces
        value = ' '.join(value.split())

        # Handle ranges (keep as is for now)
        # e.g. "0,15-0,25" or "16,0-18,0"

        return value if value else None

    def _to_float(self, value: str) -> float:
        """Convert string to float (handle ranges by taking average)"""
        if not value:
            return 0.0

        try:
            # Handle ranges: "0,15-0,25" -> average
            if '-' in value:
                parts = value.replace(',', '.').split('-')
                return (float(parts[0]) + float(parts[1])) / 2
            else:
                return float(value.replace(',', '.'))
        except:
            return 0.0


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python steel_tables_importer.py --all              # Import all CSV files")
        print("  python steel_tables_importer.py --file grades.csv  # Import single file")
        sys.exit(1)

    importer = SteelTablesImporter()

    if sys.argv[1] == '--all':
        # Import all CSV files
        csv_files = [
            'Аустенитные стали.csv',
            'Дуплексные стали.csv',
            'Ферритные стали.csv',
            'Мартенситные.csv',
            'Марки ВЭМ.csv',
            'Ножевые.csv',
            'Спец сплавы.csv'
        ]

        total_imported = 0
        total_skipped = 0
        total_errors = 0

        for csv_file in csv_files:
            if os.path.exists(csv_file):
                result = importer.import_csv(csv_file)
                total_imported += result['imported']
                total_skipped += result['skipped']
                total_errors += result['errors']
                print()
            else:
                print(f"SKIP: {csv_file} not found")
                print()

        print("=" * 50)
        print(f"TOTAL: Imported {total_imported}, Skipped {total_skipped}, Errors {total_errors}")

    elif sys.argv[1] == '--file':
        csv_path = sys.argv[2]
        importer.import_csv(csv_path)


if __name__ == '__main__':
    main()
