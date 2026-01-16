import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Check if Standard column exists
cursor.execute("PRAGMA table_info(steel_grades)")
columns = cursor.fetchall()
print("Current columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Check some sample Standard values
cursor.execute("SELECT grade, standard FROM steel_grades WHERE standard IS NOT NULL LIMIT 20")
rows = cursor.fetchall()
print("\nSample Standard values:")
for grade, standard in rows:
    print(f"  {grade}: {standard}")

# Check how many have Standard populated
cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE standard IS NOT NULL AND standard != ''")
with_standard = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]

print(f"\nTotal grades: {total}")
print(f"With Standard: {with_standard}")

conn.close()
