#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database_schema import get_connection

def normalize_grade_name(grade):
    """Нормализует название марки: убирает звездочки и пробелы"""
    if not grade:
        return grade
    return grade.replace('*', '').strip()

def remove_asterisks_from_grades():
    """Удаляет звездочки из всех названий марок"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Удаление звездочек из названий марок...")
    print("=" * 60)
    
    # Получаем все марки со звездочками
    cursor.execute("SELECT id, grade FROM steel_grades WHERE grade LIKE '%*%'")
    grades_with_asterisks = cursor.fetchall()
    
    print(f"Найдено марок со звездочками: {len(grades_with_asterisks)}")
    
    updated_count = 0
    for grade_id, grade_name in grades_with_asterisks:
        normalized = normalize_grade_name(grade_name)
        if normalized != grade_name:
            try:
                cursor.execute("UPDATE steel_grades SET grade = ? WHERE id = ?", (normalized, grade_id))
                if cursor.rowcount > 0:
                    updated_count += 1
                    print(f"  OK: ID {grade_id}: '{grade_name}' -> '{normalized}'")
            except sqlite3.IntegrityError as e:
                print(f"  ERROR: ID {grade_id}: конфликт при обновлении '{grade_name}' -> '{normalized}': {e}")
    
    conn.commit()
    print(f"\nОбновлено марок: {updated_count}")
    print("=" * 60)
    conn.close()
    
    return updated_count

def find_and_remove_duplicates():
    """Находит и удаляет дубликаты по нормализованному названию"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\nПоиск и удаление дубликатов...")
    print("=" * 60)
    
    # Получаем все марки и нормализуем их названия
    cursor.execute("SELECT id, grade, link, analogues FROM steel_grades ORDER BY id")
    all_grades = cursor.fetchall()
    
    # Группируем по нормализованному названию
    grade_groups = {}
    for grade_id, grade_name, link, analogues in all_grades:
        normalized = normalize_grade_name(grade_name)
        if normalized not in grade_groups:
            grade_groups[normalized] = []
        grade_groups[normalized].append({
            'id': grade_id,
            'grade': grade_name,
            'link': link,
            'analogues': analogues
        })
    
    # Находим группы с дубликатами
    duplicates_found = 0
    duplicates_to_remove = []
    
    for normalized_name, grades_list in grade_groups.items():
        if len(grades_list) > 1:
            duplicates_found += len(grades_list) - 1
            print(f"\nДубликаты для '{normalized_name}' ({len(grades_list)} записей):")
            
            # Сортируем: сначала записи с ссылкой, потом по ID
            grades_list_sorted = sorted(
                grades_list,
                key=lambda x: (0 if x['link'] else 1, x['id'])
            )
            
            # Оставляем первую запись (лучшую - с ссылкой, или первую по ID)
            keep_id = grades_list_sorted[0]['id']
            
            for grade_info in grades_list_sorted:
                print(f"  ID {grade_info['id']}: '{grade_info['grade']}' (link: {'есть' if grade_info['link'] else 'нет'})")
            
            # Помечаем остальные для удаления
            for grade_info in grades_list_sorted[1:]:
                duplicates_to_remove.append(grade_info['id'])
                print(f"    -> Удалить ID {grade_info['id']}")
    
    # Удаляем дубликаты
    if duplicates_to_remove:
        print(f"\nУдаляем {len(duplicates_to_remove)} дубликатов...")
        removed_count = 0
        for grade_id in duplicates_to_remove:
            try:
                cursor.execute("DELETE FROM steel_grades WHERE id = ?", (grade_id,))
                if cursor.rowcount > 0:
                    removed_count += 1
            except sqlite3.Error as e:
                print(f"  ERROR: Не удалось удалить ID {grade_id}: {e}")
        
        conn.commit()
        print(f"Удалено дубликатов: {removed_count}")
    else:
        print("Дубликатов не найдено")
    
    print("=" * 60)
    conn.close()
    
    return len(duplicates_to_remove)

def verify_results():
    """Проверяет результаты после удаления звездочек и дубликатов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\nПроверка результатов...")
    print("=" * 60)
    
    # Общее количество марок
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    total = cursor.fetchone()[0]
    print(f"Всего марок в базе: {total}")
    
    # Количество марок со звездочками
    cursor.execute("SELECT COUNT(*) FROM steel_grades WHERE grade LIKE '%*%'")
    with_asterisks = cursor.fetchone()[0]
    print(f"Марок со звездочками: {with_asterisks}")
    
    # Количество дубликатов (по нормализованному названию)
    cursor.execute("SELECT grade FROM steel_grades")
    all_grades = cursor.fetchall()
    
    from collections import Counter
    normalized_grades = [normalize_grade_name(grade[0]) for grade in all_grades]
    grade_counts = Counter(normalized_grades)
    duplicates = {name: count for name, count in grade_counts.items() if count > 1}
    
    if duplicates:
        print(f"Найдено {len(duplicates)} марок с дубликатами:")
        for grade, count in list(duplicates.items())[:10]:
            print(f"  '{grade}': {count} раз(а)")
        if len(duplicates) > 10:
            print(f"  ... и еще {len(duplicates) - 10} марок")
    else:
        print("Дубликатов не найдено")
    
    print("=" * 60)
    conn.close()

def main():
    """Основная функция"""
    print("=" * 60)
    print("Удаление звездочек и дубликатов из базы данных")
    print("=" * 60)
    
    # Шаг 1: Удаляем звездочки
    remove_asterisks_from_grades()
    
    # Шаг 2: Удаляем дубликаты
    find_and_remove_duplicates()
    
    # Шаг 3: Проверяем результаты
    verify_results()
    
    print("\nГотово!")

if __name__ == "__main__":
    main()

