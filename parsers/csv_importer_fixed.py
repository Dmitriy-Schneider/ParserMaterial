#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fixed CSV Importer - Adds ALL missing grades
============================================
Fixes:
1. Adds grades even if they have only one manufacturer (Buderus only)
2. Properly fills Standard column for ALL grades
3. Links analogues correctly (2711 ISO-B <-> 1.2711)
4. Updates analogues for existing grades
"""

import sqlite3
import csv
import logging
from typing import Dict, List, Set, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_import_fixed.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class CSVImporterFixed:
    STANDARD_COUNTRIES = {
        'Bohler': 'Bohler Edelstahle, Австрия',
        'Uddeholm': 'Uddeholm, Швеция',
        'Buderus': 'Buderus, Германия',
        'EN': 'EN, Европа',
        'AISI': 'AISI, США',
        'UNS': 'UNS, США',
    }

    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()
        self.stats = {
            'total_processed': 0,
            'new_grades_added': 0,
            'analogues_updated': 0,
            'standard_updated': 0,
            'errors': 0
        }

    def load_existing_grades(self):
        self.cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = set(row[0] for row in self.cursor.fetchall())
        logging.info(f"Loaded {len(self.existing_grades)} existing grades")

    @staticmethod
    def clean_grade_name(grade: str) -> str:
        if not grade:
            return ''
        return grade.replace('®', '').strip()

    @staticmethod
    def parse_value(value: str) -> Optional[str]:
        if not value or value in ['', 'null', '—', '-']:
            return None
        value = str(value).strip()
        if value == '0' or value == '0.00':
            return None
        return value

    def get_grade_composition(self, grade_name: str) -> Optional[Dict]:
        """Get composition from existing grade in database"""
        self.cursor.execute("""
            SELECT c, si, mn, cr, mo, ni, v, w, co, cu, nb, n, s, p, other_elements
            FROM steel_grades WHERE grade = ?
        """, (grade_name,))
        row = self.cursor.fetchone()
        if row:
            return {
                'C': row[0], 'Si': row[1], 'Mn': row[2], 'Cr': row[3],
                'Mo': row[4], 'Ni': row[5], 'V': row[6], 'W': row[7],
                'Co': row[8], 'Cu': row[9], 'Nb': row[10], 'N': row[11],
                'S': row[12], 'P': row[13], 'Other': row[14]
            }
        return None

    def get_grade_analogues(self, grade_name: str) -> List[str]:
        """Get analogues from existing grade"""
        self.cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade_name,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return [a.strip() for a in row[0].split() if a.strip()]
        return []

    def update_standard(self, grade_name: str, standard: str):
        """Update Standard column for existing grade"""
        self.cursor.execute("""
            UPDATE steel_grades
            SET standard = ?
            WHERE grade = ? AND (standard IS NULL OR standard = '' OR standard = 'N/A')
        """, (standard, grade_name))
        if self.cursor.rowcount > 0:
            self.stats['standard_updated'] += 1
            logging.info(f"Updated Standard for {grade_name}: {standard}")

    def add_analogue_to_grade(self, target_grade: str, new_analogue: str):
        """Add new analogue to existing grade"""
        current_analogues = self.get_grade_analogues(target_grade)
        if new_analogue not in current_analogues:
            current_analogues.append(new_analogue)
            analogues_str = ' '.join(current_analogues)
            self.cursor.execute("""
                UPDATE steel_grades SET analogues = ? WHERE grade = ?
            """, (analogues_str, target_grade))
            logging.info(f"Added {new_analogue} to analogues of {target_grade}")

    def add_or_update_grade(self, grade_name: str, composition: Dict,
                           analogues: List[str], standard: str) -> bool:
        grade_name = self.clean_grade_name(grade_name)
        if not grade_name:
            return False

        analogues = [self.clean_grade_name(a) for a in analogues if a and self.clean_grade_name(a) != grade_name]
        analogues_str = ' '.join(analogues) if analogues else None

        if grade_name in self.existing_grades:
            # Update Standard if missing
            self.update_standard(grade_name, standard)

            # Update analogues
            for analogue in analogues:
                self.add_analogue_to_grade(grade_name, analogue)

            self.stats['analogues_updated'] += 1
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
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {file_path}")
        logging.info(f"{'='*80}")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        self.stats['total_processed'] += 1

                        # Extract ALL grade names (even if only one column filled)
                        grades = {}
                        if row.get('Bohler') and row['Bohler'].strip():
                            grades['Bohler'] = row['Bohler'].strip()
                        if row.get('Uddeholm') and row['Uddeholm'].strip():
                            grades['Uddeholm'] = row['Uddeholm'].strip()
                        if row.get('Buderus') and row['Buderus'].strip():
                            grades['Buderus'] = row['Buderus'].strip()
                        if row.get('EN') and row['EN'].strip():
                            # Handle "~" prefix
                            en_grade = row['EN'].strip()
                            if en_grade.startswith('~'):
                                en_grade = en_grade[1:].strip()
                            grades['EN'] = en_grade

                        # Skip if no grades at all
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

                        # All grade names become analogues of each other
                        all_grade_names = list(grades.values())

                        # Add each grade
                        for std, grade_name in grades.items():
                            # Analogues = all other names + any existing analogues
                            analogues = [g for g in all_grade_names if g != grade_name]

                            # If this grade exists in DB, get its analogues and add them
                            if grade_name in self.existing_grades:
                                existing_analogues = self.get_grade_analogues(grade_name)
                                for ea in existing_analogues:
                                    if ea not in analogues and ea not in all_grade_names:
                                        analogues.append(ea)

                            standard = self.STANDARD_COUNTRIES.get(std, std)
                            self.add_or_update_grade(grade_name, composition, analogues, standard)

                        # Cross-link: if one analogue exists in DB with other analogues,
                        # add all grades from this row to those analogues
                        for grade_name in all_grade_names:
                            if grade_name in self.existing_grades:
                                existing_analogues = self.get_grade_analogues(grade_name)
                                for ea in existing_analogues:
                                    if ea in self.existing_grades:
                                        for new_analogue in all_grade_names:
                                            if new_analogue != ea:
                                                self.add_analogue_to_grade(ea, new_analogue)

                    except Exception as e:
                        logging.error(f"Error processing row {row_num}: {e}")
                        self.stats['errors'] += 1

        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            self.stats['errors'] += 1

    def import_stainless_steels(self, file_path: str, category: str):
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {file_path} ({category})")
        logging.info(f"{'='*80}")

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Skip header rows
                        if row.get('Марка AISI и брендовые') in ['Аустенитные', 'Дуплексные',
                                                                   'Мартенситные', 'Ферритные',
                                                                   'Спец сплавы', '']:
                            continue

                        self.stats['total_processed'] += 1

                        grades = {}
                        if row.get('Марка AISI и брендовые') and row['Марка AISI и брендовые'].strip():
                            grades['AISI'] = row['Марка AISI и брендовые'].strip()
                        if row.get('UNS') and row['UNS'].strip():
                            grades['UNS'] = row['UNS'].strip()
                        if row.get('EN') and row['EN'].strip():
                            en_grade = row['EN'].strip()
                            if en_grade not in ['-', '—']:
                                grades['EN'] = en_grade

                        if not grades:
                            continue

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

    def run_import(self):
        logging.info("\n" + "="*80)
        logging.info("CSV FIXED IMPORTER - STARTING")
        logging.info("="*80)

        self.import_marki_vem()
        self.import_stainless_steels('Аустенитные стали.csv', 'Austenitic')
        self.import_stainless_steels('Дуплексные стали.csv', 'Duplex')
        self.import_stainless_steels('Мартенситные.csv', 'Martensitic')
        self.import_stainless_steels('Спец сплавы.csv', 'Special Alloys')
        self.import_stainless_steels('Ферритные стали.csv', 'Ferritic')

        self.conn.commit()

        logging.info("\n" + "="*80)
        logging.info("IMPORT STATISTICS")
        logging.info("="*80)
        logging.info(f"Total rows processed:    {self.stats['total_processed']}")
        logging.info(f"New grades added:        {self.stats['new_grades_added']}")
        logging.info(f"Analogues updated:       {self.stats['analogues_updated']}")
        logging.info(f"Standard updated:        {self.stats['standard_updated']}")
        logging.info(f"Errors:                  {self.stats['errors']}")
        logging.info("="*80)

        self.conn.close()

if __name__ == '__main__':
    importer = CSVImporterFixed()
    importer.run_import()
