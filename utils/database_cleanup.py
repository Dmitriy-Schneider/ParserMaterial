#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Cleanup Script
=======================
Fixes errors found in database:
1. Remove empty/invalid grades (-, empty string)
2. Remove Knife Steel grades (imported incorrectly)
3. Remove grades with question marks in composition
4. Remove duplicate grades with different case (keep ones with links)
5. Find grades with missing Standard column
"""

import sqlite3
import logging
from typing import List, Tuple, Set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_cleanup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DatabaseCleanup:
    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.stats = {
            'empty_grades_removed': 0,
            'knife_steel_removed': 0,
            'question_marks_removed': 0,
            'duplicates_removed': 0,
            'missing_standard': 0
        }

    def find_empty_grades(self) -> List[str]:
        """Find grades with empty or invalid names"""
        self.cursor.execute("""
            SELECT grade, id FROM steel_grades
            WHERE grade IS NULL
               OR grade = ''
               OR grade = '-'
               OR TRIM(grade) = ''
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} empty/invalid grades")
        return results

    def remove_empty_grades(self):
        """Remove empty/invalid grades"""
        results = self.find_empty_grades()
        if results:
            for grade, grade_id in results:
                logging.info(f"Removing empty grade: id={grade_id}, grade='{grade}'")
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (grade_id,))
                self.stats['empty_grades_removed'] += 1

    def find_knife_steel_grades(self) -> List[Tuple]:
        """Find grades with 'Knife Steel' in Standard column"""
        self.cursor.execute("""
            SELECT grade, id FROM steel_grades
            WHERE standard LIKE '%Knife Steel%'
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} Knife Steel grades to remove")
        return results

    def remove_knife_steel_grades(self):
        """Remove Knife Steel grades"""
        results = self.find_knife_steel_grades()
        if results:
            for grade, grade_id in results:
                logging.info(f"Removing Knife Steel grade: {grade}")
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (grade_id,))
                self.stats['knife_steel_removed'] += 1

    def find_question_mark_grades(self) -> List[Tuple]:
        """Find grades with question marks in composition"""
        columns = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']
        conditions = ' OR '.join([f"{col} LIKE '%?%'" for col in columns])

        query = f"""
            SELECT grade, id FROM steel_grades
            WHERE {conditions}
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} grades with question marks")
        return results

    def remove_question_mark_grades(self):
        """Remove grades with question marks in composition"""
        results = self.find_question_mark_grades()
        if results:
            for grade, grade_id in results:
                logging.info(f"Removing grade with question marks: {grade}")
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (grade_id,))
                self.stats['question_marks_removed'] += 1

    def find_duplicates_by_case(self) -> List[Tuple]:
        """
        Find duplicate grades with different case
        Returns list of (grade1, grade2, link1, link2)
        Keep grade with link, remove one without link
        """
        self.cursor.execute("""
            SELECT a.grade, b.grade, a.link, b.link, a.id, b.id
            FROM steel_grades a
            JOIN steel_grades b ON LOWER(a.grade) = LOWER(b.grade)
            WHERE a.id < b.id
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} potential duplicate pairs")
        return results

    def remove_duplicates_by_case(self):
        """Remove duplicate grades, keeping ones with links"""
        duplicates = self.find_duplicates_by_case()
        removed_ids = set()

        for grade1, grade2, link1, link2, id1, id2 in duplicates:
            # Skip if already removed
            if id1 in removed_ids or id2 in removed_ids:
                continue

            # Priority: keep grade with link
            if link1 and not link2:
                # Keep id1, remove id2
                logging.info(f"Removing duplicate (no link): {grade2} (keeping {grade1})")
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id2,))
                removed_ids.add(id2)
                self.stats['duplicates_removed'] += 1
            elif link2 and not link1:
                # Keep id2, remove id1
                logging.info(f"Removing duplicate (no link): {grade1} (keeping {grade2})")
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id1,))
                removed_ids.add(id1)
                self.stats['duplicates_removed'] += 1
            elif not link1 and not link2:
                # Neither has link - keep first alphabetically (lowercase comparison)
                if grade1.lower() < grade2.lower():
                    logging.info(f"Removing duplicate: {grade2} (keeping {grade1})")
                    self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id2,))
                    removed_ids.add(id2)
                    self.stats['duplicates_removed'] += 1
                else:
                    logging.info(f"Removing duplicate: {grade1} (keeping {grade2})")
                    self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (id1,))
                    removed_ids.add(id1)
                    self.stats['duplicates_removed'] += 1

    def find_missing_standard(self) -> List[Tuple]:
        """Find grades with missing Standard column"""
        self.cursor.execute("""
            SELECT grade, id FROM steel_grades
            WHERE standard IS NULL OR standard = '' OR standard = 'N/A'
            ORDER BY grade
            LIMIT 50
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} grades with missing Standard (showing first 50)")
        return results

    def run_cleanup(self):
        """Run all cleanup operations"""
        logging.info("\n" + "="*80)
        logging.info("DATABASE CLEANUP - STARTING")
        logging.info("="*80)

        # 1. Remove empty grades
        logging.info("\n[1/5] Removing empty/invalid grades...")
        self.remove_empty_grades()

        # 2. Remove Knife Steel grades
        logging.info("\n[2/5] Removing Knife Steel grades...")
        self.remove_knife_steel_grades()

        # 3. Remove grades with question marks
        logging.info("\n[3/5] Removing grades with question marks...")
        self.remove_question_mark_grades()

        # 4. Remove duplicates
        logging.info("\n[4/5] Removing duplicate grades...")
        self.remove_duplicates_by_case()

        # 5. Find missing Standard (just report, don't delete)
        logging.info("\n[5/5] Finding grades with missing Standard...")
        missing = self.find_missing_standard()
        self.stats['missing_standard'] = len(missing)
        if missing:
            logging.info("Grades with missing Standard:")
            for grade, _ in missing[:20]:
                logging.info(f"  - {grade}")

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("CLEANUP STATISTICS")
        logging.info("="*80)
        logging.info(f"Empty grades removed:        {self.stats['empty_grades_removed']}")
        logging.info(f"Knife Steel removed:         {self.stats['knife_steel_removed']}")
        logging.info(f"Question marks removed:      {self.stats['question_marks_removed']}")
        logging.info(f"Duplicates removed:          {self.stats['duplicates_removed']}")
        logging.info(f"Missing Standard (found):    {self.stats['missing_standard']}")
        logging.info("="*80)

        # Close connection
        self.conn.close()

if __name__ == '__main__':
    cleanup = DatabaseCleanup()
    cleanup.run_cleanup()
