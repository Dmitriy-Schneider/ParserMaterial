#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove Duplicate Grades Script
===============================
Finds and removes duplicate grades with different case
Priority: Keep grades with links, remove ones without links
"""

import sqlite3
import logging
from typing import List, Tuple, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('remove_duplicates.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DuplicateRemover:
    def __init__(self, db_path: str = 'database/steel_database.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.stats = {
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'analogues_updated': 0
        }

    def find_all_duplicates(self) -> List[Tuple]:
        """
        Find all duplicate grades (case-insensitive)
        Returns: [(grade1, grade2, link1, link2, id1, id2), ...]
        """
        self.cursor.execute("""
            SELECT a.grade, b.grade, a.link, b.link, a.id, b.id
            FROM steel_grades a
            JOIN steel_grades b ON LOWER(a.grade) = LOWER(b.grade)
            WHERE a.id < b.id
            ORDER BY LOWER(a.grade)
        """)
        results = self.cursor.fetchall()
        logging.info(f"Found {len(results)} potential duplicate pairs")
        return results

    def remove_duplicate_from_analogues(self, duplicate_grade: str):
        """Remove duplicate grade from all analogues"""
        # Update analogues by removing the duplicate grade
        self.cursor.execute("""
            UPDATE steel_grades
            SET analogues = TRIM(REPLACE(' ' || analogues || ' ', ' ' || ? || ' ', ' '))
            WHERE analogues LIKE ?
        """, (duplicate_grade, f'%{duplicate_grade}%'))

        if self.cursor.rowcount > 0:
            logging.info(f"Removed '{duplicate_grade}' from {self.cursor.rowcount} analogue lists")
            self.stats['analogues_updated'] += self.cursor.rowcount

    def remove_duplicates(self):
        """Remove duplicate grades, keeping ones with links"""
        duplicates = self.find_all_duplicates()
        removed_ids = set()

        for grade1, grade2, link1, link2, id1, id2 in duplicates:
            # Skip if already removed
            if id1 in removed_ids or id2 in removed_ids:
                continue

            self.stats['duplicates_found'] += 1

            # Determine which one to remove
            to_remove = None
            to_keep = None

            if link1 and not link2:
                # Keep grade1 (has link), remove grade2
                to_remove = (id2, grade2)
                to_keep = (id1, grade1)
            elif link2 and not link1:
                # Keep grade2 (has link), remove grade1
                to_remove = (id1, grade1)
                to_keep = (id2, grade2)
            elif not link1 and not link2:
                # Neither has link - keep first alphabetically (case-insensitive)
                if grade1.lower() < grade2.lower():
                    to_remove = (id2, grade2)
                    to_keep = (id1, grade1)
                else:
                    to_remove = (id1, grade1)
                    to_keep = (id2, grade2)
            else:
                # Both have links - keep first alphabetically
                if grade1.lower() < grade2.lower():
                    to_remove = (id2, grade2)
                    to_keep = (id1, grade1)
                else:
                    to_remove = (id1, grade1)
                    to_keep = (id2, grade2)

            if to_remove:
                remove_id, remove_grade = to_remove
                keep_id, keep_grade = to_keep

                logging.info(f"Removing duplicate: '{remove_grade}' (keeping '{keep_grade}')")

                # Remove from analogues first
                self.remove_duplicate_from_analogues(remove_grade)

                # Delete the duplicate
                self.cursor.execute("DELETE FROM steel_grades WHERE id = ?", (remove_id,))
                removed_ids.add(remove_id)
                self.stats['duplicates_removed'] += 1

    def run(self):
        """Run duplicate removal"""
        logging.info("\n" + "="*80)
        logging.info("DUPLICATE REMOVER - STARTING")
        logging.info("="*80)

        self.remove_duplicates()

        # Commit changes
        self.conn.commit()

        # Print statistics
        logging.info("\n" + "="*80)
        logging.info("REMOVAL STATISTICS")
        logging.info("="*80)
        logging.info(f"Duplicate pairs found:    {self.stats['duplicates_found']}")
        logging.info(f"Duplicates removed:       {self.stats['duplicates_removed']}")
        logging.info(f"Analogue lists updated:   {self.stats['analogues_updated']}")
        logging.info("="*80)

        # Show some examples of what's left
        logging.info("\nExamples of remaining grades:")
        self.cursor.execute("""
            SELECT grade, link FROM steel_grades
            WHERE grade LIKE '%Microclean%' OR grade LIKE '%MICROCLEAN%'
            ORDER BY LOWER(grade)
            LIMIT 10
        """)
        for grade, link in self.cursor.fetchall():
            link_status = "WITH LINK" if link else "NO LINK"
            logging.info(f"  {grade:<30} {link_status}")

        self.conn.close()

if __name__ == '__main__':
    remover = DuplicateRemover()
    remover.run()
