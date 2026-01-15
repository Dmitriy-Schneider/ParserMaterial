#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split Merged Grades Script
===========================
Splits incorrectly merged grades into separate entries:
- 1.563475Ni8 → 1.5634 + 75Ni8
- 347/347H → 347 + 347H
- T11347M47 → T11347 + M47

Process:
1. Find merged grades where ALL parts exist in database
2. Add merged grade to analogues of BOTH parts
3. Remove merged grade from database
4. Update all analogues lists (remove merged, keep only parts)
"""

import sqlite3
import logging
import re
from typing import List, Tuple, Set, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('split_merged_grades.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MergedGradeSplitter:
    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()

        self.stats = {
            'merged_found': 0,
            'merged_removed': 0,
            'analogues_updated': 0,
            'parts_linked': 0
        }

        # List of confirmed merged grades (from find_merged_grades.py)
        self.merged_grades = []

    def load_existing_grades(self):
        """Load all existing grade names"""
        self.cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = set(row[0] for row in self.cursor.fetchall())
        logging.info(f"Loaded {len(self.existing_grades)} existing grades")

    def check_if_mergeable(self, grade: str) -> Dict:
        """
        Check if grade can be split and if split parts exist in database
        Returns: {
            'can_split': bool,
            'parts': [str],
            'parts_exist': [bool],
            'method': str
        }
        """
        result = {
            'can_split': False,
            'parts': [],
            'parts_exist': [],
            'method': None
        }

        # Method 1: Split by /
        if '/' in grade:
            parts = grade.split('/')
            result['parts'] = parts
            result['parts_exist'] = [p in self.existing_grades for p in parts]
            result['can_split'] = len(parts) >= 2
            result['method'] = 'slash'
            return result

        # Method 2: Pattern 1.XXXXYYYYLetters (e.g. 1.563475Ni8)
        match = re.match(r'^(1\.\d{4})(\d+[A-Za-z]\d*)$', grade)
        if match:
            parts = [match.group(1), match.group(2)]
            result['parts'] = parts
            result['parts_exist'] = [p in self.existing_grades for p in parts]
            result['can_split'] = True
            result['method'] = 'decimal_split'
            return result

        # Method 3: Pattern LettersDigitsDigitsLettersDigits (e.g. T11347M47)
        # Look for capital letter in middle of long number sequence
        match = re.match(r'^([A-Z]+\d+)([A-Z]\d+)$', grade)
        if match:
            parts = [match.group(1), match.group(2)]
            result['parts'] = parts
            result['parts_exist'] = [p in self.existing_grades for p in parts]
            result['can_split'] = True
            result['method'] = 'capital_letter_split'
            return result

        return result

    def find_all_merged_grades(self) -> List[Dict]:
        """Find all merged grades where ALL parts exist"""
        # Get all grades
        self.cursor.execute("SELECT grade, id, analogues FROM steel_grades")
        all_grades = self.cursor.fetchall()

        merged = []
        for grade, grade_id, analogues in all_grades:
            split_info = self.check_if_mergeable(grade)
            if split_info['can_split'] and all(split_info['parts_exist']):
                merged.append({
                    'grade': grade,
                    'id': grade_id,
                    'analogues': analogues,
                    'parts': split_info['parts'],
                    'method': split_info['method']
                })

        logging.info(f"Found {len(merged)} merged grades where all parts exist")
        return merged

    def get_grade_analogues(self, grade_name: str) -> List[str]:
        """Get analogues from existing grade"""
        self.cursor.execute("SELECT analogues FROM steel_grades WHERE grade = ?", (grade_name,))
        row = self.cursor.fetchone()
        if row and row[0]:
            return [a.strip() for a in row[0].split() if a.strip()]
        return []

    def add_analogue_to_grade(self, target_grade: str, new_analogue: str):
        """Add new analogue to existing grade"""
        current_analogues = self.get_grade_analogues(target_grade)
        if new_analogue not in current_analogues:
            current_analogues.append(new_analogue)
            analogues_str = ' '.join(current_analogues)
            self.cursor.execute("""
                UPDATE steel_grades SET analogues = ? WHERE grade = ?
            """, (analogues_str, target_grade))
            self.stats['analogues_updated'] += 1

    def remove_from_analogues(self, grade_to_remove: str):
        """Remove grade from all analogue lists"""
        self.cursor.execute("""
            SELECT id, grade, analogues FROM steel_grades
            WHERE analogues IS NOT NULL AND analogues != ''
        """)
        all_grades = self.cursor.fetchall()

        for grade_id, grade, analogues in all_grades:
            if not analogues:
                continue

            analogue_list = analogues.split()
            if grade_to_remove in analogue_list:
                analogue_list.remove(grade_to_remove)
                new_analogues = ' '.join(analogue_list) if analogue_list else None
                self.cursor.execute("""
                    UPDATE steel_grades SET analogues = ? WHERE id = ?
                """, (new_analogues, grade_id))
                self.stats['analogues_updated'] += 1
                logging.info(f"Removed '{grade_to_remove}' from analogues of '{grade}'")

    def split_merged_grade(self, merged_info: Dict):
        """
        Split a merged grade:
        1. Link parts together as analogues (if both exist)
        2. Remove merged grade from analogues lists
        3. Delete merged grade from database
        """
        merged_grade = merged_info['grade']
        parts = merged_info['parts']
        method = merged_info['method']

        logging.info(f"\nProcessing: {merged_grade} → {' + '.join(parts)} ({method})")

        # Step 1: Link parts together as analogues
        if len(parts) == 2:
            part1, part2 = parts
            # Add part2 to part1's analogues
            self.add_analogue_to_grade(part1, part2)
            # Add part1 to part2's analogues
            self.add_analogue_to_grade(part2, part1)
            self.stats['parts_linked'] += 1
            logging.info(f"  Linked {part1} <-> {part2}")

        # Step 2: Remove merged grade from all analogue lists
        self.remove_from_analogues(merged_grade)

        # Step 3: Delete merged grade from database
        self.cursor.execute("DELETE FROM steel_grades WHERE grade = ?", (merged_grade,))
        self.stats['merged_removed'] += 1
        logging.info(f"  Deleted merged grade: {merged_grade}")

    def run_split(self):
        """Run splitting process"""
        logging.info("\n" + "="*80)
        logging.info("MERGED GRADES SPLITTER - STARTING")
        logging.info("="*80)

        # Find all merged grades
        self.merged_grades = self.find_all_merged_grades()
        self.stats['merged_found'] = len(self.merged_grades)

        if not self.merged_grades:
            logging.info("No merged grades found")
            self.conn.close()
            return

        # Show what will be split
        logging.info("\nGrades to be split:")
        for m in self.merged_grades[:20]:  # Show first 20
            logging.info(f"  {m['grade']} → {' + '.join(m['parts'])}")
        if len(self.merged_grades) > 20:
            logging.info(f"  ... and {len(self.merged_grades) - 20} more")

        # Process each merged grade
        for merged_info in self.merged_grades:
            self.split_merged_grade(merged_info)

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("SPLITTING STATISTICS")
        logging.info("="*80)
        logging.info(f"Merged grades found:     {self.stats['merged_found']}")
        logging.info(f"Merged grades removed:   {self.stats['merged_removed']}")
        logging.info(f"Parts linked:            {self.stats['parts_linked']}")
        logging.info(f"Analogue lists updated:  {self.stats['analogues_updated']}")
        logging.info("="*80)

        # Show examples after splitting
        logging.info("\nExamples of remaining grades:")
        for merged_info in self.merged_grades[:5]:
            parts = merged_info['parts']
            if len(parts) == 2:
                part1, part2 = parts
                # Check analogues after split
                analogues1 = self.get_grade_analogues(part1)
                analogues2 = self.get_grade_analogues(part2)
                logging.info(f"\n{part1}:")
                logging.info(f"  Analogues: {' '.join(analogues1[:10])}...")
                logging.info(f"{part2}:")
                logging.info(f"  Analogues: {' '.join(analogues2[:10])}...")

        self.conn.close()

if __name__ == '__main__':
    splitter = MergedGradeSplitter()
    splitter.run_split()
