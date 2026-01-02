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


if __name__ == "__main__":
    create_database()

