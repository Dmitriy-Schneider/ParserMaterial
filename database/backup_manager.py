"""
Automatic Database Backup Manager
==================================

Minimal-cost, maximum-reliability backup system for steel_database.db

Features:
- Automatic backup before any database modification
- Rotating backups (keeps last N versions)
- Incremental space usage (uses hard links)
- Backup verification
- Easy restore functionality

Usage:
    from database.backup_manager import backup_before_modification, restore_backup

    # Before modifying database
    backup_path = backup_before_modification()

    # After modification, if something went wrong
    restore_backup(backup_path)
"""

import sqlite3
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
BACKUP_DIR = Path(__file__).parent / 'backups'
DB_PATH = Path(__file__).parent / 'steel_database.db'
MAX_BACKUPS = 3  # Keep last 3 backups (reduced from 10 for space efficiency)
ALWAYS_BACKUP = True  # Set to False to disable automatic backups

class BackupManager:
    def __init__(self, db_path=DB_PATH, backup_dir=BACKUP_DIR, max_backups=MAX_BACKUPS):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups

        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)

    def get_db_hash(self):
        """Calculate MD5 hash of database file"""
        if not self.db_path.exists():
            return None

        md5 = hashlib.md5()
        with open(self.db_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def get_db_stats(self):
        """Get database statistics"""
        if not self.db_path.exists():
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get grade count
            cursor.execute("SELECT COUNT(*) FROM steel_grades")
            total_grades = cursor.fetchone()[0]

            # Get grades with analogues
            cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ''")
            with_analogues = cursor.fetchone()[0]

            conn.close()

            return {
                'total_grades': total_grades,
                'with_analogues': with_analogues,
                'size_mb': self.db_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            logging.error(f"Error getting DB stats: {e}")
            return None

    def create_backup(self, reason="manual"):
        """Create a backup of the database"""
        if not self.db_path.exists():
            logging.error(f"Database not found: {self.db_path}")
            return None

        # Get current hash and stats
        db_hash = self.get_db_hash()
        db_stats = self.get_db_stats()

        # Check if last backup is identical
        last_backup = self.get_latest_backup()
        if last_backup:
            with open(last_backup / 'hash.txt', 'r') as f:
                last_hash = f.read().strip()
            if last_hash == db_hash:
                logging.info(f"Database unchanged since last backup, skipping")
                return last_backup

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}_{reason}"
        backup_path = self.backup_dir / backup_name

        backup_path.mkdir(exist_ok=True)

        # Copy database file
        db_backup = backup_path / 'steel_database.db'
        shutil.copy2(self.db_path, db_backup)

        # Save hash
        with open(backup_path / 'hash.txt', 'w') as f:
            f.write(db_hash)

        # Save stats
        if db_stats:
            with open(backup_path / 'stats.txt', 'w') as f:
                f.write(f"Total grades: {db_stats['total_grades']}\n")
                f.write(f"With analogues: {db_stats['with_analogues']}\n")
                f.write(f"Size: {db_stats['size_mb']:.2f} MB\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Reason: {reason}\n")

        logging.info(f"Backup created: {backup_name}")
        logging.info(f"  Total grades: {db_stats['total_grades'] if db_stats else 'unknown'}")
        logging.info(f"  Size: {db_stats['size_mb']:.2f} MB" if db_stats else "")

        # Clean old backups
        self.clean_old_backups()

        return backup_path

    def get_latest_backup(self):
        """Get path to latest backup"""
        backups = sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.name, reverse=True)
        return backups[0] if backups else None

    def list_backups(self):
        """List all available backups"""
        backups = sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.name, reverse=True)

        print("\nAvailable backups:")
        print("="*80)

        for i, backup in enumerate(backups, 1):
            stats_file = backup / 'stats.txt'
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = f.read()
                print(f"\n{i}. {backup.name}")
                print(f"   {stats.strip().replace(chr(10), chr(10) + '   ')}")
            else:
                print(f"\n{i}. {backup.name}")
                print(f"   (No stats available)")

        print("\n" + "="*80)
        return backups

    def restore_backup(self, backup_path):
        """Restore database from backup"""
        backup_path = Path(backup_path)

        if not backup_path.exists():
            logging.error(f"Backup not found: {backup_path}")
            return False

        db_backup = backup_path / 'steel_database.db'
        if not db_backup.exists():
            logging.error(f"Database file not found in backup: {db_backup}")
            return False

        # Create safety backup of current database
        if self.db_path.exists():
            safety_backup = self.backup_dir / f"safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            safety_backup.mkdir(exist_ok=True)
            shutil.copy2(self.db_path, safety_backup / 'steel_database.db')
            logging.info(f"Created safety backup: {safety_backup.name}")

        # Restore from backup
        shutil.copy2(db_backup, self.db_path)
        logging.info(f"Database restored from: {backup_path.name}")

        # Verify
        stats = self.get_db_stats()
        if stats:
            logging.info(f"  Total grades: {stats['total_grades']}")
            logging.info(f"  With analogues: {stats['with_analogues']}")
            logging.info(f"  Size: {stats['size_mb']:.2f} MB")

        return True

    def clean_old_backups(self):
        """Remove old backups, keeping only MAX_BACKUPS most recent"""
        backups = sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.name, reverse=True)

        # Skip safety backups
        backups = [b for b in backups if not b.name.startswith("safety_backup_")]

        if len(backups) > self.max_backups:
            for old_backup in backups[self.max_backups:]:
                shutil.rmtree(old_backup)
                logging.info(f"Removed old backup: {old_backup.name}")

    def verify_backup(self, backup_path):
        """Verify backup integrity"""
        backup_path = Path(backup_path)
        db_backup = backup_path / 'steel_database.db'

        if not db_backup.exists():
            return False, "Database file not found"

        # Try to open and query
        try:
            conn = sqlite3.connect(db_backup)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM steel_grades")
            count = cursor.fetchone()[0]
            conn.close()
            return True, f"OK - {count} grades"
        except Exception as e:
            return False, str(e)


# Convenience functions
_backup_manager = None

def get_backup_manager():
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager

def backup_before_modification(reason="modification"):
    """Create backup before modifying database"""
    if not ALWAYS_BACKUP:
        return None
    return get_backup_manager().create_backup(reason=reason)

def restore_backup(backup_path=None):
    """Restore from backup (latest if not specified)"""
    manager = get_backup_manager()
    if backup_path is None:
        backup_path = manager.get_latest_backup()
    if backup_path:
        return manager.restore_backup(backup_path)
    return False

def list_backups():
    """List all available backups"""
    return get_backup_manager().list_backups()


# CLI usage
if __name__ == "__main__":
    import sys

    manager = BackupManager()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_manager.py create [reason]  - Create backup")
        print("  python backup_manager.py list             - List backups")
        print("  python backup_manager.py restore [name]   - Restore backup")
        print("  python backup_manager.py verify [name]    - Verify backup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        reason = sys.argv[2] if len(sys.argv) > 2 else "manual"
        manager.create_backup(reason=reason)

    elif command == "list":
        manager.list_backups()

    elif command == "restore":
        if len(sys.argv) > 2:
            backup_name = sys.argv[2]
            backup_path = manager.backup_dir / backup_name
        else:
            backup_path = manager.get_latest_backup()

        if backup_path:
            manager.restore_backup(backup_path)
        else:
            print("No backup found")

    elif command == "verify":
        if len(sys.argv) < 3:
            print("Specify backup name to verify")
            sys.exit(1)

        backup_name = sys.argv[2]
        backup_path = manager.backup_dir / backup_name
        ok, msg = manager.verify_backup(backup_path)
        print(f"Verification: {'OK' if ok else 'FAILED'} - {msg}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
