#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import sqlite3
import config
from database_schema import get_connection

def load_russian_grades_csv(filename='russian_steel_grades.csv'):
    """Загружает марки из CSV файла"""
    grades_map = {}  # Словарь: латиница -> кириллица
    
    print(f"Читаю CSV файл: {filename}")
    
    with open(filename, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        
        for row in reader:
            latin_grade = row['Grade (Latin)'].strip()
            cyrillic_grade = row['Grade (Cyrillic)'].strip()
            
            if latin_grade and cyrillic_grade:
                grades_map[latin_grade] = cyrillic_grade
    
    print(f"Загружено марок из CSV: {len(grades_map)}")
    return grades_map

def update_grades_in_database(grades_map):
    """Обновляет названия марок в базе данных с латиницы на кириллицу"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updated_count = 0
    not_found_count = 0
    duplicate_warnings = []
    
    print("\nОбновляю марки в базе данных...")
    print("=" * 60)
    
    for latin_grade, cyrillic_grade in grades_map.items():
        # Проверяем, существует ли марка с латинским названием
        cursor.execute("SELECT id, grade, analogues FROM steel_grades WHERE grade = ?", (latin_grade,))
        existing_row = cursor.fetchone()
        
        if existing_row:
            grade_id, current_grade, analogues = existing_row
            
            # Проверяем, не существует ли уже марка с кириллическим названием
            cursor.execute("SELECT id, grade FROM steel_grades WHERE grade = ?", (cyrillic_grade,))
            duplicate_row = cursor.fetchone()
            
            if duplicate_row:
                duplicate_id, duplicate_grade = duplicate_row
                if duplicate_id != grade_id:
                    duplicate_warnings.append({
                        'latin': latin_grade,
                        'cyrillic': cyrillic_grade,
                        'existing_id': grade_id,
                        'duplicate_id': duplicate_id
                    })
                    print(f"  WARNING: Марка '{cyrillic_grade}' уже существует (ID {duplicate_id})")
                    print(f"    Пропускаю обновление '{latin_grade}' (ID {grade_id})")
                    not_found_count += 1
                    continue
            
            # Обновляем название марки на кириллицу
            try:
                cursor.execute("UPDATE steel_grades SET grade = ? WHERE id = ?", (cyrillic_grade, grade_id))
                if cursor.rowcount > 0:
                    updated_count += 1
                    print(f"  OK: Обновлена марка ID {grade_id}: '{latin_grade}' -> '{cyrillic_grade}'")
                else:
                    print(f"  ERROR: Не удалось обновить марку ID {grade_id}")
            except sqlite3.IntegrityError as e:
                print(f"  ERROR: Ошибка уникальности при обновлении '{latin_grade}': {e}")
                not_found_count += 1
        else:
            not_found_count += 1
            print(f"  NOT FOUND: Марка '{latin_grade}' не найдена в базе данных")
    
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print(f"\nСтатистика обновления:")
    print(f"  Обновлено марок: {updated_count}")
    print(f"  Не найдено/пропущено: {not_found_count}")
    print(f"  Предупреждений о дубликатах: {len(duplicate_warnings)}")
    
    return updated_count, not_found_count, duplicate_warnings

def check_duplicates():
    """Проверяет дубликаты в базе данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\nПроверка на дубликаты...")
    print("=" * 60)
    
    # Проверяем дубликаты по названию марки
    cursor.execute("""
        SELECT grade, COUNT(*) as count 
        FROM steel_grades 
        GROUP BY grade 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"Найдено {len(duplicates)} марок-дубликатов:")
        for grade, count in duplicates:
            cursor.execute("SELECT id, analogues, base FROM steel_grades WHERE grade = ?", (grade,))
            rows = cursor.fetchall()
            print(f"\n  Марка '{grade}' встречается {count} раз(а):")
            for row_id, analogues, base in rows:
                print(f"    ID {row_id}, Analogues: {analogues}, Base: {base}")
    else:
        print("Дубликатов по названию марки не найдено")
    
    conn.close()
    
    return len(duplicates)

def main():
    """Основная функция"""
    print("=" * 60)
    print("Обновление русских марок сталей в базе данных")
    print("=" * 60)
    
    # Загружаем марки из CSV
    grades_map = load_russian_grades_csv()
    
    if not grades_map:
        print("Не удалось загрузить марки из CSV файла!")
        return
    
    # Обновляем марки в базе данных
    updated, not_found, warnings = update_grades_in_database(grades_map)
    
    # Проверяем дубликаты
    duplicates_count = check_duplicates()
    
    # Финальная статистика
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM steel_grades")
    total_count = cursor.fetchone()[0]
    conn.close()
    
    print("=" * 60)
    print("\nФинальная статистика:")
    print(f"  Всего марок в базе: {total_count}")
    print(f"  Обновлено из CSV: {updated}")
    print(f"  Дубликатов: {duplicates_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()






