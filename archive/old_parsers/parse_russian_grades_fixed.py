#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import csv
import re

# Словарь транслитерации латиницы в кириллицу для марок сталей
# Согласно ГОСТ 7.79-2000 и специфике марок сталей
# ВАЖНО: многосимвольные комбинации должны обрабатываться ПЕРВЫМИ

TRANSLIT_COMBINATIONS = {
    # Многосимвольные комбинации (обрабатываются первыми)
    'KH': 'Х',  # По ГОСТ Kh → Х, в марках часто заглавные KH
    'Kh': 'Х',
    'kh': 'х',
    'CH': 'Ч',  # В марках сталей обычно Ч
    'Ch': 'Ч',
    'ch': 'ч',
    'SH': 'Ш',
    'Sh': 'Ш',
    'sh': 'ш',
    'ZH': 'Ж',
    'Zh': 'Ж',
    'zh': 'ж',
    'TS': 'Ц',
    'Ts': 'Ц',
    'ts': 'ц',
    'YU': 'Ю',
    'Yu': 'Ю',
    'yu': 'ю',
    'YA': 'Я',
    'Ya': 'Я',
    'ya': 'я',
}

# Одиночные символы (обрабатываются после комбинаций)
TRANSLIT_SINGLE = {
    # Заглавные буквы
    'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К',
    'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У',
    'F': 'Ф', 'V': 'В', 'S': 'С', 'D': 'Д', 'G': 'Г', 'R': 'Р',
    'L': 'Л', 'N': 'Н', 'I': 'И', 'U': 'У',
    # Строчные буквы
    'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'h': 'н', 'k': 'к',
    'm': 'м', 'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у',
    'f': 'ф', 'v': 'в', 's': 'с', 'd': 'д', 'g': 'г', 'r': 'р',
    'l': 'л', 'n': 'н', 'i': 'и', 'u': 'у',
}

def transliterate_to_cyrillic(text):
    """
    Преобразует латиницу в кириллицу для марок сталей
    Сначала обрабатывает многосимвольные комбинации, затем одиночные символы
    Сохраняет цифры, дефисы, звездочки и другие символы
    """
    result = []
    i = 0
    text_len = len(text)
    
    while i < text_len:
        # Проверяем многосимвольные комбинации (2 символа)
        if i + 1 < text_len:
            two_chars = text[i:i+2]
            # Проверяем сначала заглавные, потом строчные, потом смешанные
            if two_chars in TRANSLIT_COMBINATIONS:
                result.append(TRANSLIT_COMBINATIONS[two_chars])
                i += 2
                continue
            # Проверяем варианты с разным регистром
            two_chars_variants = [
                two_chars.upper(),
                two_chars.capitalize(),
                two_chars.lower()
            ]
            found = False
            for variant in two_chars_variants:
                if variant in TRANSLIT_COMBINATIONS:
                    result.append(TRANSLIT_COMBINATIONS[variant])
                    i += 2
                    found = True
                    break
            if found:
                continue
        
        # Обрабатываем одиночный символ
        char = text[i]
        if char in TRANSLIT_SINGLE:
            result.append(TRANSLIT_SINGLE[char])
        else:
            result.append(char)  # Сохраняем цифры, дефисы и другие символы
        
        i += 1
    
    return ''.join(result)

def parse_russian_grades():
    """Парсит страницу с русскими марками стали и извлекает все главные марки"""
    url = "https://zknives.com/knives/steels/ru"
    
    print(f"Загружаю страницу: {url}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        print("Страница успешно загружена")
    except Exception as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Находим все элементы с классом stlNmLnk
    grade_elements = soup.find_all(class_='stlNmLnk')
    
    print(f"Найдено элементов с классом stlNmLnk: {len(grade_elements)}")
    
    grades = []
    seen_grades = set()
    
    for element in grade_elements:
        # Извлекаем текст марки
        grade_text = element.get_text(strip=True)
        
        # Пропускаем пустые значения
        if not grade_text or grade_text == '':
            continue
        
        # Пропускаем дубликаты
        if grade_text in seen_grades:
            continue
        
        seen_grades.add(grade_text)
        grades.append(grade_text)
        print(f"  Найдена марка: {grade_text}")
    
    print(f"\nВсего уникальных марок найдено: {len(grades)}")
    
    return grades

def create_csv_with_transliteration(grades):
    """Создает CSV файл с двумя столбцами: латиница и кириллица"""
    filename = "russian_steel_grades.csv"
    
    print(f"\nСоздаю CSV файл с правильной транслитерацией: {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        
        # Записываем заголовок
        writer.writerow(['Grade (Latin)', 'Grade (Cyrillic)'])
        
        # Записываем данные
        for grade in grades:
            cyrillic_grade = transliterate_to_cyrillic(grade)
            writer.writerow([grade, cyrillic_grade])
            if len(grades) <= 50 or grades.index(grade) < 10 or grades.index(grade) >= len(grades) - 5:
                print(f"  {grade} -> {cyrillic_grade}")
    
    print(f"\nCSV файл создан: {filename}")
    print(f"Всего записей: {len(grades)}")
    
    return filename

def main():
    """Основная функция"""
    print("=" * 60)
    print("Парсинг русских марок сталей с правильной транслитерацией")
    print("=" * 60)
    
    # Парсим марки
    grades = parse_russian_grades()
    
    if not grades:
        print("Не удалось найти марки сталей!")
        return
    
    # Создаем CSV файл
    filename = create_csv_with_transliteration(grades)
    
    # Показываем примеры проверки
    print("\nПримеры транслитерации:")
    test_cases = ['03KH17N13M2', 'KH12MF', '08KH18N10', 'X12MF', '11KHF']
    for test in test_cases:
        result = transliterate_to_cyrillic(test)
        print(f"  {test} -> {result}")
    
    print("=" * 60)
    print(f"Готово! Файл сохранен: {filename}")
    print("=" * 60)

if __name__ == "__main__":
    main()






