"""Fix OCR12VMD2 - remove incorrect analogues '2' and '3'"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Fixing grade OCR12VMD2...")

# Get current analogues
cursor.execute("SELECT analogues FROM steel_grades WHERE grade = 'OCR12VMD2'")
result = cursor.fetchone()

if result:
    analogues = result[0]
    print(f"Current analogues: {analogues[:100]}...")

    # Split, remove '2' and '3', rejoin
    analogue_list = analogues.split()
    cleaned = [a for a in analogue_list if a not in ['2', '3']]

    new_analogues = ' '.join(cleaned)

    # Update database
    cursor.execute("UPDATE steel_grades SET analogues = ? WHERE grade = 'OCR12VMD2'", (new_analogues,))
    conn.commit()

    print(f"Removed '2' and '3' from analogues")
    print(f"New analogues: {new_analogues[:100]}...")
    print("OK: Fixed successfully!")
else:
    print("ERROR: Grade OCR12VMD2 not found")

conn.close()
