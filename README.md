# ParserSteel - Steel Grade Database & Similarity Search System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production-success.svg)

**Интеллектуальная система поиска аналогов марок стали по химическому составу**

[Возможности](#-возможности) •
[Демо](#-демо) •
[Установка](#-установка) •
[API](#-api) •
[Технологии](#-технологии) •
[Архитектура](#-архитектура)

</div>

---

## 📋 О проекте

**ParserSteel** — это полнофункциональная система для работы с базой данных марок сталей и сплавов. Система позволяет искать аналоги материалов по химическому составу с использованием интеллектуального алгоритма классификации, учитывающего специфику различных групп сталей.

### Проблема
Поиск аналогов марок стали — сложная задача для инженеров и металлургов. Разные стандарты (ГОСТ, DIN, AISI, JIS), различные системы наименований, отсутствие единой базы данных. Существующие решения (Stahlschluessel) дорогие и не учитывают специфику материалов.

### Решение
ParserSteel использует **гибридный алгоритм Smart Fuzzy Search**, который:
- Автоматически классифицирует сталь по химсоставу (28 групп)
- Учитывает значимость элементов для каждого типа стали
- Защищает критичные элементы от "прощения" при поиске
- Интегрируется с AI (GPT) для интеллектуального поиска

---

## 🎯 Возможности

### Поиск марок стали
- **Точный поиск** по названию марки (с поддержкой кириллицы и латиницы)
- **AI-поиск** — интеллектуальный поиск через GPT с пониманием контекста
- **Perplexity Search** — поиск неизвестных марок в открытых интернет-источниках
- **Fuzzy Search (Similar)** — поиск аналогов по химическому составу

### Smart Fuzzy Search
- **28 групп классификации** сталей (инструментальные, нержавеющие, конструкционные и др.)
- **Веса элементов** — для каждой группы определена значимость химических элементов (0-10)
- **Защита критичных элементов** — C, Cr, Mo, V с весом ≥8 не "прощаются" при поиске
- **Настраиваемые параметры**: Tolerance (допуск %) и Max Mismatched (макс. несовпадений)

### Telegram Bot
- Полная интеграция с веб-интерфейсом
- Поиск марок, аналогов, сравнение составов
- Fuzzy Search с теми же алгоритмами

### База данных
- **10,000+ марок** сталей и сплавов
- Источники: ГОСТ, DIN/EN, AISI, JIS, китайские стандарты
- Полный химический состав (15 элементов)
- Аналоги, стандарты, производители, ссылки на источники

---

## 📸 Демо

### Главный экран — веб-интерфейс
<!-- TODO: Сделать скриншот главной страницы -->
![Главный экран](docs/images/web_main.png)

### Поиск марок стали
| Поиск по названию | Результаты поиска |
|:---:|:---:|
| ![Поиск](docs/images/search_input.png) | ![Результаты](docs/images/search_results.png) |

### Smart Fuzzy Search (Similar)
| Настройка параметров поиска | Результаты с классификацией |
|:---:|:---:|
| ![Similar настройки](docs/images/similar_settings.png) | ![Similar результаты](docs/images/similar_results.png) |

### AI-поиск
| AI запрос | AI ответ |
|:---:|:---:|
| ![AI поиск](docs/images/ai_search.png) | ![AI результат](docs/images/ai_result.png) |

### Telegram Bot
| Поиск марки | Аналоги | Сравнение |
|:---:|:---:|:---:|
| ![Bot поиск](docs/images/bot_search.png) | ![Bot аналоги](docs/images/bot_analogues.png) | ![Bot сравнение](docs/images/bot_compare.png) |

---

## 🧠 Алгоритм Smart Fuzzy Search

### Классификация сталей

Система автоматически определяет тип стали по химическому составу:

```
┌─────────────────────────────────────────────────────────────────┐
│                    КЛАССИФИКАЦИЯ СТАЛИ                          │
├─────────────────────────────────────────────────────────────────┤
│  Химический состав  ──►  Правила классификации  ──►  Группа    │
│                                                                 │
│  C=1.55, Cr=12, Mo=0.8, V=0.9  ──►  COLD_WORK_TOOL             │
│  C=0.4, Cr=5, Mo=1.3, V=1.0    ──►  HOT_WORK_TOOL              │
│  C=0.85, W=6, Mo=5, V=2, Co=5  ──►  HSS_HIGH_SPEED             │
│  Cr=18, Ni=10, Mo=2            ──►  STAINLESS_AUSTENITIC       │
└─────────────────────────────────────────────────────────────────┘
```

### Веса элементов по группам

| Группа | C | Cr | Mo | V | W | Ni | Критичные |
|--------|---|----|----|---|---|----|-----------|
| Cold Work Tool | 10 | 10 | 8 | 9 | 7 | 3 | C, Cr, V, Mo |
| Hot Work Tool | 7 | 10 | 10 | 9 | 8 | 7 | Cr, Mo, V, W |
| HSS | 8 | 5 | 10 | 9 | 10 | 2 | W, Mo, V, Co |
| Stainless Aust. | 5 | 10 | 9 | 2 | 2 | 10 | Cr, Ni, Mo |

### Логика Smart Mismatched

```python
# Критичные элементы (вес >= 8) защищены от "прощения"
CRITICAL_WEIGHT_THRESHOLD = 8

# Пример: поиск аналогов для Х12МФ (C=1.55, Cr=12, Mo=0.5, V=0.3)
# Группа: COLD_WORK_TOOL
# Критичные элементы: C(10), Cr(10), V(9), Mo(8)

# 9X5ВФ (C=0.9, Cr=5.5) — ОТКЛОНЁН
# Причина: C и Cr (критичные) не совпадают

# 1.2379 (C=1.55, Cr=12, Mo=0.7, V=0.9) — ПРИНЯТ
# Причина: критичные элементы в пределах допуска
```

---

## 🛠 Технологии

### Backend
| Технология | Назначение |
|------------|------------|
| **Python 3.11+** | Основной язык |
| **Flask** | REST API фреймворк |
| **SQLite** | База данных |
| **OpenAI GPT** | AI-поиск с пониманием контекста |
| **Perplexity API** | Поиск неизвестных марок в открытых источниках |
| **python-telegram-bot** | Telegram Bot API |

### Frontend
| Технология | Назначение |
|------------|------------|
| **HTML5/CSS3** | Разметка и стили |
| **JavaScript (ES6+)** | Логика интерфейса |
| **Bootstrap** | UI компоненты |

### DevOps
| Технология | Назначение |
|------------|------------|
| **Docker** | Контейнеризация |
| **Docker Compose** | Оркестрация сервисов |

### Ключевые модули
| Модуль | Описание |
|--------|----------|
| `fuzzy_search.py` | Smart Fuzzy Search с классификацией (28 групп) |
| `ai_search.py` | Интеграция с GPT + Perplexity API для поиска |
| `config/element_weights.csv` | Веса элементов для 28 групп сталей |

---

## 📦 Установка

### Требования
- Python 3.11+
- Docker & Docker Compose (опционально)
- OpenAI API Key (для AI-поиска)
- Telegram Bot Token (для бота)

### Вариант 1: Docker (рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Dmitriy-Schneider/ParserMaterial.git
cd ParserMaterial

# 2. Создайте .env файл
cp .env.example .env
# Отредактируйте .env — добавьте API ключи

# 3. Запустите контейнеры
docker-compose up -d

# Веб-интерфейс: http://localhost:5001
# Telegram Bot: активен автоматически
```

### Вариант 2: Локальная установка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/Dmitriy-Schneider/ParserMaterial.git
cd ParserMaterial

# 2. Создайте виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Создайте .env файл
cp .env.example .env

# 5. Запустите приложение
python app.py
```

### Конфигурация (.env)

```env
# OpenAI для AI-поиска
OPENAI_API_KEY=sk-...

# Perplexity для поиска неизвестных марок
PERPLEXITY_API_KEY=pplx-...

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC...

# Flask
FLASK_ENV=production
FLASK_PORT=5000
```

### База данных

> **Важно:** База данных **не предоставляется** в этом репозитории.

База данных является **интеллектуальной собственностью автора** и была собрана путем парсинга и обработки данных из открытых источников:
- Справочники по металлургии (splav-kharkov.com, zknives.com и др.)
- Стандарты ГОСТ, DIN/EN, AISI, JIS, GB
- Технические каталоги производителей

На данный момент база содержит **~10,000 марок** сталей и сплавов с полным химическим составом.

**Для создания собственной базы данных:**
1. Используйте схему из `database_schema.py`
2. Импортируйте данные из ваших источников
3. Применяйте парсеры для сбора информации

---

## 🚀 Использование

### Веб-интерфейс

1. Откройте http://localhost:5001
2. **Search** — поиск по названию марки
3. **AI Search** — интеллектуальный поиск (например: "аналог D2 для ножей")
4. **Similar** — поиск аналогов по химсоставу с настройками:
   - **Tolerance** (10-90%) — допустимое отклонение элементов
   - **Max Mismatched** (1-10) — максимум несовпадающих элементов

### Telegram Bot

```
/start — Начало работы
/search Х12МФ — Поиск марки
/similar Х12МФ — Аналоги по составу
/compare Х12МФ D2 — Сравнение марок
/help — Справка
```

---

## 🔌 API

### Основные endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/steels/search?q={query}` | Поиск марки |
| `POST` | `/api/steels/ai-search` | AI-поиск |
| `POST` | `/api/steels/fuzzy-search` | Smart Fuzzy Search |
| `GET` | `/api/steels/{grade}` | Детали марки |
| `GET` | `/api/steels/{grade}/analogues` | Аналоги марки |

### Пример: Fuzzy Search

```bash
curl -X POST http://localhost:5001/api/steels/fuzzy-search \
  -H "Content-Type: application/json" \
  -d '{
    "grade_data": {
      "grade": "Х12МФ",
      "c": "1.55",
      "cr": "12.0",
      "mo": "0.5",
      "v": "0.3"
    },
    "tolerance_percent": 30,
    "max_mismatched_elements": 3,
    "smart_mode": true
  }'
```

### Ответ

```json
{
  "results": [
    {
      "grade": "1.2379",
      "similarity": 95.2,
      "mismatched_count": 1,
      "steel_group": "COLD_WORK_TOOL",
      "steel_group_name": "Холодноштамповые",
      "c": "1.55",
      "cr": "12.0",
      "mo": "0.7",
      "v": "0.9",
      "standard": "DIN"
    }
  ],
  "reference_steel_group": "COLD_WORK_TOOL",
  "reference_steel_group_name": "Холодноштамповые"
}
```

---

## 📁 Структура проекта

```
ParserMaterial/
├── app.py                    # Flask приложение
├── ai_search.py              # AI поиск (GPT интеграция)
├── fuzzy_search.py           # Smart Fuzzy Search алгоритм
├── config.py                 # Конфигурация
├── database_schema.py        # Схема БД
│
├── config/
│   └── element_weights.csv   # Веса элементов (28 групп)
│
├── database/
│   ├── steel_database.db     # SQLite база (не в репо)
│   └── backup_manager.py     # Менеджер бэкапов
│
├── telegram_bot/
│   ├── bot.py                # Telegram бот
│   ├── config.py
│   ├── Dockerfile
│   └── handlers/
│       ├── search.py
│       ├── fuzzy_search.py
│       ├── analogues.py
│       └── compare.py
│
├── templates/
│   └── index.html            # Веб-интерфейс
│
├── static/
│   ├── logo_blue.svg
│   └── logo_white.svg
│
├── docs/
│   └── DEPLOYMENT_GUIDE.md   # Руководство по развертыванию
│
├── docker-compose.yml        # Docker оркестрация
├── Dockerfile                # Docker образ
├── requirements.txt          # Python зависимости
└── .env.example              # Пример конфигурации
```

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТЫ                                 │
├──────────────────┬──────────────────┬───────────────────────────┤
│   Веб-браузер    │   Telegram Bot   │        API клиенты        │
└────────┬─────────┴────────┬─────────┴─────────────┬─────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOCKER NETWORK                             │
├─────────────────────────────┬───────────────────────────────────┤
│     steel-parser:5000       │      telegram-bot                 │
│     (Flask REST API)        │      (python-telegram-bot)        │
├─────────────────────────────┴───────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  ai_search  │  │fuzzy_search │  │   element_weights.csv   │  │
│  │ GPT+Perplx  │  │  (Smart)    │  │   (28 групп сталей)     │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
│         ▼                ▼                     ▼                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              SQLite: steel_database.db                      ││
│  │              (10,000+ марок сталей)                         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Группы классификации сталей

| ID | Название (RU) | Название (EN) | Критичные элементы |
|----|---------------|---------------|-------------------|
| COLD_WORK_TOOL | Холодноштамповые | Cold Work Tool Steel | C, Cr, V, Mo |
| HOT_WORK_TOOL | Горячештамповые | Hot Work Tool Steel | Mo, Cr, V, W |
| HSS_HIGH_SPEED | Быстрорежущие | High Speed Steel | W, Mo, V, Co |
| PLASTIC_MOLD | Для пресс-форм | Plastic Mold Steel | Cr, Mo |
| STAINLESS_AUSTENITIC | Нержавеющие аустенитные | Austenitic Stainless | Cr, Ni, Mo |
| STAINLESS_MARTENSITIC | Нержавеющие мартенситные | Martensitic Stainless | C, Cr |
| STAINLESS_DUPLEX | Дуплексные | Duplex Stainless | Cr, Ni, Mo, N |
| BEARING_STEEL | Подшипниковые | Bearing Steel | C, Cr |
| SPRING_STEEL | Пружинные | Spring Steel | C, Si, Mn |
| NICKEL_SUPERALLOY | Жаропрочные никелевые | Nickel Superalloy | Ni, Cr, Mo, Co |
| CARBON_STEEL | Углеродистые | Carbon Steel | C |
| ALLOY_STRUCTURAL | Конструкционные | Alloy Structural | C, Cr, Ni, Mo |

*Полный список: 28 групп включая цветные металлы (медные, алюминиевые, титановые сплавы)*

---

## 🔒 Безопасность и интеллектуальная собственность

- API ключи хранятся в `.env` (не в репозитории)
- **База данных (~10,000 марок) является интеллектуальной собственностью** автора и не публикуется
- База собрана из открытых источников и представляет результат значительной работы по парсингу, нормализации и верификации данных
- Docker изоляция сервисов
- Валидация входных данных

---

## 🛣 Roadmap

- [x] Smart Fuzzy Search с классификацией
- [x] Telegram Bot интеграция
- [x] Docker deployment
- [x] AI-поиск (GPT)
- [ ] Авторизация пользователей
- [ ] История поисков
- [ ] Экспорт результатов (Excel, PDF)
- [ ] REST API документация (Swagger)

---

## 🤝 Contributing

Contributions приветствуются!

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📝 Лицензия

Распространяется под лицензией MIT. См. файл [LICENSE](LICENSE).

---

## 👤 Автор

**Dmitriy Schneider**

- GitHub: [@Dmitriy-Schneider](https://github.com/Dmitriy-Schneider)

---

<div align="center">

⭐ Если проект был полезен, поставьте звезду!

**ParserSteel** — интеллектуальный поиск аналогов марок стали

</div>
