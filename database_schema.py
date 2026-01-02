import sqlite3
import os
import config


def create_database():
    """Create the database and tables"""
    # Ensure database folder exists
    os.makedirs(config.DB_FOLDER, exist_ok=True)
    
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    
    # Create steel grades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS steel_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grade TEXT NOT NULL,
            analogues TEXT,
            base TEXT,
            c TEXT,
            cr TEXT,
            mo TEXT,
            v TEXT,
            w TEXT,
            co TEXT,
            ni TEXT,
            mn TEXT,
            si TEXT,
            s TEXT,
            p TEXT,
            cu TEXT,
            nb TEXT,
            n TEXT,
            tech TEXT,
            standard TEXT,
            manufacturer TEXT,
            link TEXT,
            UNIQUE(grade, link)
        )
    ''')
    
    # Create index for faster searching
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_grade ON steel_grades(grade)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_analogues ON steel_grades(analogues)
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database created at {config.DB_FILE}")


def get_connection():
    """Get database connection"""
    return sqlite3.connect(config.DB_FILE)


def migrate_database():
    """Migrate existing database to add new columns"""
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()

    try:
        # Check if standard column exists
        cursor.execute("PRAGMA table_info(steel_grades)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add standard column if missing
        if 'standard' not in columns:
            print("Adding 'standard' column...")
            cursor.execute("ALTER TABLE steel_grades ADD COLUMN standard TEXT")
            conn.commit()
            print("✓ Added 'standard' column")

        # Add manufacturer column if missing
        if 'manufacturer' not in columns:
            print("Adding 'manufacturer' column...")
            cursor.execute("ALTER TABLE steel_grades ADD COLUMN manufacturer TEXT")
            conn.commit()
            print("✓ Added 'manufacturer' column")

    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

    print("Migration completed!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--migrate":
        migrate_database()
    else:
        create_database()

