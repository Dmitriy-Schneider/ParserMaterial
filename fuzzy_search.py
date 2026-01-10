"""
Fuzzy Search - Chemical Composition Similarity Matching
Поиск аналогов марок стали по химическому составу с заданным допуском
"""

import sqlite3
from typing import List, Dict, Optional, Any
from database_schema import get_connection


class CompositionMatcher:
    """
    Поиск аналогов марок стали по химическому составу
    Аналогично функции Fuzzy Search в Stahlschluessel
    """

    # Элементы для сравнения (в порядке приоритета)
    ELEMENTS = [
        'c', 'cr', 'ni', 'mo',      # Высокий приоритет
        'v', 'w', 'co', 'mn', 'si',  # Средний приоритет
        'cu', 'nb', 'n', 's', 'p'    # Низкий приоритет
    ]

    # Обязательные элементы для сравнения
    REQUIRED_ELEMENTS = ['c']  # Хотя бы углерод должен быть

    def __init__(self):
        """Инициализация matcher"""
        self.conn = get_connection()

    def parse_element_value(self, value_str: Any) -> Optional[float]:
        """
        Парсинг значения элемента из БД
        Обрабатывает: '0.30', '3.75-4.50', None, '', 'null'

        Args:
            value_str: Значение из БД

        Returns:
            Float значение (для диапазона - середина) или None
        """
        if not value_str or value_str in ['', 'null', '0', '0.00', None]:
            return None

        value_str = str(value_str).strip()

        # Диапазон: берем середину
        if '-' in value_str:
            try:
                parts = value_str.split('-')
                if len(parts) == 2:
                    low = float(parts[0].strip())
                    high = float(parts[1].strip())
                    return (low + high) / 2
            except (ValueError, IndexError):
                return None

        # Одиночное значение
        try:
            return float(value_str.replace(',', '.'))
        except ValueError:
            return None

    def calculate_element_similarity(self,
                                     val1: Optional[float],
                                     val2: Optional[float],
                                     tolerance_percent: float) -> tuple:
        """
        Расчет похожести между двумя значениями элемента

        Args:
            val1: Значение 1
            val2: Значение 2
            tolerance_percent: Допустимое отклонение (%)

        Returns:
            (is_match: bool, difference_percent: float)
        """
        # Оба отсутствуют: пропускаем этот элемент
        if val1 is None and val2 is None:
            return (True, 0.0)

        # Один отсутствует: не совпадает
        if val1 is None or val2 is None:
            return (False, 100.0)

        # Оба нули: совпадает
        if val1 == 0 and val2 == 0:
            return (True, 0.0)

        # Расчет процентного отклонения
        max_val = max(abs(val1), abs(val2))
        if max_val == 0:
            return (True, 0.0)

        diff_percent = abs(val1 - val2) / max_val * 100

        is_match = diff_percent <= tolerance_percent

        return (is_match, diff_percent)

    def calculate_composition_similarity(self,
                                        ref_composition: Dict[str, Any],
                                        candidate_composition: Dict[str, Any],
                                        tolerance_percent: float) -> Optional[float]:
        """
        Расчет общей похожести химического состава

        Args:
            ref_composition: Эталонный состав (dict с элементами)
            candidate_composition: Состав кандидата
            tolerance_percent: Допустимое отклонение (%)

        Returns:
            Similarity score (0-100) или None если нельзя сравнить
        """
        # Парсинг эталонного состава
        ref_values = {}
        for element in self.ELEMENTS:
            ref_values[element] = self.parse_element_value(
                ref_composition.get(element)
            )

        # Парсинг состава кандидата
        cand_values = {}
        for element in self.ELEMENTS:
            cand_values[element] = self.parse_element_value(
                candidate_composition.get(element)
            )

        # Проверка обязательных элементов
        has_required = False
        for req_elem in self.REQUIRED_ELEMENTS:
            if ref_values.get(req_elem) is not None:
                has_required = True
                break

        if not has_required:
            return None  # Нет обязательных элементов

        # Расчет взвешенной похожести
        total_weight = 0
        matched_weight = 0

        for element in self.ELEMENTS:
            ref_val = ref_values.get(element)
            cand_val = cand_values.get(element)

            # Пропускаем если оба отсутствуют
            if ref_val is None and cand_val is None:
                continue

            # Вес элемента по важности
            if element in ['c', 'cr', 'ni', 'mo']:
                weight = 3  # Высокий приоритет
            elif element in ['v', 'w', 'co', 'mn', 'si']:
                weight = 2  # Средний приоритет
            else:
                weight = 1  # Низкий приоритет

            is_match, diff_percent = self.calculate_element_similarity(
                ref_val, cand_val, tolerance_percent
            )

            total_weight += weight

            if is_match:
                # Оценка: чем ближе - тем выше
                element_score = (100 - diff_percent) / 100 * weight
                matched_weight += element_score

        if total_weight == 0:
            return None  # Нет сопоставимых элементов

        # Итоговая похожесть (0-100)
        similarity = (matched_weight / total_weight) * 100

        return similarity

    def find_similar_grades(self,
                           reference_composition: Dict[str, Any],
                           tolerance_percent: float = 50.0,
                           max_results: int = 10,
                           exclude_grade: Optional[str] = None) -> List[Dict]:
        """
        Поиск марок с похожим химическим составом

        Args:
            reference_composition: Эталонный состав (dict с grade и элементами)
            tolerance_percent: Максимальное отклонение на элемент (0-100)
            max_results: Максимум результатов
            exclude_grade: Марка для исключения (обычно сама эталонная)

        Returns:
            Список похожих марок отсортированный по similarity (от большего к меньшему)
            [
                {
                    'grade': 'AR500',
                    'similarity': 92.5,
                    'c': '0.28',
                    'cr': '1.20',
                    ...
                    'standard': 'ASTM',
                    'manufacturer': 'ArcelorMittal',
                    'link': 'https://...'
                }
            ]
        """
        cursor = self.conn.cursor()

        # Получаем все марки из БД
        cursor.execute("""
            SELECT grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
                   standard, manufacturer, analogues, link, base, tech
            FROM steel_grades
        """)

        columns = [
            'grade', 'c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si',
            'cu', 'nb', 'n', 's', 'p', 'standard', 'manufacturer',
            'analogues', 'link', 'base', 'tech'
        ]

        rows = cursor.fetchall()

        results = []

        for row in rows:
            candidate = dict(zip(columns, row))

            # Пропускаем исключенную марку (обычно саму эталонную)
            if exclude_grade and candidate['grade'] == exclude_grade:
                continue

            # Расчет похожести
            similarity = self.calculate_composition_similarity(
                reference_composition,
                candidate,
                tolerance_percent
            )

            # Пропускаем если нельзя сравнить или похожесть низкая
            if similarity is None or similarity < 40:  # Минимум 40% похожести
                continue

            # Добавляем в результаты
            result_item = {
                'grade': candidate['grade'],
                'similarity': round(similarity, 1),
            }

            # Копируем все поля из candidate
            for key in columns:
                if key != 'grade':  # grade уже добавлен
                    result_item[key] = candidate[key]

            results.append(result_item)

        # Сортировка по похожести (от большего к меньшему)
        results.sort(key=lambda x: x['similarity'], reverse=True)

        # Возвращаем топ N результатов
        return results[:max_results]

    def __del__(self):
        """Закрытие соединения с БД"""
        if hasattr(self, 'conn'):
            self.conn.close()


def get_composition_matcher():
    """Получить экземпляр CompositionMatcher"""
    return CompositionMatcher()


if __name__ == "__main__":
    # Тестирование
    print("=== Fuzzy Search Test ===\n")

    matcher = CompositionMatcher()

    # Пример: найти похожие на HARDOX 500
    reference = {
        'grade': 'HARDOX 500',
        'c': '0.28',
        'cr': '1.00',
        'mo': '0.25',
        'ni': '0.50'
    }

    print(f"Поиск марок похожих на {reference['grade']}")
    print(f"Допуск: 50%, Макс результатов: 10\n")

    results = matcher.find_similar_grades(
        reference_composition=reference,
        tolerance_percent=50.0,
        max_results=10,
        exclude_grade='HARDOX 500'
    )

    if results:
        print(f"Найдено {len(results)} похожих марок:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['grade']}: {result['similarity']}% похожести")
            print(f"   C={result['c']}, Cr={result['cr']}, Mo={result['mo']}, Ni={result['ni']}")
            if result['standard']:
                print(f"   Стандарт: {result['standard']}")
            print()
    else:
        print("Похожие марки не найдены")
