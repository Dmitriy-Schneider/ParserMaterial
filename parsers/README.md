# Parsers for Steel Grade Database

This directory contains parsers for various steel grade databases and marochnik websites.

## Available Parsers

### splav_kharkov_advanced.py
**Status:** ✅ Production Ready
**Source:** https://www.splav-kharkov.com
**Coverage:** 27 material types (10,394+ grades)

Comprehensive scraper for Russian marochnik splav-kharkov.com

**Material Types:**
1. Heat-resistant steel and alloys
2. Precision alloys
3. Structural steel
4. Tool steel
5. Steel for castings
6. Corrosion-resistant steel and alloys
7. **Cast iron (Чугун)** - 122 grades including ЧНХМДШ
8. Special-purpose steel
9. Bronze
10. Brass
11. Aluminum and aluminum alloys
12. Copper and copper alloys
13. Electrical steel
14. Nickel and nickel alloys
15. Zinc, Magnesium, Titanium, Tin, Lead alloys
16-27. Precious metals, powder metallurgy, welding materials

**Features:**
- ✅ Smart duplicate detection (checks existing DB)
- ✅ Handles multiple URL structures (direct & class-based)
- ✅ Extracts chemical composition, analogues, standards
- ✅ Rate limiting (1s per grade, 2s per class)
- ✅ Comprehensive logging
- ✅ Statistics tracking

**Usage:**

```bash
# Parse all material types
python parsers/splav_kharkov_advanced.py

# Parse cast iron only (type_id=7)
python parsers/splav_kharkov_advanced.py --cast-iron-only

# Test mode (5 grades per class)
python parsers/splav_kharkov_advanced.py --test

# Specific types (e.g., structural steel, tool steel, stainless)
python parsers/splav_kharkov_advanced.py --type-ids 3 4 6

# Single type
python parsers/splav_kharkov_advanced.py --type-ids 1
```

**Command Line Options:**
- `--type-ids 1 2 3` - Parse specific material types
- `--cast-iron-only` - Parse only cast iron (type_id=7)
- `--test` - Test mode: limit to 5 grades per class

**Output:**
- Logs to: `splav_kharkov_advanced.log`
- Statistics: grades found/added/skipped/errors
- Database: Updates `steel_grades.db` automatically

**Example Output:**
```
================================================================================
Processing type_id=7: Cast iron
================================================================================
Found 1 classes for type_id=7 (Cast iron)

Processing class_id=-1: Cast iron (direct)
Found 0 new grades to process

================================================================================
PARSING STATISTICS
================================================================================
Total grades found:     0
New grades added:       0
Analogues updated:      0
Skipped (existing):     122
Errors:                 0
================================================================================
```

---

## Development

### Adding New Parsers

Create a new parser file following this template:

```python
"""Parser for <website>"""
import requests
from bs4 import BeautifulSoup
from database_schema import get_connection

class MyParser:
    def __init__(self, db_path='steel_grades.db'):
        self.db_path = db_path
        # Load existing grades to avoid duplicates
        self.load_existing_grades()

    def load_existing_grades(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT grade FROM steel_grades")
        self.existing_grades = {row[0] for row in cursor.fetchall()}
        conn.close()

    def parse_grade(self, url):
        # Extract composition, analogues, standard
        pass

    def insert_grade(self, grade_data):
        # Check duplicates before insert
        if grade_data['grade'] in self.existing_grades:
            return False
        # Insert to DB
        pass
```

### Testing New Parsers

1. Test on small subset first: `python parser.py --test`
2. Check logs for errors
3. Verify no duplicates: `SELECT grade, COUNT(*) FROM steel_grades GROUP BY grade HAVING COUNT(*) > 1`
4. Run full scrape: `python parser.py`

---

## Database Schema

Parsers should populate these fields:

```sql
CREATE TABLE steel_grades (
    grade TEXT PRIMARY KEY,
    standard TEXT,
    c TEXT, cr TEXT, ni TEXT, mo TEXT,
    v TEXT, w TEXT, co TEXT, mn TEXT,
    si TEXT, cu TEXT, nb TEXT, n TEXT,
    s TEXT, p TEXT,
    analogues TEXT,
    link TEXT,
    manufacturer TEXT,
    base TEXT,
    tech TEXT
)
```

**Required Fields:**
- `grade` - Material designation (e.g., "ЧНХМДШ", "AISI 304")
- `standard` - Standard/specification (e.g., "GOST", "ASTM")

**Chemical Composition Fields:**
- Support ranges: "0.17 - 0.24"
- Support max values: "до 0.08" (up to 0.08)
- Handle HTML entities: "до &nbsp; 1" → "до 1"

**Optional Fields:**
- `analogues` - Space-separated list of equivalent grades
- `link` - Source URL
- `manufacturer` - Material manufacturer

---

## Performance Tips

1. **Rate Limiting**: Add delays to avoid overwhelming servers
   ```python
   import time
   time.sleep(1)  # 1 second between requests
   ```

2. **Duplicate Prevention**: Load existing grades at startup
   ```python
   existing_grades = set(cursor.fetchall())
   if grade in existing_grades:
       continue
   ```

3. **Batch Processing**: Commit after N grades, not after each
   ```python
   for i, grade in enumerate(grades):
       insert_grade(grade)
       if i % 100 == 0:
           conn.commit()
   ```

4. **Error Recovery**: Log errors but continue parsing
   ```python
   try:
       parse_grade(url)
   except Exception as e:
       logging.error(f"Failed {url}: {e}")
       continue  # Don't stop entire scrape
   ```

---

## Status

| Parser | Status | Grades | Last Updated |
|--------|--------|--------|--------------|
| splav_kharkov_advanced.py | ✅ Active | 10,394+ | 2026-01-15 |

**Database Health:**
- Total grades: 10,394
- Cast iron grades: 122
- Zero duplicates
- All parsers use duplicate prevention

---

## Notes

- Always test parsers with `--test` flag first
- Monitor logs for encoding issues (HTML entities, Cyrillic text)
- Respect website rate limits (1-2 seconds per request)
- Update existing analogues instead of skipping
