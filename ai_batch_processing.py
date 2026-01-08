"""
Пакетная AI-обработка марок стали для заполнения столбца Standard
Автоматический режим с сохранением прогресса
"""
import sqlite3
import sys
import os
import csv
from pathlib import Path
from dotenv import load_dotenv

# Добавить путь к utils
sys.path.append(str(Path(__file__).parent))
from database_schema import get_connection

# Загрузить переменные окружения
load_dotenv()

# Импортировать функции из fill_standards_with_ai
from utils.fill_standards_with_ai import (
    detect_standard_pattern,
    ask_ai_for_standard,
    format_standard_value
)

try:
    from fix_ru_zknives_mismatches import latin_to_cyrillic_grade
except Exception:
    latin_to_cyrillic_grade = None

INVALID_STANDARD_LOWER = ['%n/a%', '%unknown%', '%none%', '%null%', '%zknives%', '%z knives%']
INVALID_STANDARD_LIKE = [
    '%Н/А%',
    '%н/а%',
    '%Неподтверждено%',
    '%неподтверждено%',
    '%Нет данных%',
    '%нет данных%',
    '%Не указано%',
    '%не указано%',
    '%Неизвестно%',
    '%неизвестно%'
]

ZKNIVES_MISMATCHES_PATH = Path("reports") / "zknives_mismatches.csv"


def _is_cyrillic(text):
    return any(0x0400 <= ord(ch) <= 0x04FF for ch in text)


def load_zknives_skip_grades(path):
    if not path.exists():
        print(f"[WARN] Не найден файл исключений: {path}")
        return set()

    skip = set()
    with path.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            grade = (row.get("grade") or "").strip()
            if grade:
                skip.add(grade)
    return skip

def process_batch(batch_size=100, use_ai=True, auto_commit=True):
    """
    Обработать марки пакетами с автоматическим сохранением

    Args:
        batch_size: размер пакета для обработки
        use_ai: использовать AI для неопределенных марок
        auto_commit: автоматически сохранять результаты
    """
    conn = get_connection()
    cursor = conn.cursor()

    print("="*80)
    print("ПАКЕТНАЯ AI-ОБРАБОТКА МАРОК СТАЛИ")
    print("="*80)

    # Проверить API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key and use_ai:
        print("\n[ERROR] OPENAI_API_KEY не найден в .env файле!")
        print("Установите AI в False или добавьте ключ в .env")
        conn.close()
        return False

    try:
        # Очистить некорректные значения standard (N/A, unknown, None, Н/А, Неподтверждено, etc.)
        where_parts = []
        params = []
        if INVALID_STANDARD_LOWER:
            where_parts.extend(["LOWER(standard) LIKE ?"] * len(INVALID_STANDARD_LOWER))
            params.extend(INVALID_STANDARD_LOWER)
        if INVALID_STANDARD_LIKE:
            where_parts.extend(["standard LIKE ?"] * len(INVALID_STANDARD_LIKE))
            params.extend(INVALID_STANDARD_LIKE)

        if where_parts:
            before_changes = conn.total_changes
            cursor.execute(
                f"UPDATE steel_grades SET standard = NULL WHERE {' OR '.join(where_parts)}",
                params
            )
            cleared = conn.total_changes - before_changes
            if cleared:
                print(f"[INFO] Очищено некорректных standard: {cleared}")
                if auto_commit:
                    conn.commit()

        # Очистить значения standard, которые совпадают с grade и не содержат страны
        before_changes = conn.total_changes
        cursor.execute("""
            UPDATE steel_grades
            SET standard = NULL
            WHERE standard IS NOT NULL
              AND TRIM(standard) <> ''
              AND instr(standard, ',') = 0
              AND TRIM(standard) = TRIM(grade)
        """)
        cleared_equal = conn.total_changes - before_changes
        if cleared_equal:
            print(f"[INFO] Очищено standard, совпадающих с grade: {cleared_equal}")
            if auto_commit:
                conn.commit()

        # Получить марки без standard
        cursor.execute("""
            SELECT id, grade, link, manufacturer, standard
            FROM steel_grades
            WHERE standard IS NULL OR TRIM(standard) = ''
            ORDER BY id
        """)

        all_grades = cursor.fetchall()
        skip_grades = load_zknives_skip_grades(ZKNIVES_MISMATCHES_PATH)
        skipped = 0
        if skip_grades:
            has_cyrillic = any(_is_cyrillic(grade) for grade in skip_grades)
            filtered = []
            for row in all_grades:
                grade = row[1]
                if grade in skip_grades:
                    skipped += 1
                    continue
                if has_cyrillic and latin_to_cyrillic_grade:
                    has_latin = any('A' <= ch <= 'Z' or 'a' <= ch <= 'z' for ch in grade)
                    if has_latin and latin_to_cyrillic_grade(grade) in skip_grades:
                        skipped += 1
                        continue
                filtered.append(row)
            all_grades = filtered

        total_to_process = len(all_grades)

        print(f"\nВсего марок без standard: {total_to_process}")
        if skipped:
            print(f"[INFO] Исключено по zknives_mismatches: {skipped}")

        if total_to_process == 0:
            print("\n[INFO] Все марки уже обработаны!")
            conn.close()
            return True

        # Оценка стоимости
        if use_ai:
            estimated_cost = total_to_process * 0.005  # ~$0.005 за запрос GPT-4o-mini
            print(f"\nОценочная стоимость AI обработки: ${estimated_cost:.2f}")
            print(f"Время обработки: ~{total_to_process // 30} минут")
            print(f"Модель: GPT-4o-mini (быстрая и дешевая)")

        print(f"\nРежим: {'AI включен' if use_ai else 'Только паттерны'}")
        print(f"Автосохранение: {'Да' if auto_commit else 'Нет'}")
        print(f"Размер пакета: {batch_size}")
        print("-"*80)

        # Статистика
        updated_by_pattern = 0
        updated_by_ai = 0
        failed = 0
        processed = 0

        # Обработка пакетами
        for i in range(0, len(all_grades), batch_size):
            batch = all_grades[i:i+batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, len(all_grades))

            print(f"\n[ПАКЕТ {batch_start}-{batch_end}/{len(all_grades)}]")

            for row_id, grade, link, manufacturer, current_standard in batch:
                processed += 1

                # Определить по паттерну
                detection = detect_standard_pattern(grade, link, manufacturer)

                # Если не определено и AI включен
                ai_result = None
                if detection['type'] == 'unknown' and use_ai:
                    ai_result = ask_ai_for_standard(grade, link, manufacturer)

                # Форматировать значение
                standard_value = format_standard_value(
                    detection,
                    ai_result,
                    grade=grade,
                    link=link,
                    manufacturer=manufacturer
                )

                if standard_value:
                    # Обновить БД
                    cursor.execute(
                        "UPDATE steel_grades SET standard = ? WHERE id = ?",
                        (standard_value, row_id)
                    )

                    source = "паттерн" if detection['type'] != 'unknown' else "AI"

                    if detection['type'] != 'unknown':
                        updated_by_pattern += 1
                    else:
                        updated_by_ai += 1

                    # Вывод только для AI или каждых 10 марок
                    if source == "AI" or processed % 10 == 0:
                        # Безопасный вывод
                        try:
                            print(f"  [{processed}/{total_to_process}] {grade[:30]:30s} -> {standard_value[:40]} ({source})")
                        except:
                            print(f"  [{processed}/{total_to_process}] [марка] -> [standard] ({source})")
                else:
                    failed += 1
                    if failed <= 5 or failed % 100 == 0:
                        print(f"  [SKIP] {grade[:30]}: не удалось определить")

            # Сохранить пакет
            if auto_commit:
                conn.commit()
                print(f"  [COMMIT] Пакет {batch_start}-{batch_end} сохранен в БД")

        # Финальная статистика
        print("\n" + "="*80)
        print("ИТОГИ ОБРАБОТКИ:")
        print("="*80)
        print(f"Обработано марок:           {processed}")
        print(f"Обновлено по паттернам:     {updated_by_pattern}")
        print(f"Обновлено через AI:         {updated_by_ai}")
        print(f"Не удалось определить:      {failed}")
        print(f"Всего обновлено:            {updated_by_pattern + updated_by_ai}")
        print("="*80)

        # Общая статистика
        cursor.execute("""
            SELECT COUNT(*) FROM steel_grades
            WHERE standard IS NOT NULL AND standard != ''
        """)
        filled = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM steel_grades")
        total = cursor.fetchone()[0]

        print(f"\nОБЩАЯ СТАТИСТИКА БД:")
        print(f"Всего марок:                {total}")
        print(f"С заполненным standard:     {filled} ({filled*100//total}%)")
        print(f"Без standard:               {total - filled}")
        print("="*80)

        if not auto_commit:
            response = input("\n\nСохранить изменения в БД? (yes/no): ")
            if response.lower() == 'yes':
                conn.commit()
                print("[OK] Изменения сохранены")
            else:
                conn.rollback()
                print("[ROLLBACK] Изменения отменены")
        else:
            print("\n[AUTO-COMMIT] Все изменения автоматически сохранены")

        return True

    except KeyboardInterrupt:
        print("\n\n[ПРЕРВАНО] Обработка остановлена пользователем")
        if auto_commit:
            print("[INFO] Все обработанные пакеты уже сохранены")
        else:
            conn.rollback()
            print("[ROLLBACK] Несохраненные изменения отменены")
        return False

    except Exception as e:
        print(f"\n[ERROR] Ошибка при обработке: {e}")
        if auto_commit:
            print("[INFO] Частично обработанные данные сохранены")
        else:
            conn.rollback()
            print("[ROLLBACK] Изменения отменены")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Пакетная AI-обработка марок стали')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета (по умолчанию: 100)')
    parser.add_argument('--no-ai', action='store_true', help='Отключить AI, использовать только паттерны')
    parser.add_argument('--no-auto-commit', action='store_true', help='Отключить автосохранение')

    args = parser.parse_args()

    success = process_batch(
        batch_size=args.batch_size,
        use_ai=not args.no_ai,
        auto_commit=not args.no_auto_commit
    )

    if success:
        print("\n[SUCCESS] Обработка завершена успешно!")
        sys.exit(0)
    else:
        print("\n[FAILED] Обработка завершена с ошибками")
        sys.exit(1)
