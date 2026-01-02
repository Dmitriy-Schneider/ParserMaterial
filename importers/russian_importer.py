"""
Russian Steel Grades Importer
Импорт российских марок стали из CSV файлов в базу данных
"""

import csv
import sqlite3
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database_schema import get_connection
import config


class RussianImporter:
    """Импортер российских марок стали из CSV"""

    def __init__(self, db_path: str = None):
        """
        Initialize importer

        Args:
            db_path: Path to database file (defaults to config.DB_FILE)
        """
        self.db_path = db_path or config.DB_FILE
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def import_csv(self, csv_path: str, source: str = "GOST") -> Dict[str, int]:
        """
        Import steel grades from CSV file

        Args:
            csv_path: Path to CSV file
            source: Source/standard name (GOST, TU, etc.)

        Returns:
            Dictionary with import statistics
        """
        print(f"Importing {csv_path}...")

        if not os.path.exists(csv_path):
            print(f"ERROR: File not found: {csv_path}")
            return {"imported": 0, "skipped": 0, "errors": 1}

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Read CSV with proper encoding
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                # Detect delimiter
                first_line = f.readline()
                delimiter = ';' if ';' in first_line else ','
                f.seek(0)

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    try:
                        self._import_row(cursor, row, source)
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

    def _import_row(self, cursor: sqlite3.Cursor, row: Dict[str, str], source: str):
        """Import single row from CSV"""

        # Get grade name
        grade = row.get('Grade', '').strip()
        if not grade:
            self.skipped_count += 1
            return

        # Check if grade already exists
        cursor.execute("SELECT id FROM steel_grades WHERE grade = ?", (grade,))
        if cursor.fetchone():
            self.skipped_count += 1
            return

        # Prepare data
        data = {
            'grade': grade,
            'base': self._clean_value(row.get('Base', 'Fe')),
            'c': self._clean_value(row.get('C')),
            'cr': self._clean_value(row.get('Cr')),
            'mo': self._clean_value(row.get('Mo')),
            'v': self._clean_value(row.get('V')),
            'w': self._clean_value(row.get('W')),
            'co': self._clean_value(row.get('Co')),
            'ni': self._clean_value(row.get('Ni')),
            'mn': self._clean_value(row.get('Mn')),
            'si': self._clean_value(row.get('Si')),
            's': self._clean_value(row.get('S')),
            'p': self._clean_value(row.get('P')),
            'cu': self._clean_value(row.get('Cu')),
            'nb': self._clean_value(row.get('Nb')),
            'n': self._clean_value(row.get('N')),
            'tech': self._clean_value(row.get('Tech')),
            'standard': source,
            'manufacturer': self._clean_value(row.get('Maker')),
            'analogues': self._clean_value(row.get('CC', '')),  # Cross-country analogues
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

        if self.imported_count % 1000 == 0:
            print(f"  Imported {self.imported_count} grades...")

    def _clean_value(self, value: str) -> str:
        """Clean and normalize value"""
        if not value:
            return None

        value = value.strip()

        # Remove quotes
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        # Empty or placeholder values
        if value in ('', '-', 'N/A', 'n/a', '0', '0.00'):
            return None

        return value

    def import_all_russian_files(self, directory: str = "."):
        """
        Import all Russian CSV files from directory

        Args:
            directory: Directory containing CSV files
        """
        csv_files = [
            ("Марки сталей.csv", "GOST/TU"),
            ("Аустенитные стали.csv", "GOST-Austenitic"),
            ("Дуплексные стали.csv", "GOST-Duplex"),
            ("Марки ВЭМ.csv", "VEM"),
            ("Мартенситные.csv", "GOST-Martensitic"),
            ("Ножевые.csv", "GOST-Knife"),
            ("Ферритные стали.csv", "GOST-Ferritic"),
            ("Спец сплавы.csv", "GOST-Special"),
            ("russian_steel_grades.csv", "GOST"),
        ]

        total_stats = {
            "imported": 0,
            "skipped": 0,
            "errors": 0
        }

        for filename, source in csv_files:
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                stats = self.import_csv(filepath, source)
                total_stats["imported"] += stats["imported"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]
            else:
                print(f"Skipping {filename} (not found)")

        print(f"\n{'='*60}")
        print(f"TOTAL RESULTS:")
        print(f"  Imported: {total_stats['imported']:,}")
        print(f"  Skipped:  {total_stats['skipped']:,}")
        print(f"  Errors:   {total_stats['errors']:,}")
        print(f"{'='*60}")

        return total_stats


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Import Russian steel grades from CSV')
    parser.add_argument('--file', '-f', help='Single CSV file to import')
    parser.add_argument('--source', '-s', default='GOST', help='Source/standard name')
    parser.add_argument('--all', '-a', action='store_true', help='Import all CSV files')
    parser.add_argument('--dir', '-d', default='.', help='Directory with CSV files')

    args = parser.parse_args()

    importer = RussianImporter()

    if args.all:
        importer.import_all_russian_files(args.dir)
    elif args.file:
        importer.import_csv(args.file, args.source)
    else:
        print("Usage:")
        print("  python russian_importer.py --all              # Import all files")
        print("  python russian_importer.py --file grades.csv  # Import single file")


if __name__ == "__main__":
    main()
