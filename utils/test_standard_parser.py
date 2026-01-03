"""
Тестовая версия парсера для проверки на малой выборке
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection
from utils.fill_standards_with_ai import detect_standard_pattern, ask_ai_for_standard, format_standard_value


def test_parser_on_samples(limit=50, use_ai=False):
    """
    Протестировать парсер на малой выборке марок

    Args:
        limit: количество марок для тестирования
        use_ai: использовать ли AI (осторожно, тратит API quota)
    """
    conn = get_connection()
    cursor = conn.cursor()

    print("="*70)
    print(f"ТЕСТИРОВАНИЕ ПАРСЕРА STANDARD (первые {limit} марок)")
    print("="*70)

    try:
        # Получить марки без standard
        cursor.execute("""
            SELECT id, grade, link, manufacturer, standard
            FROM steel_grades
            WHERE standard IS NULL OR standard = ''
            LIMIT ?
        """, (limit,))

        test_grades = cursor.fetchall()

        print(f"\nНайдено марок для тестирования: {len(test_grades)}")
        print("-"*70)

        successful_pattern = 0
        successful_ai = 0
        failed = 0

        results = []

        for row_id, grade, link, manufacturer, current_standard in test_grades:
            # Определить по паттерну
            detection = detect_standard_pattern(grade, link, manufacturer)

            # AI (если включен)
            ai_result = None
            if detection['type'] == 'unknown' and use_ai:
                print(f"[AI] Запрос для '{grade}'...")
                ai_result = ask_ai_for_standard(grade, link, manufacturer)

            # Форматировать
            standard_value = format_standard_value(detection, ai_result)

            # Результат
            source = "паттерн" if detection['type'] != 'unknown' else ("AI" if ai_result else "failed")

            if standard_value:
                if detection['type'] != 'unknown':
                    successful_pattern += 1
                else:
                    successful_ai += 1

                status = "OK"
                print(f"[{status}] {grade:30s} -> {standard_value:40s} ({source})")
            else:
                failed += 1
                status = "SKIP"
                print(f"[{status}] {grade:30s} -> (not determined)")

            results.append({
                'grade': grade,
                'standard': standard_value,
                'source': source,
                'detection': detection,
                'ai_result': ai_result
            })

        print("\n" + "="*70)
        print("СТАТИСТИКА ТЕСТА:")
        print("="*70)
        print(f"Всего протестировано:       {len(test_grades)}")
        print(f"Определено по паттернам:    {successful_pattern}")
        print(f"Определено через AI:        {successful_ai}")
        print(f"Не удалось определить:      {failed}")
        print(f"Успех:                      {(successful_pattern + successful_ai)*100//len(test_grades)}%")
        print("="*70)

        # Показать детализацию по типам
        gov_count = sum(1 for r in results if r['detection']['type'] == 'government')
        prop_count = sum(1 for r in results if r['detection']['type'] == 'proprietary')
        unknown_count = sum(1 for r in results if r['detection']['type'] == 'unknown')

        print(f"\nДетализация по типам:")
        print(f"  Государственные стандарты:  {gov_count}")
        print(f"  Фирменные марки:            {prop_count}")
        print(f"  Неопределенные:             {unknown_count}")

        # Примеры определенных стандартов
        print(f"\nПримеры определенных стандартов:")
        for r in results[:10]:
            if r['standard']:
                print(f"  {r['grade']:25s} -> {r['standard']}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test standard parser on small sample')
    parser.add_argument('--limit', type=int, default=50, help='Number of grades to test')
    parser.add_argument('--use-ai', action='store_true', help='Use AI for unknown grades (costs API quota)')

    args = parser.parse_args()

    test_parser_on_samples(limit=args.limit, use_ai=args.use_ai)
