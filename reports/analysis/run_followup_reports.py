from pathlib import Path
import re

import pandas as pd

OUTPUT_DIR = Path('reports/analysis')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

master_csv = OUTPUT_DIR / 'master_grades_review.csv'
zknives_csv = OUTPUT_DIR / 'zknives_standard_review.csv'
csv_unique_csv = OUTPUT_DIR / 'csv_unique_grades.csv'


def read_csv(path):
    return pd.read_csv(path, sep=';', dtype=str, keep_default_na=False)


master_df = read_csv(master_csv)
zknives_df = read_csv(zknives_csv)
csv_unique_df = read_csv(csv_unique_csv)

# Excel outputs
master_df.to_excel(OUTPUT_DIR / 'master_grades_review.xlsx', index=False)
zknives_df.to_excel(OUTPUT_DIR / 'zknives_standard_review.xlsx', index=False)

# Standard corrections: ZKnives
zknives_df['expected_standard'] = zknives_df['expected_standard'].fillna('')
zknives_df['status'] = zknives_df['status'].fillna('')
errors_df = zknives_df[
    (zknives_df['expected_standard'].str.strip() != '') &
    (zknives_df['status'].isin(['placeholder', 'mismatch', 'missing_db']))
].copy()

errors_df.to_excel(OUTPUT_DIR / 'zknives_standard_errors.xlsx', index=False)

zknives_cols = [
    'grade', 'link', 'db_standard', 'expected_standard', 'standard_expected_source',
    'cc', 'country_cc', 'country_card', 'maker_card', 'maker_table', 'status'
]

for col in zknives_cols:
    if col not in errors_df.columns:
        errors_df[col] = ''

errors_df[zknives_cols].to_csv(
    OUTPUT_DIR / 'standard_corrections_zknives.csv',
    sep=';',
    index=False
)

# Standard corrections: CSV unique (only grades not in splav/zknives)
csv_cols = ['grade', 'standard', 'manufacturer', 'country', 'source']
for col in csv_cols:
    if col not in csv_unique_df.columns:
        csv_unique_df[col] = ''

csv_unique_df[csv_cols].to_csv(
    OUTPUT_DIR / 'standard_corrections_csv_unique.csv',
    sep=';',
    index=False
)

missing_std_df = csv_unique_df[csv_unique_df['standard'].str.strip() == '']
missing_std_df[csv_cols].to_csv(
    OUTPUT_DIR / 'standard_corrections_csv_unique_missing.csv',
    sep=';',
    index=False
)

# Chemistry format issues
range_re = re.compile(r'\d\s*-\s*\d')
qual_re = re.compile(
    r'(?:\b\u0434\u043e\b|\bmin\b|\bmax\b|\b\u043c\u0438\u043d\b|'
    r'\b\u043c\u0430\u043a\u0441\b|\b\u043d\u0435 \u0431\u043e\u043b\u0435\u0435\b|'
    r'<=|>=|<|>)',
    re.IGNORECASE
)
comma_re = re.compile(r',')

issue_rows = []

columns = list(master_df.columns)

for row in master_df.itertuples(index=False, name=None):
    data = dict(zip(columns, row))
    source = (data.get('primary_source') or '').strip()
    grade = (data.get('grade_raw') or data.get('grade_norm') or '').strip()
    link = (data.get('link') or '').strip()
    for element in ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n', 'tech']:
        value = (data.get(element) or '').strip()
        if not value:
            continue
        if range_re.search(value):
            issue_rows.append({
                'grade': grade,
                'source': source,
                'link': link,
                'element': element,
                'value': value,
                'issue_type': 'range'
            })
        if qual_re.search(value):
            issue_rows.append({
                'grade': grade,
                'source': source,
                'link': link,
                'element': element,
                'value': value,
                'issue_type': 'qualifier'
            })
        if comma_re.search(value):
            issue_rows.append({
                'grade': grade,
                'source': source,
                'link': link,
                'element': element,
                'value': value,
                'issue_type': 'comma'
            })

issues_df = pd.DataFrame(issue_rows)
issues_df.to_csv(OUTPUT_DIR / 'chemistry_format_issues_all.csv', sep=';', index=False)

splav_issues = issues_df[issues_df['source'] == 'splav']
splav_issues.to_csv(OUTPUT_DIR / 'chemistry_format_issues_splav.csv', sep=';', index=False)

summary = issues_df.groupby(['source', 'issue_type']).size().reset_index(name='count')
summary.to_csv(OUTPUT_DIR / 'chemistry_format_summary.csv', sep=';', index=False)

splav_elem_summary = splav_issues.groupby(['element', 'issue_type']).size().reset_index(name='count')
splav_elem_summary.to_csv(OUTPUT_DIR / 'chemistry_format_summary_splav_elements.csv', sep=';', index=False)

print('[OK] Follow-up reports generated')
