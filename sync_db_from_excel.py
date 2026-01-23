"""
Синхронизация базы данных с master_grades_review_fixed.xlsx

Этот скрипт обновляет базу данных на основе исправленных данных из Excel файла:
1. Обновляет standard из standard_expected
2. Обновляет manufacturer из manufacturer_expected
3. Переносит значения Other (дополнительные элементы)
4. Обновляет все химические элементы (C, Cr, Mo, V, W, Co, Ni, Mn, Si, S, P, Cu, Nb, N)
5. Обновляет analogues
6. Находит отсутствующие и лишние марки

ВНИМАНИЕ: Создает бэкап перед изменениями!
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import logging
from datetime import datetime

# Настройка логирования с UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'sync_db_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Пути
DB_PATH = Path('database/steel_database.db')
EXCEL_PATH = Path('reports/analysis/master_grades_review_fixed.xlsx')

# Импорт backup manager
try:
    from database.backup_manager import backup_before_modification
    BACKUP_AVAILABLE = True
except ImportError:
    logger.warning("Backup manager не найден, бэкапы создаваться не будут!")
    BACKUP_AVAILABLE = False


def create_backup():
    """Создать бэкап БД перед изменениями"""
    if BACKUP_AVAILABLE:
        logger.info("Создание бэкапа базы данных...")
        backup_path = backup_before_modification(reason="excel_sync")
        if backup_path:
            logger.info(f"[OK] Backup created: {backup_path}")
            return True
        else:
            logger.warning("Backup not created (DB unchanged since last backup)")
            return True
    else:
        logger.warning("[WARNING] BACKUP MANAGER NOT AVAILABLE! Continue without backup? (y/n)")
        response = input().strip().lower()
        return response == 'y'


def load_excel_data():
    """Загрузить данные из Excel файла"""
    logger.info(f"Загрузка данных из {EXCEL_PATH}...")

    if not EXCEL_PATH.exists():
        logger.error(f"Excel файл не найден: {EXCEL_PATH}")
        return None

    df = pd.read_excel(EXCEL_PATH)
    logger.info(f"[OK] Loaded {len(df)} grades from Excel")
    logger.info(f"  Columns: {len(df.columns)}")

    return df


def get_db_connection():
    """Получить подключение к БД"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def compare_databases(df):
    """Сравнить Excel с БД"""
    logger.info("\n" + "="*80)
    logger.info("СРАВНЕНИЕ EXCEL И БАЗЫ ДАННЫХ")
    logger.info("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Получить все марки из БД
    cursor.execute("SELECT grade FROM steel_grades")
    db_grades = set(row[0] for row in cursor.fetchall())

    # Получить все марки из Excel
    excel_grades = set(df['grade_norm'].dropna())

    logger.info(f"\nБаза данных: {len(db_grades)} марок")
    logger.info(f"Excel файл:  {len(excel_grades)} марок")

    # Найти отсутствующие в БД
    missing_in_db = excel_grades - db_grades
    logger.info(f"\n[MISSING] Missing in DB: {len(missing_in_db)} grades")
    if missing_in_db:
        logger.info("  Примеры:")
        for grade in list(missing_in_db)[:10]:
            logger.info(f"    - {grade}")
        if len(missing_in_db) > 10:
            logger.info(f"    ... и еще {len(missing_in_db)-10} марок")

    # Найти лишние в БД
    extra_in_db = db_grades - excel_grades
    logger.info(f"\n[EXTRA] Extra in DB (not in Excel): {len(extra_in_db)} grades")
    if extra_in_db:
        logger.info("  Примеры:")
        for grade in list(extra_in_db)[:10]:
            logger.info(f"    - {grade}")
        if len(extra_in_db) > 10:
            logger.info(f"    ... и еще {len(extra_in_db)-10} марок")

    # Сохранить в файлы для ручного просмотра
    if missing_in_db:
        with open('reports/analysis/grades_missing_in_db.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(missing_in_db)))
        logger.info(f"\n[OK] Missing grades list saved: reports/analysis/grades_missing_in_db.txt")

    if extra_in_db:
        with open('reports/analysis/grades_extra_in_db.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(extra_in_db)))
        logger.info(f"[OK] Extra grades list saved: reports/analysis/grades_extra_in_db.txt")

    conn.close()

    return {
        'db_grades': db_grades,
        'excel_grades': excel_grades,
        'missing_in_db': missing_in_db,
        'extra_in_db': extra_in_db
    }


def update_standards(df, dry_run=False):
    """Обновить колонку standard из standard_expected"""
    logger.info("\n" + "="*80)
    logger.info("ОБНОВЛЕНИЕ КОЛОНКИ STANDARD")
    logger.info("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Найти марки с разными standard
    updated_count = 0
    errors = 0

    for idx, row in df.iterrows():
        grade = row['grade_norm']
        standard_expected = row['standard_expected']

        # Пропускаем пустые значения
        if pd.isna(standard_expected) or standard_expected == '' or standard_expected == 'nan':
            continue

        # Получить текущий standard из БД
        cursor.execute("SELECT standard FROM steel_grades WHERE grade=?", (grade,))
        result = cursor.fetchone()

        if not result:
            # Марки нет в БД
            continue

        current_standard = result[0]

        # Если standard изменился
        if current_standard != standard_expected:
            if not dry_run:
                try:
                    cursor.execute(
                        "UPDATE steel_grades SET standard=? WHERE grade=?",
                        (standard_expected, grade)
                    )
                    updated_count += 1

                    if updated_count <= 5:  # Показать первые 5 обновлений
                        logger.info(f"  {grade}: '{current_standard}' -> '{standard_expected}'")
                except Exception as e:
                    logger.error(f"  [ERROR] Ошибка обновления {grade}: {e}")
                    errors += 1
            else:
                updated_count += 1
                if updated_count <= 5:
                    logger.info(f"  [DRY RUN] {grade}: '{current_standard}' -> '{standard_expected}'")

    if updated_count > 5:
        logger.info(f"  ... и еще {updated_count-5} обновлений")

    if not dry_run:
        conn.commit()
        logger.info(f"\n[OK] Updated standard: {updated_count} grades")
        if errors:
            logger.warning(f"[WARNING] Errors: {errors}")
    else:
        logger.info(f"\n[DRY RUN] Будет обновлено: {updated_count} марок")

    conn.close()
    return updated_count


def update_manufacturers(df, dry_run=False):
    """Обновить колонку manufacturer из manufacturer_expected"""
    logger.info("\n" + "="*80)
    logger.info("ОБНОВЛЕНИЕ КОЛОНКИ MANUFACTURER")
    logger.info("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    updated_count = 0
    errors = 0

    for idx, row in df.iterrows():
        grade = row['grade_norm']
        manufacturer_expected = row['manufacturer_expected']

        # Пропускаем пустые значения
        if pd.isna(manufacturer_expected) or manufacturer_expected == '' or manufacturer_expected == 'nan':
            continue

        # Получить текущий manufacturer из БД
        cursor.execute("SELECT manufacturer FROM steel_grades WHERE grade=?", (grade,))
        result = cursor.fetchone()

        if not result:
            continue

        current_manufacturer = result[0]

        # Если manufacturer изменился
        if current_manufacturer != manufacturer_expected:
            if not dry_run:
                try:
                    cursor.execute(
                        "UPDATE steel_grades SET manufacturer=? WHERE grade=?",
                        (manufacturer_expected, grade)
                    )
                    updated_count += 1

                    if updated_count <= 5:
                        logger.info(f"  {grade}: '{current_manufacturer}' -> '{manufacturer_expected}'")
                except Exception as e:
                    logger.error(f"  [ERROR] Ошибка обновления {grade}: {e}")
                    errors += 1
            else:
                updated_count += 1
                if updated_count <= 5:
                    logger.info(f"  [DRY RUN] {grade}: '{current_manufacturer}' -> '{manufacturer_expected}'")

    if updated_count > 5:
        logger.info(f"  ... и еще {updated_count-5} обновлений")

    if not dry_run:
        conn.commit()
        logger.info(f"\n[OK] Updated manufacturer: {updated_count} grades")
        if errors:
            logger.warning(f"[WARNING] Errors: {errors}")
    else:
        logger.info(f"\n[DRY RUN] Будет обновлено: {updated_count} марок")

    conn.close()
    return updated_count


def update_chemistry(df, dry_run=False):
    """Обновить химические элементы (C, Cr, Mo, V, W, Co, Ni, Mn, Si, S, P, Cu, Nb, N)"""
    logger.info("\n" + "="*80)
    logger.info("ОБНОВЛЕНИЕ ХИМИЧЕСКИХ ЭЛЕМЕНТОВ")
    logger.info("="*80)

    elements = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']

    conn = get_db_connection()
    cursor = conn.cursor()

    total_updated = 0
    errors = 0

    for element in elements:
        element_updated = 0

        for idx, row in df.iterrows():
            grade = row['grade_norm']
            excel_value = row.get(element)

            # Пропускаем пустые значения
            if pd.isna(excel_value) or excel_value == '':
                continue

            # Получить текущее значение из БД
            cursor.execute(f"SELECT {element} FROM steel_grades WHERE grade=?", (grade,))
            result = cursor.fetchone()

            if not result:
                continue

            current_value = result[0]

            # Если значение изменилось
            if str(current_value) != str(excel_value):
                if not dry_run:
                    try:
                        cursor.execute(
                            f"UPDATE steel_grades SET {element}=? WHERE grade=?",
                            (excel_value, grade)
                        )
                        element_updated += 1
                        total_updated += 1
                    except Exception as e:
                        logger.error(f"  [ERROR] Ошибка обновления {element} для {grade}: {e}")
                        errors += 1
                else:
                    element_updated += 1
                    total_updated += 1

        if element_updated > 0:
            logger.info(f"  {element.upper()}: {element_updated} обновлений")

    if not dry_run:
        conn.commit()
        logger.info(f"\n[OK] Total values updated: {total_updated}")
        if errors:
            logger.warning(f"[WARNING] Errors: {errors}")
    else:
        logger.info(f"\n[DRY RUN] Будет обновлено: {total_updated} значений")

    conn.close()
    return total_updated


def add_other_column_if_needed():
    """Добавить колонку 'other' в БД если её нет"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверить существование колонки
    cursor.execute("PRAGMA table_info(steel_grades)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'other' not in columns:
        logger.info("Adding column 'other' to DB...")
        cursor.execute("ALTER TABLE steel_grades ADD COLUMN other TEXT")
        conn.commit()
        logger.info("[OK] Column 'other' added")

    conn.close()
    return 'other' in columns


def update_other_elements(df, dry_run=False):
    """Обновить колонку other (дополнительные элементы)"""
    logger.info("\n" + "="*80)
    logger.info("UPDATE COLUMN OTHER (additional elements)")
    logger.info("="*80)

    # Добавить колонку если нужно
    if not dry_run:
        column_exists = add_other_column_if_needed()
    else:
        # Проверить существование колонки в dry-run режиме
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor()
        cursor_check.execute("PRAGMA table_info(steel_grades)")
        columns = [col[1] for col in cursor_check.fetchall()]
        column_exists = 'other' in columns
        conn_check.close()

        if not column_exists:
            logger.warning("[DRY RUN] Column 'other' does not exist, will be created on actual run")
            logger.info("[DRY RUN] Skipping OTHER updates until column is created")
            return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    updated_count = 0
    errors = 0

    for idx, row in df.iterrows():
        grade = row['grade_norm']
        other_value = row.get('other')

        # Пропускаем пустые значения
        if pd.isna(other_value) or other_value == '':
            continue

        # Проверить есть ли марка в БД
        cursor.execute("SELECT other FROM steel_grades WHERE grade=?", (grade,))
        result = cursor.fetchone()

        if not result:
            continue

        current_other = result[0]

        # Если значение изменилось
        if str(current_other) != str(other_value):
            if not dry_run:
                try:
                    cursor.execute(
                        "UPDATE steel_grades SET other=? WHERE grade=?",
                        (other_value, grade)
                    )
                    updated_count += 1

                    if updated_count <= 3:
                        logger.info(f"  {grade}: {other_value[:80]}...")
                except Exception as e:
                    logger.error(f"  [ERROR] Ошибка обновления {grade}: {e}")
                    errors += 1
            else:
                updated_count += 1
                if updated_count <= 3:
                    logger.info(f"  [DRY RUN] {grade}: {other_value[:80]}...")

    if updated_count > 3:
        logger.info(f"  ... и еще {updated_count-3} обновлений")

    if not dry_run:
        conn.commit()
        logger.info(f"\n[OK] Updated other: {updated_count} grades")
        if errors:
            logger.warning(f"[WARNING] Errors: {errors}")
    else:
        logger.info(f"\n[DRY RUN] Будет обновлено: {updated_count} марок")

    conn.close()
    return updated_count


def update_analogues(df, dry_run=False):
    """Обновить analogues"""
    logger.info("\n" + "="*80)
    logger.info("ОБНОВЛЕНИЕ АНАЛОГОВ")
    logger.info("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    updated_count = 0
    errors = 0

    for idx, row in df.iterrows():
        grade = row['grade_norm']
        analogues_value = row.get('analogues')

        # Пропускаем пустые значения
        if pd.isna(analogues_value) or analogues_value == '':
            continue

        # Получить текущие аналоги из БД
        cursor.execute("SELECT analogues FROM steel_grades WHERE grade=?", (grade,))
        result = cursor.fetchone()

        if not result:
            continue

        current_analogues = result[0]

        # Если аналоги изменились
        if str(current_analogues) != str(analogues_value):
            if not dry_run:
                try:
                    cursor.execute(
                        "UPDATE steel_grades SET analogues=? WHERE grade=?",
                        (analogues_value, grade)
                    )
                    updated_count += 1

                    if updated_count <= 3:
                        logger.info(f"  {grade}: обновлены аналоги")
                except Exception as e:
                    logger.error(f"  [ERROR] Ошибка обновления {grade}: {e}")
                    errors += 1
            else:
                updated_count += 1

    if updated_count > 3:
        logger.info(f"  ... и еще {updated_count-3} обновлений")

    if not dry_run:
        conn.commit()
        logger.info(f"\n[OK] Updated analogues: {updated_count} grades")
        if errors:
            logger.warning(f"[WARNING] Errors: {errors}")
    else:
        logger.info(f"\n[DRY RUN] Будет обновлено: {updated_count} марок")

    conn.close()
    return updated_count


def main():
    """Главная функция"""
    logger.info("="*80)
    logger.info("СИНХРОНИЗАЦИЯ БД С master_grades_review_fixed.xlsx")
    logger.info("="*80)

    # Проверка аргументов
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        logger.info("\n[DRY RUN MODE] Changes will NOT be applied\n")

    # Загрузить Excel
    df = load_excel_data()
    if df is None:
        return 1

    # Сравнить БД и Excel
    comparison = compare_databases(df)

    # Создать бэкап
    if not dry_run:
        if not create_backup():
            logger.error("Отмена операции - бэкап не создан")
            return 1

    # Выполнить обновления
    logger.info("\n" + "="*80)
    logger.info("НАЧАЛО ОБНОВЛЕНИЙ")
    logger.info("="*80)

    stats = {
        'standards': update_standards(df, dry_run),
        'manufacturers': update_manufacturers(df, dry_run),
        'chemistry': update_chemistry(df, dry_run),
        'other': update_other_elements(df, dry_run),
        'analogues': update_analogues(df, dry_run)
    }

    # Итоговая статистика
    logger.info("\n" + "="*80)
    logger.info("ИТОГОВАЯ СТАТИСТИКА")
    logger.info("="*80)
    logger.info(f"\nОбновлено standards:       {stats['standards']}")
    logger.info(f"Обновлено manufacturers:   {stats['manufacturers']}")
    logger.info(f"Обновлено хим. элементов:  {stats['chemistry']}")
    logger.info(f"Обновлено other:           {stats['other']}")
    logger.info(f"Обновлено analogues:       {stats['analogues']}")
    logger.info(f"\nОтсутствует в БД:          {len(comparison['missing_in_db'])}")
    logger.info(f"Лишних в БД:               {len(comparison['extra_in_db'])}")

    if dry_run:
        logger.info("\n[DRY RUN] This was a test run. To apply changes, run without --dry-run")
    else:
        logger.info("\n[OK] SYNCHRONIZATION COMPLETED SUCCESSFULLY!")

    logger.info("="*80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
