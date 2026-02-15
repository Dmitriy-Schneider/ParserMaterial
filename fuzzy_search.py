"""
Fuzzy Search - Chemical Composition Similarity Matching
Поиск аналогов марок стали по химическому составу с заданным допуском

Версия 2.0: Гибридный подход с классификацией сталей и приоритетом элементов
- Классификация стали по химсоставу (15 групп)
- Веса элементов загружаются из config/element_weights.csv
- Smart Max Mismatched учитывает значимость элементов для группы стали
"""

import sqlite3
import csv
import os
import re
from typing import List, Dict, Optional, Any, Tuple
from database_schema import get_connection


# ============================================================================
# КЛАССИФИКАЦИЯ СТАЛЕЙ ПО ХИМИЧЕСКОМУ СОСТАВУ
# ============================================================================

class SteelGroup:
    """Группа стали с весами элементов"""

    def __init__(self, group_id: str, name_ru: str, name_en: str,
                 element_weights: Dict[str, int], description: str = ""):
        self.group_id = group_id
        self.name_ru = name_ru
        self.name_en = name_en
        self.element_weights = element_weights
        self.description = description

    def get_element_weight(self, element: str) -> int:
        """Получить вес элемента (0-10). По умолчанию 1."""
        return self.element_weights.get(element.lower(), 1)

    def get_elements_by_priority(self) -> List[str]:
        """Получить список элементов от малозначимых к критичным"""
        return sorted(self.element_weights.keys(),
                     key=lambda e: self.element_weights[e])


def load_steel_groups_from_csv(csv_path: str = None) -> Dict[str, SteelGroup]:
    """Загрузка групп сталей с весами элементов из CSV файла"""
    if csv_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, 'config', 'element_weights.csv')

    groups = {}

    if not os.path.exists(csv_path):
        return _get_default_steel_groups()

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('group_id'):
                    continue
                element_weights = {}
                for element in ['c', 'cr', 'ni', 'mo', 'v', 'w', 'co',
                               'mn', 'si', 'cu', 'nb', 'n', 's', 'p']:
                    if element in row and row[element]:
                        try:
                            element_weights[element] = int(row[element])
                        except ValueError:
                            element_weights[element] = 1
                groups[row['group_id']] = SteelGroup(
                    group_id=row['group_id'],
                    name_ru=row.get('group_name_ru', ''),
                    name_en=row.get('group_name_en', ''),
                    element_weights=element_weights,
                    description=row.get('description', '')
                )
    except Exception as e:
        print(f"Warning: Could not load steel groups from CSV: {e}")
        return _get_default_steel_groups()

    return groups


def _get_default_steel_groups() -> Dict[str, SteelGroup]:
    """Базовые группы сталей (fallback если CSV недоступен)"""
    return {
        'COLD_WORK_TOOL': SteelGroup('COLD_WORK_TOOL', 'Холодноштамповые',
            'Cold Work Tool Steel',
            {'c': 10, 'cr': 10, 'v': 9, 'mo': 8, 'w': 7, 'nb': 7,
             'mn': 5, 'si': 4, 'ni': 3, 'co': 3, 'cu': 2, 'n': 2}),
        'HOT_WORK_TOOL': SteelGroup('HOT_WORK_TOOL', 'Горячештамповые',
            'Hot Work Tool Steel',
            {'mo': 10, 'cr': 10, 'v': 9, 'w': 8, 'ni': 7, 'c': 7,
             'si': 5, 'co': 4, 'mn': 4, 'cu': 2, 'nb': 2, 'n': 2}),
        'HSS_HIGH_SPEED': SteelGroup('HSS_HIGH_SPEED', 'Быстрорежущие',
            'High Speed Steel',
            {'w': 10, 'mo': 10, 'v': 9, 'co': 8, 'c': 8, 'cr': 5,
             'mn': 3, 'si': 3, 'ni': 2, 'cu': 1, 'nb': 4, 'n': 2}),
        'STAINLESS_AUSTENITIC': SteelGroup('STAINLESS_AUSTENITIC',
            'Нержавеющие аустенитные', 'Austenitic Stainless Steel',
            {'cr': 10, 'ni': 10, 'mo': 9, 'n': 7, 'c': 5, 'nb': 6,
             'mn': 4, 'si': 3, 'cu': 3, 'co': 2, 'v': 2, 'w': 2}),
        'ALLOY_STRUCTURAL': SteelGroup('ALLOY_STRUCTURAL',
            'Конструкционные легированные', 'Alloy Structural Steel',
            {'c': 9, 'cr': 7, 'ni': 7, 'mo': 7, 'mn': 6, 'v': 5,
             'si': 4, 'w': 3, 'cu': 3, 'nb': 3, 'n': 3, 'co': 2}),
        'CARBON_STEEL': SteelGroup('CARBON_STEEL', 'Углеродистые',
            'Carbon Steel',
            {'c': 10, 'mn': 6, 'si': 4, 'cr': 3, 'ni': 2, 'mo': 3,
             'v': 2, 'w': 2, 'cu': 2, 'nb': 2, 'n': 2, 'co': 1}),
    }


# Глобальный кэш групп сталей
_STEEL_GROUPS_CACHE: Optional[Dict[str, SteelGroup]] = None


def get_steel_groups() -> Dict[str, SteelGroup]:
    """Получить словарь групп сталей (с кэшированием)"""
    global _STEEL_GROUPS_CACHE
    if _STEEL_GROUPS_CACHE is None:
        _STEEL_GROUPS_CACHE = load_steel_groups_from_csv()
    return _STEEL_GROUPS_CACHE


# Совместимые группы для smart-режима (минимальный набор)
_COMPATIBLE_GROUPS = {
    'CARBON_STEEL': {'CARBON_STEEL', 'ALLOY_STRUCTURAL', 'WEAR_RESISTANT'},
    'ALLOY_STRUCTURAL': {'ALLOY_STRUCTURAL', 'CARBON_STEEL', 'WEAR_RESISTANT'},
    'WEAR_RESISTANT': {'WEAR_RESISTANT', 'ALLOY_STRUCTURAL', 'CARBON_STEEL'},
    'STAINLESS_AUSTENITIC': {'STAINLESS_AUSTENITIC', 'STAINLESS_DUPLEX'},
    'STAINLESS_DUPLEX': {'STAINLESS_DUPLEX', 'STAINLESS_AUSTENITIC'},
}


def is_compatible_group(ref_group_id: Optional[str], candidate_group_id: Optional[str]) -> bool:
    """Проверка совместимости групп в smart-режиме"""
    if not ref_group_id or not candidate_group_id:
        return True
    allowed = _COMPATIBLE_GROUPS.get(ref_group_id, {ref_group_id})
    return candidate_group_id in allowed


_NON_FERROUS_NAME_PATTERNS = [
    # Latin symbol-based patterns
    ('LEAD_ALLOY', re.compile(r'Pb', re.IGNORECASE)),
    ('TIN_ALLOY', re.compile(r'Sn', re.IGNORECASE)),
    ('ZINC_ALLOY', re.compile(r'Zn', re.IGNORECASE)),
    # Copper-base variants (order matters)
    ('COPPER_BRASS', re.compile(r'Cu\\s*Zn|CuZn', re.IGNORECASE)),
    ('COPPER_BRONZE_TIN', re.compile(r'Cu\\s*Sn|CuSn', re.IGNORECASE)),
    ('COPPER_BRONZE_AL', re.compile(r'Cu\\s*Al|CuAl', re.IGNORECASE)),
    ('COPPER_NICKEL', re.compile(r'Cu\\s*Ni|CuNi', re.IGNORECASE)),
    ('COPPER_PURE', re.compile(r'Cu', re.IGNORECASE)),
    # Other bases
    ('ALUMINUM_ALLOY', re.compile(r'\\bAl\\b|Al\\d|AlMg|AlSi|AlZn', re.IGNORECASE)),
    ('MAGNESIUM_ALLOY', re.compile(r'Mg', re.IGNORECASE)),
    ('TITANIUM_ALLOY', re.compile(r'Ti', re.IGNORECASE)),
    ('NICKEL_ALLOY', re.compile(r'\\bNi\\b|Ni\\d', re.IGNORECASE)),
    # Cyrillic patterns (Russian grade systems)
    ('COPPER_BRASS', re.compile(r'^(ЛС|ЛЦ|ЛЖ|ЛК|ЛО|ЛН|ЛМ|ЛА)|^Л\\d', re.IGNORECASE)),
    ('COPPER_BRONZE_AL', re.compile(r'^БРА', re.IGNORECASE)),
    ('COPPER_BRONZE_TIN', re.compile(r'^БР', re.IGNORECASE)),
    ('COPPER_NICKEL', re.compile(r'^МН', re.IGNORECASE)),
    ('COPPER_PURE', re.compile(r'^М\\d', re.IGNORECASE)),
    ('ALUMINUM_ALLOY', re.compile(r'^(АЛ|АК|АМГ|АМЦ|АД|Д|В)\\d', re.IGNORECASE)),
    ('TITANIUM_ALLOY', re.compile(r'^ВТ', re.IGNORECASE)),
    ('MAGNESIUM_ALLOY', re.compile(r'^МГ', re.IGNORECASE)),
]


def classify_non_ferrous_by_name(grade_name: Optional[str]) -> Optional[str]:
    """Классификация цветных сплавов по названию марки (упрощенно)."""
    if not grade_name:
        return None
    name = str(grade_name).strip()
    if not name:
        return None
    for group_id, pattern in _NON_FERROUS_NAME_PATTERNS:
        if pattern.search(name):
            # Pb + Sn чаще всего припой/свинцово-оловянный
            if group_id == 'TIN_ALLOY' and re.search(r'Pb', name, re.IGNORECASE):
                return 'LEAD_ALLOY'
            return group_id
    return None


def classify_non_ferrous_by_composition(cu: Optional[float],
                                        ni: Optional[float],
                                        c: Optional[float],
                                        cr: Optional[float],
                                        mo: Optional[float],
                                        v: Optional[float],
                                        w: Optional[float],
                                        co: Optional[float],
                                        mn: Optional[float],
                                        si: Optional[float],
                                        n: Optional[float]) -> Optional[str]:
    """Классификация цветных по составу (если есть только Cu/Ni)."""
    # Если есть Cu и почти нет "стальных" элементов — считаем медным
    steel_like = any(val is not None for val in [c, cr, mo, v, w, co, mn, si, n])
    if cu is None:
        return None
    if not steel_like:
        if ni is not None:
            return 'COPPER_NICKEL'
        return 'COPPER_PURE'
    return None


def classify_steel(composition: Dict[str, Any]) -> str:
    """
    Определение типа стали по химическому составу

    Returns:
        ID группы стали (COLD_WORK_TOOL, HSS_HIGH_SPEED, etc.)
    """
    def parse_val(v):
        if v is None or v == '' or v == 'null':
            return None
        try:
            s = str(v).strip()
            if '-' in s and not s.startswith('-'):
                parts = s.split('-')
                return (float(parts[0].replace(',', '.')) +
                        float(parts[1].replace(',', '.'))) / 2
            return float(s.replace(',', '.'))
        except:
            return None

    c = parse_val(composition.get('c'))
    cr = parse_val(composition.get('cr'))
    ni = parse_val(composition.get('ni'))
    mo = parse_val(composition.get('mo'))
    w = parse_val(composition.get('w'))
    mn = parse_val(composition.get('mn'))
    v = parse_val(composition.get('v'))
    co = parse_val(composition.get('co'))
    n = parse_val(composition.get('n'))
    si = parse_val(composition.get('si'))
    cu = parse_val(composition.get('cu'))

    # Если вообще нет данных — не классифицируем
    if not any(v is not None for v in [c, cr, ni, mo, w, mn, v, co, n, si, cu]):
        return None

    # 1. Жаропрочные никелевые (Ni > 40%)
    if ni and ni > 40:
        return 'NICKEL_SUPERALLOY'

    # 2. Высокомарганцовистые (Mn > 10%)
    if mn and mn > 10:
        return 'HADFIELD_MN'

    # 3. Быстрорежущие (W > 5% или Mo > 3% при C > 0.7%)
    if c and c > 0.7:
        if (w and w > 5) or (mo and mo > 3 and (w is None or w < 2)):
            return 'HSS_HIGH_SPEED'

    # 4. Порошковые/высоколегированные инструментальные (M390/Elmax и аналоги)
    # Отличие от нержавеющих: очень высокий C + высокий Cr + карбидообразователи
    if c and c >= 1.0 and cr and cr >= 12:
        if (v and v >= 1) or (mo and mo >= 1) or (w and w >= 1):
            return 'COLD_WORK_TOOL'

    # 5. Холодноштамповые (C > 0.5%, Cr 5-15%)
    # ВАЖНО: Проверяем ДО нержавеющих, т.к. инструментальные D2/1.2379 имеют Cr=12%
    # Отличие от нержавейки: высокий C (>0.5%) + наличие Mo/V
    if c and c > 0.5 and cr and 5 <= cr <= 15:
        # Дополнительная проверка: если есть Mo или V - точно инструментальная
        if mo or v or c > 1.0:
            return 'COLD_WORK_TOOL'

    # 6. Нержавеющие (Cr > 10%)
    if cr and cr > 10:
        # Дуплексные: высокий Cr + умеренный Ni, N может отсутствовать в данных
        if cr >= 20 and ni and 4 <= ni <= 8 and (c is None or c <= 0.08):
            if n is None or n >= 0.05:
                return 'STAINLESS_DUPLEX'
        if ni and ni > 7:
            return 'STAINLESS_AUSTENITIC'
        if c and c > 0.1:
            return 'STAINLESS_MARTENSITIC'
        return 'STAINLESS_FERRITIC'

    # 7. Горячештамповые (C 0.25-0.55%, Cr 3-8%, Mo > 0.8%)
    if c and 0.25 <= c <= 0.55 and cr and 3 <= cr <= 8:
        if mo and mo > 0.8:
            return 'HOT_WORK_TOOL'

    # 8. Для пресс-форм (P20/1.2311/1.2312 тип)
    if c and 0.2 <= c <= 0.55:
        if (cr and 1 <= cr <= 3) and (ni and ni > 0.5):
            return 'PLASTIC_MOLD'

    # 9. Подшипниковые (C ~ 1%, Cr ~ 1.5%)
    if c and 0.9 <= c <= 1.1 and cr and 1.3 <= cr <= 1.7:
        return 'BEARING_STEEL'

    # 10. Пружинные (C 0.5-0.7%, Si > 1.5%)
    if c and 0.5 <= c <= 0.7:
        if (si and si > 1.5) or (mn and mn > 0.8):
            return 'SPRING_STEEL'

    # 11. Износостойкие (C 0.15-0.35%, Mn > 0.8%)
    if c and 0.15 <= c <= 0.35 and mn and mn > 0.8:
        if cr is None or cr < 3:
            return 'WEAR_RESISTANT'

    # 12. Конструкционные легированные
    if cr and cr > 0.5:
        return 'ALLOY_STRUCTURAL'

    # Цветные сплавы (упрощенная классификация по названию/составу)
    non_ferrous = classify_non_ferrous_by_name(composition.get('grade'))
    if non_ferrous:
        return non_ferrous
    non_ferrous = classify_non_ferrous_by_composition(
        cu=cu, ni=ni, c=c, cr=cr, mo=mo, v=v, w=w, co=co, mn=mn, si=si, n=n
    )
    if non_ferrous:
        return non_ferrous

    # 13. Углеродистые (по умолчанию для стали)
    steel_like = any(val is not None for val in [c, cr, ni, mo, w, mn, v, co, n, si])
    if steel_like:
        return 'CARBON_STEEL'
    return None


class CompositionMatcher:
    """
    Поиск аналогов марок стали по химическому составу
    Аналогично функции Fuzzy Search в Stahlschluessel
    """

    # Элементы для сравнения (в порядке приоритета)
    # Примечание: S и P исключены, так как часто не указываются в данных
    ELEMENTS = [
        'c', 'cr', 'ni', 'mo',      # Высокий приоритет
        'v', 'w', 'co', 'mn', 'si',  # Средний приоритет
        'cu', 'nb', 'n'              # Низкий приоритет
    ]

    # Обязательные элементы для сравнения
    REQUIRED_ELEMENTS = ['c']  # Хотя бы углерод должен быть
    # Минимальное число сравнимых элементов для smart-режима
    MIN_COMPARABLE_ELEMENTS = 3

    def __init__(self):
        """Инициализация matcher"""
        self.conn = get_connection()

    def parse_element_value(self, value_str: Any) -> Optional[float]:
        """
        Парсинг значения элемента из БД
        Обрабатывает:
        - '0.30' - одиночное значение
        - '3.75-4.50' - диапазон (берем середину)
        - 'до 0.08' - максимальное значение (берем как есть)
        - 'до &nbsp; 1' - с HTML entities (декодируем)
        - None, '', 'null', '0', '0.00' - возвращаем None

        Args:
            value_str: Значение из БД

        Returns:
            Float значение (для диапазона - середина) или None
        """
        if not value_str or value_str in ['', 'null', '0', '0.00', None]:
            return None

        value_str = str(value_str).strip()

        # Декодируем HTML entities (например, &nbsp; → пробел)
        import html
        value_str = html.unescape(value_str)

        # Удаляем HTML entities которые не декодировались
        value_str = value_str.replace('&nbsp;', ' ')

        # Удаляем лишние пробелы
        value_str = ' '.join(value_str.split())

        # Обрабатываем префикс "до" (максимальное значение)
        if value_str.startswith('до '):
            value_str = value_str[3:].strip()

        # Диапазон: берем середину
        if '-' in value_str and not value_str.startswith('-'):
            try:
                parts = value_str.split('-')
                if len(parts) == 2:
                    low = float(parts[0].strip().replace(',', '.'))
                    high = float(parts[1].strip().replace(',', '.'))
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

        # Расчет процентного отклонения от эталонного значения (val1)
        # tolerance_percent = допустимое отклонение от val1 (reference)
        # Пример: val1=1.40, tolerance=5% → допустимо 1.33-1.47
        if abs(val1) == 0:
            # Если эталон = 0, используем абсолютное сравнение
            # Считаем match если val2 тоже близко к нулю (в пределах 0.01)
            diff_percent = abs(val2) * 10000  # Большое значение если val2 не ноль
            is_match = abs(val2) < 0.01
            return (is_match, diff_percent)

        # Стандартный расчет: процент отклонения от эталона
        diff_percent = abs(val1 - val2) / abs(val1) * 100

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

            # КРИТИЧНО: Пропускаем если ХОТЯ БЫ ОДИН элемент отсутствует
            # Сравниваем только элементы, присутствующие у ОБЕИХ марок
            # Это предотвращает ложное снижение similarity из-за неполных данных
            if ref_val is None or cand_val is None:
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

    def count_mismatched_elements(self,
                                  ref_composition: Dict[str, Any],
                                  candidate_composition: Dict[str, Any],
                                  tolerance_percent: float) -> int:
        """
        Подсчет количества элементов, НЕ прошедших tolerance (legacy режим)

        Args:
            ref_composition: Эталонный состав
            candidate_composition: Состав кандидата
            tolerance_percent: Допустимое отклонение (%)

        Returns:
            Количество элементов с отклонением > tolerance_percent
        """
        mismatched_count = 0

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

        # Подсчет несовпадающих элементов
        for element in self.ELEMENTS:
            ref_val = ref_values.get(element)
            cand_val = cand_values.get(element)

            # Сравниваем только элементы, присутствующие у ОБЕИХ марок
            if ref_val is None or cand_val is None:
                continue

            # Сравниваем элементы
            is_match, diff_percent = self.calculate_element_similarity(
                ref_val, cand_val, tolerance_percent
            )

            # Если не совпадает, увеличиваем счетчик
            if not is_match:
                mismatched_count += 1

        return mismatched_count

    def _get_allowed_mismatch_weight(self,
                                     max_mismatched: int,
                                     steel_group: SteelGroup) -> int:
        """Максимальный вес элемента, который можно "простить" при заданном лимите"""
        if max_mismatched <= 0:
            return 0
        weights = [steel_group.get_element_weight(e) for e in self.ELEMENTS]
        weights.sort()
        if max_mismatched >= len(weights):
            return weights[-1]
        return weights[max_mismatched - 1]

    # Порог веса для критичных элементов (вес >= CRITICAL_WEIGHT не прощается)
    CRITICAL_WEIGHT_THRESHOLD = 8

    def smart_count_mismatched(self,
                               ref_composition: Dict[str, Any],
                               candidate_composition: Dict[str, Any],
                               tolerance_percent: float,
                               max_mismatched: int,
                               steel_group: SteelGroup,
                               protect_critical: bool = True) -> Tuple[bool, int, List[str], float]:
        """
        Умный подсчет mismatched с учетом значимости элементов

        Логика:
        1) Подсчёт mismatched элементов
        2) Защита критичных элементов (вес >= 8): если protect_critical=True,
           критичные элементы НЕ прощаются (кроме случая max_mismatched >= 10)
        3) Фильтр по количеству: total_mismatched <= max_mismatched
        4) Расчёт "штрафа" для сортировки результатов

        Args:
            ref_composition: Эталонный состав
            candidate_composition: Состав кандидата
            tolerance_percent: Допустимое отклонение (%)
            max_mismatched: Максимальное количество mismatched элементов
            steel_group: Группа стали с весами элементов
            protect_critical: Защищать критичные элементы (по умолчанию True)

        Returns:
            (passes_filter: bool, mismatched_count: int, mismatched_elements: List[str], penalty_score: float)
        """
        mismatched_elements = []
        mismatched_weights = []  # (element, weight, diff_percent)
        comparable_count = 0
        critical_mismatched = 0  # Количество критичных элементов с отклонением

        # Парсинг составов
        ref_values = {e: self.parse_element_value(ref_composition.get(e))
                     for e in self.ELEMENTS}
        cand_values = {e: self.parse_element_value(candidate_composition.get(e))
                      for e in self.ELEMENTS}

        for element in self.ELEMENTS:
            ref_val = ref_values.get(element)
            cand_val = cand_values.get(element)

            # Сравниваем только элементы, присутствующие у ОБЕИХ марок
            if ref_val is None or cand_val is None:
                continue

            comparable_count += 1

            is_match, diff_percent = self.calculate_element_similarity(
                ref_val, cand_val, tolerance_percent
            )

            if not is_match:
                weight = steel_group.get_element_weight(element)
                mismatched_elements.append(element)
                mismatched_weights.append((element, weight, diff_percent))
                if weight >= self.CRITICAL_WEIGHT_THRESHOLD:
                    critical_mismatched += 1

        total_mismatched = len(mismatched_elements)

        # Недостаточно сравнимых элементов
        if comparable_count < self.MIN_COMPARABLE_ELEMENTS:
            return (False, total_mismatched, mismatched_elements, 999.0)

        if total_mismatched == 0:
            return (True, 0, [], 0.0)

        # Защита критичных элементов (вес >= 8)
        # Если есть mismatched критичные элементы И max_mismatched < 10, отклоняем
        if protect_critical and critical_mismatched > 0 and max_mismatched < 10:
            return (False, total_mismatched, mismatched_elements, 999.0)

        # Фильтр по количеству
        if total_mismatched > max_mismatched:
            return (False, total_mismatched, mismatched_elements, 999.0)

        # Расчёт штрафа: сумма (вес * отклонение) для mismatched элементов
        penalty_score = sum(w * (d / 100.0) for _, w, d in mismatched_weights)

        return (True, total_mismatched, mismatched_elements, penalty_score)

    def find_similar_grades(self,
                           reference_composition: Dict[str, Any],
                           tolerance_percent: float = 50.0,
                           max_mismatched_elements: int = 3,
                           exclude_grade: Optional[str] = None,
                           smart_mode: bool = False) -> List[Dict]:
        """
        Поиск марок с похожим химическим составом

        Args:
            reference_composition: Эталонный состав (dict с grade и элементами)
            tolerance_percent: Максимальное отклонение на элемент (0-100)
            max_mismatched_elements: Максимальное количество элементов с отклонением > tolerance
            exclude_grade: Марка для исключения (обычно сама эталонная)
            smart_mode: Использовать умный режим с классификацией сталей

        Returns:
            Список похожих марок отсортированный по similarity (от большего к меньшему)
            Ограничен 100 марками для производительности
            [
                {
                    'grade': 'AR500',
                    'similarity': 92.5,
                    'mismatched_count': 2,
                    'steel_group': 'WEAR_RESISTANT',  # только в smart_mode
                    'steel_group_name': 'Износостойкие',  # только в smart_mode
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

        # Получаем все марки из БД (S и P для отображения, но не для расчета)
        cursor.execute("""
            SELECT grade, c, cr, ni, mo, v, w, co, mn, si, cu, nb, n, s, p,
                   standard, manufacturer, analogues, link, base, tech, other
            FROM steel_grades
        """)

        columns = [
            'grade', 'c', 'cr', 'ni', 'mo', 'v', 'w', 'co', 'mn', 'si',
            'cu', 'nb', 'n', 's', 'p', 'standard', 'manufacturer',
            'analogues', 'link', 'base', 'tech', 'other'
        ]

        rows = cursor.fetchall()

        # Подготовка списка прямых аналогов (если есть)
        analogues_set = set()
        ref_analogues = reference_composition.get('analogues')
        if ref_analogues:
            if '|' in str(ref_analogues):
                parts = str(ref_analogues).split('|')
            else:
                parts = str(ref_analogues).split()
            analogues_set = {p.strip() for p in parts if p and p.strip()}

        # Определяем группу эталонной стали для smart режима
        ref_steel_group = None
        ref_steel_group_id = None
        steel_groups = None
        if smart_mode:
            steel_groups = get_steel_groups()
            ref_steel_group_id = classify_steel(reference_composition)
            ref_steel_group = steel_groups.get(ref_steel_group_id)
            # Fallback на ALLOY_STRUCTURAL если группа не найдена
            if ref_steel_group is None:
                ref_steel_group_id = 'ALLOY_STRUCTURAL'
                ref_steel_group = steel_groups.get('ALLOY_STRUCTURAL',
                    _get_default_steel_groups()['ALLOY_STRUCTURAL'])

        results = []

        for row in rows:
            candidate = dict(zip(columns, row))

            # Пропускаем исключенную марку (обычно саму эталонную)
            if exclude_grade and candidate['grade'] == exclude_grade:
                continue

            candidate_group_id = None
            candidate_group_name = None
            if smart_mode and steel_groups:
                candidate_group_id = classify_steel(candidate)
                if not is_compatible_group(ref_steel_group_id, candidate_group_id):
                    continue
                candidate_group = steel_groups.get(candidate_group_id)
                if candidate_group:
                    candidate_group_name = candidate_group.name_ru

            penalty_score = 0.0
            if smart_mode and ref_steel_group:
                # SMART режим: учитываем значимость элементов
                passes, mismatched_count, mismatched_elems, penalty_score = self.smart_count_mismatched(
                    reference_composition,
                    candidate,
                    tolerance_percent,
                    max_mismatched_elements,
                    ref_steel_group
                )
                if not passes:
                    continue
            else:
                # LEGACY режим: простой подсчет
                mismatched_count = self.count_mismatched_elements(
                    reference_composition,
                    candidate,
                    tolerance_percent
                )
                if mismatched_count > max_mismatched_elements:
                    continue

            # Расчет похожести для сортировки
            if smart_mode and ref_steel_group:
                # Используем веса группы для расчета similarity
                similarity = self.calculate_weighted_similarity(
                    reference_composition,
                    candidate,
                    tolerance_percent,
                    ref_steel_group
                )
            else:
                similarity = self.calculate_composition_similarity(
                    reference_composition,
                    candidate,
                    tolerance_percent
                )

            # Пропускаем если нельзя сравнить
            if similarity is None:
                continue

            # Исключаем прямые аналоги только если они явно указаны
            if similarity >= 99.5 and candidate['grade'] in analogues_set:
                continue

            # Добавляем в результаты
            result_item = {
                'grade': candidate['grade'],
                'similarity': round(similarity, 1),
                'mismatched_count': mismatched_count,
                'penalty_score': round(penalty_score, 2),  # Штраф за критичные mismatched
            }

            # Добавляем информацию о группе стали в smart режиме
            if smart_mode and ref_steel_group:
                result_item['steel_group'] = ref_steel_group_id
                result_item['steel_group_name'] = ref_steel_group.name_ru
                result_item['candidate_steel_group'] = candidate_group_id
                result_item['candidate_steel_group_name'] = candidate_group_name

            # Копируем все поля из candidate
            for key in columns:
                if key != 'grade':  # grade уже добавлен
                    result_item[key] = candidate[key]

            results.append(result_item)

        # Сортировка:
        # 1) По похожести (от большего к меньшему)
        # 2) По штрафу за критичные элементы (от меньшего к большему)
        # 3) По количеству mismatched (от меньшего к большему)
        results.sort(key=lambda x: (-x['similarity'], x['penalty_score'], x['mismatched_count']))

        # Возвращаем топ 100 результатов для производительности
        return results[:100]

    def calculate_weighted_similarity(self,
                                     ref_composition: Dict[str, Any],
                                     candidate_composition: Dict[str, Any],
                                     tolerance_percent: float,
                                     steel_group: SteelGroup) -> Optional[float]:
        """
        Расчет похожести с использованием весов группы стали

        Args:
            ref_composition: Эталонный состав
            candidate_composition: Состав кандидата
            tolerance_percent: Допустимое отклонение (%)
            steel_group: Группа стали с весами элементов

        Returns:
            Similarity score (0-100) или None
        """
        # Парсинг составов
        ref_values = {e: self.parse_element_value(ref_composition.get(e))
                     for e in self.ELEMENTS}
        cand_values = {e: self.parse_element_value(candidate_composition.get(e))
                      for e in self.ELEMENTS}

        # Проверка обязательных элементов
        if ref_values.get('c') is None:
            return None

        total_weight = 0
        matched_weight = 0
        comparable_count = 0

        for element in self.ELEMENTS:
            ref_val = ref_values.get(element)
            cand_val = cand_values.get(element)

            # Пропускаем если хотя бы один отсутствует
            if ref_val is None or cand_val is None:
                continue

            comparable_count += 1

            # Получаем вес из группы стали
            weight = steel_group.get_element_weight(element)

            is_match, diff_percent = self.calculate_element_similarity(
                ref_val, cand_val, tolerance_percent
            )

            total_weight += weight

            if is_match:
                # Чем ближе к эталону, тем выше оценка
                element_score = (100 - diff_percent) / 100 * weight
                matched_weight += element_score

        if total_weight == 0:
            return None

        if comparable_count < self.MIN_COMPARABLE_ELEMENTS:
            return None

        return (matched_weight / total_weight) * 100

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
