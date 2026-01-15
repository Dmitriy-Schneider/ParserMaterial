#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find Merged Grades Script
==========================
Finds grades that are incorrectly merged from multiple grades:
- 1.563475Ni8 → 1.5634 + 75Ni8
- 347/347H → 347 + 347H
- T11347M47 → T11347 + M47

Strategy:
1. Find grades with "/" (likely merged with slash)
2. Find very long grade names (possible merges)
3. Check analogues for clues about correct splitting
4. Verify with source CSV files
"""

import sqlite3
import logging
import re
from typing import List, Tuple, Set, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('find_merged_grades.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MergedGradeFinder:
    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.existing_grades: Set[str] = set()
        self.load_existing_grades()

        self.suspicious_grades: List[Tuple] = []

    def load_existing_grades(self):
        """Load all existing grade names"""
        self.cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = set(row[0] for row in self.cursor.fetchall())
        logging.info(f"Loaded {len(self.existing_grades)} existing grades")

    def find_grades_with_slash(self) -> List[Tuple]:
        """Find grades with / in name (e.g. 347/347H)"""
        self.cursor.execute("""
            SELECT grade, id, analogues FROM steel_grades
            WHERE grade LIKE '%/%'
            ORDER BY grade
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} grades with '/' in name")
        return results

    def find_very_long_grades(self, min_length: int = 15) -> List[Tuple]:
        """Find very long grade names (possible merges)"""
        self.cursor.execute(f"""
            SELECT grade, id, analogues FROM steel_grades
            WHERE LENGTH(grade) >= ?
            ORDER BY LENGTH(grade) DESC
        """, (min_length,))
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} grades with length >= {min_length}")
        return results

    def find_unusual_patterns(self) -> List[Tuple]:
        """
        Find grades with unusual patterns suggesting merges:
        - Multiple number groups (1.5634 + 75Ni8 = 1.563475Ni8)
        - Letter groups in middle (T11347 + M47 = T11347M47)
        """
        self.cursor.execute("""
            SELECT grade, id, analogues FROM steel_grades
            ORDER BY grade
        """)
        all_grades = self.cursor.fetchall()

        suspicious = []
        for grade, grade_id, analogues in all_grades:
            # Pattern: digits.digits+digits+letters (e.g. 1.563475Ni8)
            if re.search(r'\d\.\d{4}\d+[A-Za-z]', grade):
                suspicious.append((grade, grade_id, analogues, "decimal+digits+letters"))

            # Pattern: letters+many_digits+letters (e.g. T11347M47)
            elif re.search(r'^[A-Z]+\d{5,}[A-Z]\d+$', grade):
                suspicious.append((grade, grade_id, analogues, "letters+long_digits+letters"))

        logging.info(f"Found {len(suspicious)} grades with unusual patterns")
        return suspicious

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

    def analyze_all_suspicious(self):
        """Find and analyze all suspicious grades"""
        logging.info("\n" + "="*80)
        logging.info("MERGED GRADES FINDER - STARTING")
        logging.info("="*80)

        # 1. Grades with /
        logging.info("\n[1/3] Finding grades with '/' ...")
        slash_grades = self.find_grades_with_slash()

        for grade, grade_id, analogues in slash_grades:
            split_info = self.check_if_mergeable(grade)
            if split_info['can_split']:
                self.suspicious_grades.append({
                    'grade': grade,
                    'id': grade_id,
                    'analogues': analogues,
                    'split_parts': split_info['parts'],
                    'parts_exist': split_info['parts_exist'],
                    'method': split_info['method']
                })

                parts_status = ' / '.join([
                    f"{p} ({'EXISTS' if exists else 'NOT FOUND'})"
                    for p, exists in zip(split_info['parts'], split_info['parts_exist'])
                ])
                logging.warning(f"SUSPICIOUS: {grade} → {parts_status}")

        # 2. Very long grades
        logging.info("\n[2/3] Finding very long grades...")
        long_grades = self.find_very_long_grades(min_length=12)

        for grade, grade_id, analogues in long_grades:
            # Skip if already in suspicious list
            if any(s['grade'] == grade for s in self.suspicious_grades):
                continue

            split_info = self.check_if_mergeable(grade)
            if split_info['can_split']:
                self.suspicious_grades.append({
                    'grade': grade,
                    'id': grade_id,
                    'analogues': analogues,
                    'split_parts': split_info['parts'],
                    'parts_exist': split_info['parts_exist'],
                    'method': split_info['method']
                })

                parts_status = ' / '.join([
                    f"{p} ({'EXISTS' if exists else 'NOT FOUND'})"
                    for p, exists in zip(split_info['parts'], split_info['parts_exist'])
                ])
                logging.warning(f"SUSPICIOUS: {grade} → {parts_status}")

        # 3. Unusual patterns
        logging.info("\n[3/3] Finding unusual patterns...")
        unusual = self.find_unusual_patterns()

        for grade, grade_id, analogues, pattern_type in unusual:
            # Skip if already in suspicious list
            if any(s['grade'] == grade for s in self.suspicious_grades):
                continue

            split_info = self.check_if_mergeable(grade)
            if split_info['can_split']:
                self.suspicious_grades.append({
                    'grade': grade,
                    'id': grade_id,
                    'analogues': analogues,
                    'split_parts': split_info['parts'],
                    'parts_exist': split_info['parts_exist'],
                    'method': split_info['method'],
                    'pattern': pattern_type
                })

                parts_status = ' / '.join([
                    f"{p} ({'EXISTS' if exists else 'NOT FOUND'})"
                    for p, exists in zip(split_info['parts'], split_info['parts_exist'])
                ])
                logging.warning(f"SUSPICIOUS ({pattern_type}): {grade} → {parts_status}")

        # Print summary
        logging.info("\n" + "="*80)
        logging.info("ANALYSIS COMPLETE")
        logging.info("="*80)
        logging.info(f"Total suspicious grades found: {len(self.suspicious_grades)}")

        # Group by method
        by_method = {}
        for s in self.suspicious_grades:
            method = s.get('method', 'unknown')
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(s)

        for method, grades in by_method.items():
            logging.info(f"\n{method.upper()}: {len(grades)} grades")
            for g in grades[:10]:  # Show first 10
                parts_exist_str = ', '.join([
                    f"{p}:{'✓' if e else '✗'}"
                    for p, e in zip(g['split_parts'], g['parts_exist'])
                ])
                logging.info(f"  {g['grade']} → [{parts_exist_str}]")

        # Find grades where ALL parts exist
        logging.info("\n" + "="*80)
        logging.info("GRADES WHERE ALL PARTS EXIST (HIGH CONFIDENCE)")
        logging.info("="*80)

        high_confidence = [s for s in self.suspicious_grades if all(s['parts_exist'])]
        logging.info(f"Found {len(high_confidence)} grades where all parts exist in database")

        for s in high_confidence:
            logging.info(f"\n{s['grade']} → {' + '.join(s['split_parts'])}")
            logging.info(f"  Method: {s['method']}")
            logging.info(f"  Analogues: {s['analogues']}")

        self.conn.close()

if __name__ == '__main__':
    finder = MergedGradeFinder()
    finder.analyze_all_suspicious()
