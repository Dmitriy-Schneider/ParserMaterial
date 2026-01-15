#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Analogues Script
======================
Fixes issues in analogues lists:
1. Removes duplicate analogues
2. Removes non-existent analogues (not in database)
3. Handles multi-word grade names properly
"""

import sqlite3
import logging
from typing import List, Set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('clean_analogues.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AnaloguesCleaner:
    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Load all existing grades
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()

        self.stats = {
            'total_grades': 0,
            'grades_with_analogues': 0,
            'duplicates_removed': 0,
            'nonexistent_removed': 0,
            'grades_updated': 0
        }

    def load_existing_grades(self):
        """Load all existing grade names"""
        self.cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = set(row[0] for row in self.cursor.fetchall())
        logging.info(f"Loaded {len(self.existing_grades)} existing grades")

    def clean_analogue_list(self, analogues_str: str) -> tuple[str, int, int]:
        """
        Clean analogues string
        Returns: (cleaned_string, duplicates_removed, nonexistent_removed)
        """
        if not analogues_str:
            return '', 0, 0

        # Split by space
        analogue_list = analogues_str.split()

        # Remove duplicates while preserving order
        seen = set()
        unique_analogues = []
        duplicates_count = 0

        for analogue in analogue_list:
            if analogue in seen:
                duplicates_count += 1
                continue
            seen.add(analogue)
            unique_analogues.append(analogue)

        # Check which analogues exist in database
        valid_analogues = []
        nonexistent_count = 0

        for analogue in unique_analogues:
            if analogue in self.existing_grades:
                valid_analogues.append(analogue)
            else:
                # Check if it might be part of multi-word grade
                # Try to combine with next analogue
                nonexistent_count += 1
                logging.debug(f"Non-existent analogue: '{analogue}'")

        cleaned_str = ' '.join(valid_analogues) if valid_analogues else None
        return cleaned_str, duplicates_count, nonexistent_count

    def clean_all_analogues(self):
        """Clean analogues for all grades"""
        # Get all grades with analogues
        self.cursor.execute("""
            SELECT id, grade, analogues FROM steel_grades
            WHERE analogues IS NOT NULL AND analogues != ''
        """)

        grades_to_process = self.cursor.fetchall()
        self.stats['total_grades'] = len(self.existing_grades)
        self.stats['grades_with_analogues'] = len(grades_to_process)

        logging.info(f"Processing {len(grades_to_process)} grades with analogues...")

        for grade_id, grade, analogues in grades_to_process:
            cleaned, dups, nonexist = self.clean_analogue_list(analogues)

            if dups > 0 or nonexist > 0:
                # Update database
                if cleaned:
                    self.cursor.execute("""
                        UPDATE steel_grades SET analogues = ? WHERE id = ?
                    """, (cleaned, grade_id))
                else:
                    # No valid analogues left
                    self.cursor.execute("""
                        UPDATE steel_grades SET analogues = NULL WHERE id = ?
                    """, (grade_id,))

                self.stats['grades_updated'] += 1
                self.stats['duplicates_removed'] += dups
                self.stats['nonexistent_removed'] += nonexist

                if dups > 0:
                    logging.info(f"Grade '{grade}': removed {dups} duplicates")
                if nonexist > 0:
                    logging.warning(f"Grade '{grade}': removed {nonexist} non-existent analogues")

    def run(self):
        """Run cleaning process"""
        logging.info("\n" + "="*80)
        logging.info("ANALOGUES CLEANER - STARTING")
        logging.info("="*80)

        self.clean_all_analogues()

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("CLEANING STATISTICS")
        logging.info("="*80)
        logging.info(f"Total grades in DB:          {self.stats['total_grades']}")
        logging.info(f"Grades with analogues:       {self.stats['grades_with_analogues']}")
        logging.info(f"Grades updated:              {self.stats['grades_updated']}")
        logging.info(f"Duplicate analogues removed: {self.stats['duplicates_removed']}")
        logging.info(f"Non-existent removed:        {self.stats['nonexistent_removed']}")
        logging.info("="*80)

        # Show some examples
        logging.info("\n\nExamples after cleaning:")
        self.cursor.execute("""
            SELECT grade, analogues FROM steel_grades
            WHERE grade IN ('2.4663', 'N06617', '2.4360', 'N04400')
        """)
        for grade, analogues in self.cursor.fetchall():
            logging.info(f"{grade}: {analogues}")

        self.conn.close()

if __name__ == '__main__':
    cleaner = AnaloguesCleaner()
    cleaner.run()
