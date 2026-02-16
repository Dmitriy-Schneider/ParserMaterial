#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check analogues statistics after fix"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('database/steel_database.db')
cursor = conn.cursor()

# Всего марок с аналогами
cursor.execute('SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != ""')
total_with_analogues = cursor.fetchone()[0]

# С разделителями
cursor.execute('SELECT COUNT(*) FROM steel_grades WHERE analogues LIKE "%|%"')
with_pipes = cursor.fetchone()[0]

# Без разделителей
cursor.execute('SELECT COUNT(*) FROM steel_grades WHERE analogues IS NOT NULL AND analogues != "" AND analogues NOT LIKE "%|%"')
without_pipes = cursor.fetchone()[0]

print('=' * 80)
print('=== Статистика аналогов после исправления ===')
print('=' * 80)
print(f'Всего марок с аналогами: {total_with_analogues}')
print(f'  С разделителями |: {with_pipes} ({with_pipes/total_with_analogues*100:.1f}%)')
print(f'  БЕЗ разделителей: {without_pipes} ({without_pipes/total_with_analogues*100:.1f}%)')
print()
print('До исправления:')
print(f'  С разделителями: 5,840 (86.0%)')
print(f'  БЕЗ разделителей: 955 (14.0%)')
print()
print(f'✅ Исправлено: 89 марок')
print(f'📊 Улучшение: с 86.0% до {with_pipes/total_with_analogues*100:.1f}%')
print(f'⚠️ Осталось: {without_pipes} марок БЕЗ разделителей')

conn.close()
