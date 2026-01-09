"""
Utility to clear AI Search cache
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from database_schema import get_connection

def clear_ai_cache():
    """Clear AI search cache from database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='ai_searches'
        """)

        if cursor.fetchone():
            # Get count before deletion
            cursor.execute("SELECT COUNT(*) FROM ai_searches")
            count = cursor.fetchone()[0]

            if count > 0:
                print(f"Found {count} records in AI Search cache")

                # Delete all records
                cursor.execute("DELETE FROM ai_searches")
                conn.commit()

                print(f"[OK] Deleted {count} records from AI Search cache")
                print("[OK] All AI searches will now be performed fresh")
            else:
                print("[OK] AI Search cache is already empty")
        else:
            print("[INFO] Table ai_searches not found (cache was not used)")

        conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to clear cache: {e}")
        return False

    return True

if __name__ == '__main__':
    print("=== Clear AI Search Cache ===\n")
    success = clear_ai_cache()
    sys.exit(0 if success else 1)
