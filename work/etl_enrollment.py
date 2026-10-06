# /// script
# requires-python = ">=3.10"
# dependencies = ["xlrd"]
# ///
"""把 114-1 在學生人數統計表（.xls）轉成整齊的 CSV。"""
import csv
import re
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "東華大學統計資料" / "在學人數統計表"
OUT_PATH = ROOT / "work" / "enrollment_114-1.csv"

COLLEGE_COL, DEPT_COL, GROUP_COL, FEMALE_COL, MALE_COL = 1, 2, 3, 5, 6

SECTION_PROGRAM = [
    ("碩專班", "合計", "碩士在職專班"),
    ("博士班", "合計", "博士班"),
    ("碩士班", "合計", "碩士班"),
    ("學士班", "合計", "學士班"),
]

strip_paren = lambda s: re.sub(r"[（(].*?[）)]", "", s).strip()


def merge_map(sheet, col):
    """合併儲存格裡，col 這一欄每一列對應到的值（同一個合併範圍內的所有列都對應同一個值）。"""
    m = {}
    for rlo, rhi, clo, chi in sheet.merged_cells:
        if clo <= col < chi:
            value = sheet.cell_value(rlo, clo)
            for r in range(rlo, rhi):
                m[r] = value
    return m


def resolve_column(sheet, col, rows):
    """逐列解析合併儲存格的值：
    - 這一列本身在合併範圍內，或本身有值 -> 直接用（視為「有自己的值」）。
    - 這一列是空白、且不屬於任何合併範圍（報表留白的孤兒列，例如某一列忘了合併進上一格或下一格）
      -> 先沿用前一列的值；但如果緊接著的下一列「有自己的值」且跟目前沿用的值不同，
         代表這個孤兒列其實是下一個區塊的開頭被漏掉合併，改用下一列的值。
    """
    cell_merges = merge_map(sheet, col)
    own_value = {}
    for r in rows:
        own = sheet.cell_value(r, col)
        if r in cell_merges:
            own_value[r] = cell_merges[r]
        elif own != "":
            own_value[r] = own

    resolved = {}
    current = None
    for r in rows:
        if r in own_value:
            current = own_value[r]
        resolved[r] = current

    for i, r in enumerate(rows):
        if r in own_value:
            continue
        next_r = rows[i + 1] if i + 1 < len(rows) else None
        if next_r is not None and next_r in own_value and own_value[next_r] != resolved[r]:
            resolved[r] = own_value[next_r]

    return resolved


def cell_int(sheet, row, col):
    v = sheet.cell_value(row, col)
    return int(v) if v != "" else 0


def extract(path):
    wb = xlrd.open_workbook(path, formatting_info=True)
    sheet = wb.sheet_by_index(0)

    current_program = None
    data_rows = []
    row_program = {}
    for r in range(sheet.nrows):
        col0 = str(sheet.cell_value(r, 0)).strip()
        if col0.startswith("備註"):
            break
        is_section_header = False
        for keyword, marker, program in SECTION_PROGRAM:
            if keyword in col0 and marker in col0:
                current_program = program
                is_section_header = True
                break
        if is_section_header or current_program is None:
            continue
        data_rows.append(r)
        row_program[r] = current_program

    college_of = resolve_column(sheet, COLLEGE_COL, data_rows)
    dept_of = resolve_column(sheet, DEPT_COL, data_rows)

    totals = {}
    for r in data_rows:
        college = strip_paren(college_of[r])
        dept_raw = str(dept_of[r]).strip()
        program = row_program[r]
        female = cell_int(sheet, r, FEMALE_COL)
        male = cell_int(sheet, r, MALE_COL)
        for gender, count in (("女", female), ("男", male)):
            key = (college, dept_raw, program, gender)
            totals[key] = totals.get(key, 0) + count

    return totals


def main():
    src = sorted(SRC_DIR.glob("114-1*.xls"))[0]
    totals = extract(src)

    OUT_PATH.parent.mkdir(exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["college", "dept_raw", "program_raw", "gender", "count"])
        for (college, dept_raw, program, gender), count in sorted(totals.items()):
            writer.writerow([college, dept_raw, program, gender, count])

    print(f"來源：{src.name}")
    print(f"輸出：{OUT_PATH}（{len(totals)} 列）")


if __name__ == "__main__":
    main()
