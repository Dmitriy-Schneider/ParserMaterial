# CSV Import Errors - Fixed

**Date:** 2026-01-16
**Status:** ✅ FIXED

## Summary

Fixed critical errors in database from CSV imports:
1. Deleted 31 merged grades (both parts exist in DB)
2. Fixed 4 duplex steels analogues (25 → 255)
3. Fixed Standard for grade 255 (AISI 255, США)

**Database state:**
- Before: 10,083 grades
- After: 10,052 grades
- Deleted: 31 merged grades

---

## Problem 1: Merged Grades from CSV

### Issue
CSV files contained "merged" grades like `1.17301045` (should be `1.1730` + `1045`) where both parts already exist in the database as separate grades with links. These merged grades should never have been imported.

### Root Cause
CSV parsing didn't check if parts already exist before creating merged grades. Grades without links indicate CSV origin.

### Examples Found:
- `1.17301045` = `1.1730` + `1045` ✓ both exist
- `1.2063145Cr6` = `1.2063` + `145Cr6` ✓ both exist
- `1.2345H11` = `1.2345` + `H11` ✓ both exist
- `1.3345 ~ASP 2023` = `1.3345` + `ASP2023` ✓ both exist

### Solution
**Deleted 31 merged grades** where both parts exist:

#### Decimal + Digits Pattern (18 grades)
```
1.05351055    = 1.0535 + 1055
1.06011060    = 1.0601 + 1060
1.06031070    = 1.0603 + 1070
1.06051075    = 1.0605 + 1075
1.09049255    = 1.0904 + 9255
1.12031055    = 1.1203 + 1055
1.12211060    = 1.1221 + 1060
1.12311070    = 1.1231 + 1070
1.12481075    = 1.1248 + 1075
1.12691086    = 1.1269 + 1086
1.12741095    = 1.1274 + 1095
1.15201070    = 1.1520 + 1070
1.17301045    = 1.1730 + 1045 ⭐ (user reported)
1.210951100   = 1.2109 + 51100
1.350552100   = 1.3505 + 52100
1.50269255    = 1.5026 + 9255
1.65114340    = 1.6511 + 4340
1.71039254    = 1.7103 + 9254
```

#### Decimal + Alphanumeric Pattern (1 grade)
```
1.2063145Cr6  = 1.2063 + 145Cr6 ⭐ (user reported)
```

#### Decimal + Letter+Digits Pattern (9 grades)
```
1.2067L3      = 1.2067 + L3
1.2080D3      = 1.2080 + D3
1.2345H11     = 1.2345 + H11 ⭐ (user reported)
1.2363A2      = 1.2363 + A2
1.2378D7      = 1.2378 + D7
1.2519O7      = 1.2519 + O7
1.2550S1      = 1.2550 + S1
1.2825O1      = 1.2825 + O1
1.3302T15     = 1.3302 + T15
```

#### ASP Pattern (3 grades)
```
1.3241\n~ASP 2060  = 1.3241 + ASP2060
1.3244\n~ASP 2030  = 1.3244 + ASP2030
1.3345\n~ASP 2023  = 1.3345 + ASP2023 ⭐ (user reported)
```

---

## Problem 2: Wrong Analogue (25 vs 255)

### Issue
Duplex/super duplex stainless steels had `25` (carbon steel GOST 25) in analogues instead of `255` (AISI 255 duplex stainless).

**Grade 25:** Carbon steel, C=0.22-0.3%, Cr≤0.25%, Ni≤0.3%
**Grade 255:** Duplex stainless, C=0.04%, Cr=24-27%, Ni=4.5-6.5%, Mo=2.9-3.9%

### Examples Found:
- `1.4501` (DIN duplex): had `25` → fixed to `255` ⭐ (user reported)
- `1.4507` (DIN duplex): had `25` → fixed to `255` ⭐ (user reported)
- `S32506` (UNS duplex): had `25` → fixed to `255`
- `S32520` (UNS duplex): had `25` → fixed to `255`

### Solution
**Fixed 4 duplex steels:**
- Replaced ` 25 ` with ` 255 ` in analogues
- Only for duplex/super duplex steels (Cr > 20%, Ni < 15%)

**Before:**
```
1.4501: 25 S32520 S32760...
1.4507: 25 S32506 S32550...
```

**After:**
```
1.4501: 255 S32520 S32760...
1.4507: 255 S32506 S32550...
```

---

## Problem 3: Missing Standard for Grade 255

### Issue
Grade `255` (AISI 255 super duplex stainless) had `Standard: None`.

### Solution
**Fixed Standard:**
```
Before: None
After:  AISI 255, США
```

---

## Verification Results

### ✅ All Checks Passed

**1. Merged Grades Deleted:**
```
1.17301045      : DELETED (OK)
1.2063145Cr6    : DELETED (OK)
1.2345H11       : DELETED (OK)
1.3345 ~ASP 2023: DELETED (OK)
All others      : DELETED (OK)
```

**2. Duplex Steels Fixed:**
```
Grade   | Contains 255 | Contains 25 (error) | Status
--------|--------------|---------------------|-------
1.4501  | True         | False               | OK
1.4507  | True         | False               | OK
S32506  | True         | False               | OK
S32520  | True         | False               | OK
```

**3. Grade 255 Standard:**
```
Grade: 255
Standard: AISI 255, США
Status: OK
```

---

## Files Created

1. `utils/find_merged_grades_from_csv.py` - Find merged grades from CSV
2. `utils/check_grade_25_vs_255.py` - Analyze 25 vs 255 issue
3. `utils/fix_csv_import_errors.py` - **Main fix script**
4. `utils/verify_csv_fixes.py` - Verification script

---

## Implementation Details

### Pattern Matching for Merged Grades

```python
# Pattern 1: Decimal + digits
r'^(1\.\d{4})(\d+)$'
# Example: 1.17301045 → 1.1730 + 1045

# Pattern 2: Decimal + alphanumeric
r'^(1\.\d{4})(\d+[A-Za-z]\d*)$'
# Example: 1.2063145Cr6 → 1.2063 + 145Cr6

# Pattern 3: Decimal + letter+digits
r'^(1\.\d{4})([A-Z]\d+)$'
# Example: 1.2345H11 → 1.2345 + H11

# Pattern 4: ASP pattern
r'^([\d\.]+)\s*~?\s*(ASP\s+\d+)$'
# Example: 1.3345 ~ASP 2023 → 1.3345 + ASP2023
```

### Duplex Steel Detection

```python
cr_val > 20 and ni_val < 15
# Duplex typically: Cr 20-28%, Ni 3-8%
```

### Analogue Replacement

```python
# Safe replacement avoiding partial matches
if analogues.startswith('25 '):
    new_analogues = '255 ' + new_analogues[3:]
if ' 25 ' in new_analogues:
    new_analogues = new_analogues.replace(' 25 ', ' 255 ')
if new_analogues.endswith(' 25'):
    new_analogues = new_analogues[:-3] + ' 255'
```

---

## Database Changes

**Summary:**
- Deleted: 31 grades
- Updated: 4 grades (analogues)
- Updated: 1 grade (standard)
- Total grades: 10,052 (was 10,083)

**Docker container rebuilt:** ✅

---

## Prevention

To prevent similar issues in future CSV imports:

1. **Check for existing parts** before creating merged grades
2. **Validate analogues** - ensure duplex steels don't reference carbon steels
3. **Set Standard** for all grades during import
4. **Link validation** - grades from official sources should have links

---

**Completed:** 2026-01-16
**Status:** ✅ ALL FIXES VERIFIED
