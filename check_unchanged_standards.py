import sqlite3

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Get unchanged records (without comma)
cursor.execute("SELECT grade, standard FROM steel_grades WHERE standard IS NOT NULL AND standard != '' AND standard NOT LIKE '%,%' LIMIT 20")
rows = cursor.fetchall()

print("Unchanged Standard values (without country):")
for grade, standard in rows:
    print(f"  {grade}: {standard}")

conn.close()
