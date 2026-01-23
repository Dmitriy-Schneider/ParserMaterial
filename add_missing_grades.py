"""
Добавить отсутствующие марки из Excel в БД

Добавляет 772 марки, которые есть в master_grades_review_fixed.xlsx,
но отсутствуют в базе данных.
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'add_missing_grades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Импорт backup manager
try:
    from database.backup_manager import backup_before_modification
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False

DB_PATH = Path('database/steel_database.db')
EXCEL_PATH = Path('reports/analysis/master_grades_review_fixed.xlsx')
MISSING_FILE = Path('reports/analysis/grades_missing_in_db.txt')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def load_missing_grades():
    """Загрузить список отсутствующих марок"""
    if not MISSING_FILE.exists():
        logger.error(f"File not found: {MISSING_FILE}")
        return set()

    with open(MISSING_FILE, 'r', encoding='utf-8') as f:
        missing = set(line.strip() for line in f if line.strip())

    logger.info(f"Loaded {len(missing)} missing grades from file")
    return missing


def add_grades_from_excel():
    """Добавить отсутствующие марки из Excel"""
    logger.info("="*80)
    logger.info("ADDING MISSING GRADES FROM EXCEL")
    logger.info("="*80)

    # Создать бэкап
    if BACKUP_AVAILABLE:
        logger.info("Creating backup...")
        backup_before_modification(reason="add_missing_grades")

    # Загрузить Excel
    logger.info(f"Loading Excel file: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)

    # Загрузить список отсутствующих
    missing_grades = load_missing_grades()

    if not missing_grades:
        logger.warning("No missing grades to add!")
        return 0

    # Фильтровать Excel - только отсутствующие марки
    df_missing = df[df['grade_norm'].isin(missing_grades)]
    logger.info(f"Found {len(df_missing)} grades in Excel to add")

    # Подключиться к БД
    conn = get_db_connection()
    cursor = conn.cursor()

    # Колонки для вставки
    columns = ['grade', 'analogues', 'base', 'c', 'cr', 'mo', 'v', 'w', 'co',
               'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n', 'tech',
               'standard', 'manufacturer', 'link', 'other']

    added_count = 0
    errors = 0

    for idx, row in df_missing.iterrows():
        grade = row['grade_norm']

        try:
            # Подготовить значения
            values = []
            for col in columns:
                if col == 'grade':
                    values.append(grade)
                elif col == 'standard':
                    val = row.get('standard_expected')
                    values.append(val if pd.notna(val) and val != 'nan' else None)
                elif col == 'manufacturer':
                    val = row.get('manufacturer_expected')
                    values.append(val if pd.notna(val) and val != 'nan' else None)
                elif col == 'link':
                    val = row.get('link')
                    values.append(val if pd.notna(val) else None)
                elif col in row:
                    val = row[col]
                    values.append(val if pd.notna(val) and val != '' else None)
                else:
                    values.append(None)

            # Вставить в БД
            placeholders = ','.join(['?' for _ in columns])
            sql = f"INSERT INTO steel_grades ({','.join(columns)}) VALUES ({placeholders})"

            cursor.execute(sql, values)
            added_count += 1

            if added_count <= 10:
                logger.info(f"  Added: {grade} (standard={values[columns.index('standard')]})")

        except Exception as e:
            logger.error(f"  [ERROR] Failed to add {grade}: {e}")
            errors += 1

    if added_count > 10:
        logger.info(f"  ... and {added_count - 10} more grades")

    # Коммит
    conn.commit()

    # Статистика
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Added grades: {added_count}")
    if errors:
        logger.warning(f"Errors: {errors}")

    # Проверка
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    total = cursor.fetchone()[0]
    logger.info(f"Total grades in DB now: {total}")

    conn.close()

    logger.info("\n[OK] MISSING GRADES ADDED SUCCESSFULLY!")
    logger.info("="*80)

    return added_count


if __name__ == "__main__":
    add_grades_from_excel()
