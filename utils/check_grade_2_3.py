"""Check what grades 2 and 3 are"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT grade, standard, c, cr, ni FROM steel_grades WHERE grade IN ('2', '3')")
for r in cursor.fetchall():
    print(f"Grade: {r[0]}, Standard: {r[1]}, C: {r[2]}, Cr: {r[3]}, Ni: {r[4]}")

conn.close()
