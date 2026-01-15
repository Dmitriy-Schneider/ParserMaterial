#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Standard Column Script
===========================
Fixes incorrect Standard values:
- "AISI (Austenitic)" → "AISI, США"
- "GOST/TU-Extended" → "GOST, Россия"
- "UNS (Austenitic)" → "UNS, США"
- etc.
"""

import sqlite3
import logging
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_standard_column.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class StandardFixer:
    # Mapping of incorrect patterns to correct values
    STANDARD_FIXES = {
        # AISI variations
        'AISI (Austenitic)': 'AISI, США',
        'AISI (Martensitic)': 'AISI, США',
        'AISI (Ferritic)': 'AISI, США',
        'AISI (Duplex)': 'AISI, США',
        'AISI (PH)': 'AISI, США',

        # UNS variations
        'UNS (Austenitic)': 'UNS, США',
        'UNS (Martensitic)': 'UNS, США',
        'UNS (Ferritic)': 'UNS, США',
        'UNS (Duplex)': 'UNS, США',
        'UNS (PH)': 'UNS, США',

        # EN variations
        'EN (Austenitic)': 'EN, Европа',
        'EN (Martensitic)': 'EN, Европа',
        'EN (Ferritic)': 'EN, Европа',
        'EN (Duplex)': 'EN, Европа',

        # GOST variations
        'GOST/TU-Extended': 'GOST, Россия',
        'GOST Extended': 'GOST, Россия',
        'GOST/TU': 'GOST, Россия',

        # Other
        'Nb: 10×C to 1.0': 'EN, Европа',  # Wrong format
    }

    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.stats = {
            'total_fixed': 0,
            'by_pattern': {}
        }

    def find_incorrect_standards(self) -> List[Tuple]:
        """Find all incorrect standard values"""
        self.cursor.execute("""
            SELECT DISTINCT standard FROM steel_grades
            WHERE standard IS NOT NULL AND standard != ''
            ORDER BY standard
        """)
        all_standards = [row[0] for row in self.cursor.fetchall()]

        incorrect = []
        for std in all_standards:
            # Check if it matches any incorrect pattern
            if std in self.STANDARD_FIXES:
                incorrect.append(std)
            # Check for patterns with parentheses or Extended
            elif '(' in std or 'Extended' in std:
                incorrect.append(std)

        logging.info(f"Found {len(incorrect)} distinct incorrect standard values")
        return incorrect

    def fix_gost_patterns(self):
        """Fix all GOST standards with (A), (Б), etc."""
        # Fix all GOST with parentheses
        self.cursor.execute("""
            UPDATE steel_grades
            SET standard = 'GOST, Россия'
            WHERE standard LIKE 'GOST %(%'
        """)
        count = self.cursor.rowcount
        if count > 0:
            logging.info(f"  Fixed {count} GOST grades with parentheses")
            self.stats['total_fixed'] += count
            self.stats['by_pattern']['GOST patterns'] = count

    def fix_standard(self, old_value: str, new_value: str) -> int:
        """Fix all grades with old standard value"""
        self.cursor.execute("""
            UPDATE steel_grades
            SET standard = ?
            WHERE standard = ?
        """, (new_value, old_value))

        count = self.cursor.rowcount
        self.stats['by_pattern'][old_value] = count
        self.stats['total_fixed'] += count

        return count

    def run_fix(self):
        """Run fixing process"""
        logging.info("\n" + "="*80)
        logging.info("STANDARD COLUMN FIXER - STARTING")
        logging.info("="*80)

        # Find all incorrect standards
        incorrect = self.find_incorrect_standards()

        if not incorrect:
            logging.info("No incorrect standards found")
            self.conn.close()
            return

        logging.info("\nIncorrect standard values found:")
        for std in incorrect:
            logging.info(f"  - {std}")

        # Fix known patterns
        logging.info("\nFixing known patterns...")
        for old_value, new_value in self.STANDARD_FIXES.items():
            count = self.fix_standard(old_value, new_value)
            if count > 0:
                logging.info(f"  '{old_value}' → '{new_value}': {count} grades")

        # Fix GOST patterns with parentheses
        logging.info("\nFixing GOST patterns...")
        self.fix_gost_patterns()

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("FIXING STATISTICS")
        logging.info("="*80)
        logging.info(f"Total grades fixed: {self.stats['total_fixed']}")
        logging.info("="*80)

        # Show examples
        logging.info("\nExamples after fixing:")
        self.cursor.execute("""
            SELECT grade, standard FROM steel_grades
            WHERE standard IN ('AISI, США', 'UNS, США', 'EN, Европа', 'GOST, Россия')
            LIMIT 20
        """)
        for grade, standard in self.cursor.fetchall():
            logging.info(f"  {grade:<20} → {standard}")

        self.conn.close()

if __name__ == '__main__':
    fixer = StandardFixer()
    fixer.run_fix()
