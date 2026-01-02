"""Quick migration to add tech column"""
import sqlite3
import config

conn = sqlite3.connect(config.DB_FILE)
cursor = conn.cursor()

try:
    # Get current columns
    cursor.execute("PRAGMA table_info(steel_grades)")
    columns = [col[1] for col in cursor.fetchall()]
    print("Current columns:", columns)

    # Add tech if missing (should already exist in new schema)
    if 'tech' not in columns:
        print("Adding tech column...")
        cursor.execute("ALTER TABLE steel_grades ADD COLUMN tech TEXT")
        conn.commit()
        print("Tech column added!")
    else:
        print("Tech column already exists")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
