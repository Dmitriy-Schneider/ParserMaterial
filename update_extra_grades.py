"""
Обновить "лишние" марки в БД из Excel

910 марок в БД имеют спецсимволы (®, пробелы), которые отсутствуют в Excel.
Этот скрипт находит соответствующие марки в Excel и обновляет их данные.
"""

import sqlite3
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'update_extra_grades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

try:
    from database.backup_manager import backup_before_modification
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False

DB_PATH = Path('database/steel_database.db')
EXCEL_PATH = Path('reports/analysis/master_grades_review_fixed.xlsx')
EXTRA_FILE = Path('reports/analysis/grades_extra_in_db.txt')


def normalize_grade_name(name):
    """Нормализовать название марки - убрать спецсимволы"""
    if not name:
        return name
    # Убрать ®, ™, пробелы, дефисы, точки
    normalized = name.replace('®', '').replace('™', '').replace('�', '')
    normalized = normalized.replace(' ', '').replace('-', '').replace('.', '')
    return normalized.upper()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def load_extra_grades():
    """Загрузить список лишних марок"""
    if not EXTRA_FILE.exists():
        logger.error(f"File not found: {EXTRA_FILE}")
        return []

    with open(EXTRA_FILE, 'r', encoding='utf-8') as f:
        extra = [line.strip() for line in f if line.strip()]

    logger.info(f"Loaded {len(extra)} extra grades from file")
    return extra


def update_extra_grades():
    """Обновить лишние марки из Excel"""
    logger.info("="*80)
    logger.info("UPDATING EXTRA GRADES FROM EXCEL")
    logger.info("="*80)

    # Создать бэкап
    if BACKUP_AVAILABLE:
        logger.info("Creating backup...")
        backup_before_modification(reason="update_extra_grades")

    # Загрузить Excel
    logger.info(f"Loading Excel file: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)

    # Создать индекс для быстрого поиска: normalized -> row
    excel_index = {}
    for idx, row in df.iterrows():
        grade = row['grade_norm']
        if pd.notna(grade):
            normalized = normalize_grade_name(grade)
            excel_index[normalized] = row

    logger.info(f"Built index for {len(excel_index)} Excel grades")

    # Загрузить список лишних
    extra_grades = load_extra_grades()

    # Подключиться к БД
    conn = get_db_connection()
    cursor = conn.cursor()

    updated_count = 0
    not_found = 0
    errors = 0

    for db_grade in extra_grades:
        try:
            # Нормализовать название из БД
            normalized = normalize_grade_name(db_grade)

            # Найти в Excel
            if normalized not in excel_index:
                not_found += 1
                if not_found <= 5:
                    logger.warning(f"  Not found in Excel: {db_grade} (normalized: {normalized})")
                continue

            excel_row = excel_index[normalized]

            # Подготовить обновление
            updates = []
            params = []

            # Standard
            if pd.notna(excel_row.get('standard_expected')) and excel_row['standard_expected'] != 'nan':
                updates.append("standard=?")
                params.append(excel_row['standard_expected'])

            # Manufacturer
            if pd.notna(excel_row.get('manufacturer_expected')) and excel_row['manufacturer_expected'] != 'nan':
                updates.append("manufacturer=?")
                params.append(excel_row['manufacturer_expected'])

            # Химические элементы
            for elem in ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']:
                if elem in excel_row and pd.notna(excel_row[elem]) and excel_row[elem] != '':
                    updates.append(f"{elem}=?")
                    params.append(excel_row[elem])

            # Other
            if 'other' in excel_row and pd.notna(excel_row['other']) and excel_row['other'] != '':
                updates.append("other=?")
                params.append(excel_row['other'])

            # Analogues
            if 'analogues' in excel_row and pd.notna(excel_row['analogues']) and excel_row['analogues'] != '':
                updates.append("analogues=?")
                params.append(excel_row['analogues'])

            if not updates:
                continue

            # Выполнить UPDATE
            sql = f"UPDATE steel_grades SET {', '.join(updates)} WHERE grade=?"
            params.append(db_grade)

            cursor.execute(sql, params)
            updated_count += 1

            if updated_count <= 10:
                logger.info(f"  Updated: {db_grade} (matched with {excel_row['grade_norm']})")

        except Exception as e:
            logger.error(f"  [ERROR] Failed to update {db_grade}: {e}")
            errors += 1

    if updated_count > 10:
        logger.info(f"  ... and {updated_count - 10} more grades")

    if not_found > 5:
        logger.warning(f"  ... and {not_found - 5} more not found")

    # Коммит
    conn.commit()

    # Статистика
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Updated grades: {updated_count}")
    logger.info(f"Not found in Excel: {not_found}")
    if errors:
        logger.warning(f"Errors: {errors}")

    conn.close()

    logger.info("\n[OK] EXTRA GRADES UPDATED SUCCESSFULLY!")
    logger.info("="*80)

    return updated_count


if __name__ == "__main__":
    update_extra_grades()
