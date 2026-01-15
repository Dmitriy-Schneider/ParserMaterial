# Database Migrations

This directory contains database migration scripts to track changes to the steel_grades database.

## Migration List

### 001_remove_registered_symbol.sql
**Date:** 2026-01-15
**Status:** ✅ Applied
**Description:** Remove ® (registered trademark) symbol from all grade names

**Reason:**
- Users can't easily type ® symbol, especially in Telegram bot
- Improves search usability
- Makes grade names consistent

**Affected Records:** 15 grades
- AL-6XN, Nimonic 75/80A/90, Nitronic 50
- Alleima 253 MA/2RE10/2RE69/353 MA/3RE60
- E-BRITE, SEA-CURE, SHOMAC 30-2
- Safurex, Sanicro 25

**Testing:**
```bash
# Before: Search for "Nimonic 75" → NOT FOUND
# After:  Search for "Nimonic 75" → FOUND ✓

curl "http://localhost:5001/api/steels?grade=Nimonic%2075&exact=true"
```

## How to Apply Migrations

### Manual (SQLite)
```bash
sqlite3 steel_grades.db < migrations/001_remove_registered_symbol.sql
```

### In Docker Container
```bash
# Copy updated database to container
docker cp steel_grades.db parser-steel-app:/app/steel_grades.db
docker restart parser-steel-app
```

## Migration Status

| Migration | Date | Status | Description |
|-----------|------|--------|-------------|
| 001 | 2026-01-15 | ✅ Applied | Remove ® from grade names |

---

**Note:** Database file (steel_grades.db) is excluded from git (.gitignore).
Migrations are documented here for reproducibility and tracking.
