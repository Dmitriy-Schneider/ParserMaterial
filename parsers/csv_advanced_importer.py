#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced CSV Importer for ParserSteel Project
==============================================

Imports grades from multiple CSV files:
1. Марки ВЭМ.csv - Bohler, Uddeholm, Buderus, EN grades
2. Аустенитные стали.csv - Austenitic steels (AISI, UNS, EN)
3. Дуплексные стали.csv - Duplex steels
4. Мартенситные.csv - Martensitic steels
5. Спец сплавы.csv - Special alloys
6. Ферритные стали.csv - Ferritic steels
7. Ножевые.csv - Knife steels (no analogues)

Features:
- Checks against existing database
- Adds only missing grades
- Updates analogues for existing grades
- Removes ® symbol automatically
- Sets Standard column with manufacturer/country info
"""

import sqlite3
import csv
import re
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class CSVAdvancedImporter:
    # Manufacturer/Standard country mapping
    STANDARD_COUNTRIES = {
        'Bohler': 'Bohler Edelstahle, Австрия',
        'Uddeholm': 'Uddeholm, Швеция',
        'Buderus': 'Buderus, Германия',
        'EN': 'EN, Европа',
        'AISI': 'AISI, США',
        'UNS': 'UNS, США',
        'GOST': 'GOST, Россия',
        'JIS': 'JIS, Япония',
        'DIN': 'DIN, Германия',
        'GB': 'GB, Китай'
    }

    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Load existing grades to avoid duplicates
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()

        # Statistics
        self.stats = {
            'total_processed': 0,
            'new_grades_added': 0,
            'analogues_updated': 0,
            'skipped_existing': 0,
            'errors': 0
        }

    def load_existing_grades(self):
        """Load all existing grades from database"""
        self.cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = set(row[0] for row in self.cursor.fetchall())
        logging.info(f"Loaded {len(self.existing_grades)} existing grades from database")

    @staticmethod
    def clean_grade_name(grade: str) -> str:
        """Remove ® symbol and clean grade name"""
        if not grade:
            return ''
        return grade.replace('®', '').strip()

    @staticmethod
    def parse_value(value: str) -> Optional[str]:
        """Parse and clean chemical composition value"""
        if not value or value in ['', 'null', '—', '-']:
            return None
        value = str(value).strip()
        if value == '0' or value == '0.00':
            return None
        return value

    def add_or_update_grade(self, grade_name: str, composition: Dict,
                           analogues: List[str], standard: str) -> bool:
        """
        Add new grade or update analogues for existing grade
        Returns True if grade was added, False if updated
        """
        grade_name = self.clean_grade_name(grade_name)
        if not grade_name:
            return False

        # Clean analogue names
        analogues = [self.clean_grade_name(a) for a in analogues if a and a != grade_name]
        analogues_str = ' '.join(analogues) if analogues else None

        if grade_name in self.existing_grades:
            # Update analogues only
            self.cursor.execute("""
                UPDATE steel_grades
                SET analogues = CASE
                    WHEN analogues IS NULL OR analogues = '' THEN ?
                    ELSE analogues || ' ' || ?
                END
                WHERE grade = ?
            """, (analogues_str, analogues_str, grade_name))
            self.stats['analogues_updated'] += 1
            logging.info(f"Updated analogues for existing grade: {grade_name}")
            return False
        else:
            # Add new grade
            self.cursor.execute("""
                INSERT INTO steel_grades (
                    grade, c, si, mn, cr, mo, ni, v, w, co, cu, nb, n, s, p,
                    other_elements, analogues, standard
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                grade_name,
                self.parse_value(composition.get('C')),
                self.parse_value(composition.get('Si')),
                self.parse_value(composition.get('Mn')),
                self.parse_value(composition.get('Cr')),
                self.parse_value(composition.get('Mo')),
                self.parse_value(composition.get('Ni')),
                self.parse_value(composition.get('V')),
                self.parse_value(composition.get('W')),
                self.parse_value(composition.get('Co')),
                self.parse_value(composition.get('Cu')),
                self.parse_value(composition.get('Nb')),
                self.parse_value(composition.get('N')),
                self.parse_value(composition.get('S')),
                self.parse_value(composition.get('P')),
                self.parse_value(composition.get('Other')),
                analogues_str,
                standard
            ))
            self.existing_grades.add(grade_name)
            self.stats['new_grades_added'] += 1
            logging.info(f"Added new grade: {grade_name} ({standard})")
            return True

    def import_marki_vem(self, file_path: str = 'Марки ВЭМ.csv'):
        """Import grades from Марки ВЭМ.csv"""
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {file_path}")
        logging.info(f"{'='*80}")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        self.stats['total_processed'] += 1

                        # Extract grade names from different columns
                        grades = {}
                        if row.get('Bohler') and row['Bohler'].strip():
                            grades['Bohler'] = row['Bohler'].strip()
                        if row.get('Uddeholm') and row['Uddeholm'].strip():
                            grades['Uddeholm'] = row['Uddeholm'].strip()
                        if row.get('Buderus') and row['Buderus'].strip():
                            grades['Buderus'] = row['Buderus'].strip()
                        if row.get('EN') and row['EN'].strip():
                            grades['EN'] = row['EN'].strip()

                        if not grades:
                            continue

                        # Chemical composition
                        composition = {
                            'C': row.get('C'),
                            'Si': row.get('Si'),
                            'Mn': row.get('Mn'),
                            'Cr': row.get('Cr'),
                            'Mo': row.get('Mo'),
                            'Ni': row.get('Ni'),
                            'V': row.get('V'),
                            'W': row.get('W'),
                            'Co': None,
                            'Cu': None,
                            'Nb': None,
                            'N': None,
                            'S': None,
                            'P': None,
                            'Other': row.get('проч')
                        }

                        # Add each grade name as a separate entry
                        all_grade_names = list(grades.values())

                        for std, grade_name in grades.items():
                            # Analogues = all other names
                            analogues = [g for g in all_grade_names if g != grade_name]

                            # Determine standard string
                            standard = self.STANDARD_COUNTRIES.get(std, std)

                            self.add_or_update_grade(grade_name, composition, analogues, standard)

                    except Exception as e:
                        logging.error(f"Error processing row {row_num}: {e}")
                        self.stats['errors'] += 1

        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            self.stats['errors'] += 1

    def import_stainless_steels(self, file_path: str, category: str):
        """
        Import stainless steel grades (Аустенитные, Дуплексные, Мартенситные, etc.)
        Format: Марка AISI | UNS | EN | C | Mn | Si | Cr | Ni | P | S | Mo | N | Cu | Прочие
        """
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {file_path} ({category})")
        logging.info(f"{'='*80}")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Skip header rows
                        if row.get('Марка AISI и брендовые') in ['Аустенитные', 'Дуплексные', 'Мартенситные',
                                                                   'Ферритные', 'Спец сплавы', '']:
                            continue

                        self.stats['total_processed'] += 1

                        # Extract grade names
                        grades = {}
                        if row.get('Марка AISI и брендовые') and row['Марка AISI и брендовые'].strip():
                            grades['AISI'] = row['Марка AISI и брендовые'].strip()
                        if row.get('UNS') and row['UNS'].strip():
                            grades['UNS'] = row['UNS'].strip()
                        if row.get('EN') and row['EN'].strip():
                            grades['EN'] = row['EN'].strip()

                        if not grades:
                            continue

                        # Chemical composition
                        composition = {
                            'C': row.get('C'),
                            'Si': row.get('Si'),
                            'Mn': row.get('Mn'),
                            'Cr': row.get('Cr'),
                            'Mo': row.get('Mo'),
                            'Ni': row.get('Ni'),
                            'V': None,
                            'W': None,
                            'Co': None,
                            'Cu': row.get('Cu'),
                            'Nb': None,
                            'N': row.get('N'),
                            'S': row.get('S'),
                            'P': row.get('P'),
                            'Other': row.get('Прочие элементы')
                        }

                        # Add each grade name
                        all_grade_names = list(grades.values())

                        for std, grade_name in grades.items():
                            analogues = [g for g in all_grade_names if g != grade_name]
                            standard = self.STANDARD_COUNTRIES.get(std, std)
                            self.add_or_update_grade(grade_name, composition, analogues, standard)

                    except Exception as e:
                        logging.error(f"Error processing row {row_num} in {file_path}: {e}")
                        self.stats['errors'] += 1

        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            self.stats['errors'] += 1

    def import_knife_steels(self, file_path: str = 'Ножевые.csv'):
        """
        Import knife steels (no analogues, just single names)
        Format: Steel | C(%) | Cr (%) | V(%) | Mo (%) | W(%) | Nb (%) | Co (%) | Ni (%) | N(%)
        """
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {file_path}")
        logging.info(f"{'='*80}")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        self.stats['total_processed'] += 1

                        grade_name = row.get('Steel', '').strip()
                        if not grade_name:
                            continue

                        # Chemical composition
                        composition = {
                            'C': row.get('C(%)'),
                            'Si': None,
                            'Mn': None,
                            'Cr': row.get('Cr (%)'),
                            'Mo': row.get('Mo (%)'),
                            'Ni': row.get('Ni (%)'),
                            'V': row.get('V(%)'),
                            'W': row.get('W(%)'),
                            'Co': row.get('Co (%)'),
                            'Cu': None,
                            'Nb': row.get('Nb (%)'),
                            'N': row.get('N(%)'),
                            'S': None,
                            'P': None,
                            'Other': None
                        }

                        # No analogues, just add the grade
                        self.add_or_update_grade(grade_name, composition, [], 'Knife Steel')

                    except Exception as e:
                        logging.error(f"Error processing row {row_num} in {file_path}: {e}")
                        self.stats['errors'] += 1

        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            self.stats['errors'] += 1

    def run_import(self):
        """Run complete import process"""
        logging.info("\n" + "="*80)
        logging.info("CSV ADVANCED IMPORTER - STARTING")
        logging.info("="*80)

        # Import all files
        self.import_marki_vem()
        self.import_stainless_steels('Аустенитные стали.csv', 'Austenitic')
        self.import_stainless_steels('Дуплексные стали.csv', 'Duplex')
        self.import_stainless_steels('Мартенситные.csv', 'Martensitic')
        self.import_stainless_steels('Спец сплавы.csv', 'Special Alloys')
        self.import_stainless_steels('Ферритные стали.csv', 'Ferritic')
        self.import_knife_steels()

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("IMPORT STATISTICS")
        logging.info("="*80)
        logging.info(f"Total rows processed:    {self.stats['total_processed']}")
        logging.info(f"New grades added:        {self.stats['new_grades_added']}")
        logging.info(f"Analogues updated:       {self.stats['analogues_updated']}")
        logging.info(f"Skipped (existing):      {self.stats['skipped_existing']}")
        logging.info(f"Errors:                  {self.stats['errors']}")
        logging.info("="*80)

        # Close connection
        self.conn.close()

if __name__ == '__main__':
    importer = CSVAdvancedImporter()
    importer.run_import()
