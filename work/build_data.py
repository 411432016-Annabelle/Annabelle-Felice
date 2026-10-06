# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""把 data/ 裡的三份標準 CSV 整理、加總成網頁可以直接 <script src> 載入的 docs/data.js。"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = ROOT / "docs" / "data.js"


def build_enrollment():
    df = pd.read_csv(DATA_DIR / "enrollment.csv", encoding="utf-8-sig")
    keep = ["semester", "college", "dept", "degree", "gender"]
    agg = df.groupby(keep, as_index=False)["count"].sum()
    agg["count"] = agg["count"].astype(int)
    return agg.to_dict(orient="records")


def build_leave():
    df = pd.read_csv(DATA_DIR / "leave.csv", encoding="utf-8-sig")
    keep = ["semester", "college", "dept", "degree", "gender", "reason"]
    agg = df.groupby(keep, as_index=False)[["new_leave", "on_leave_end"]].sum()
    agg["new_leave"] = agg["new_leave"].astype(int)
    agg["on_leave_end"] = agg["on_leave_end"].astype(int)
    return agg.to_dict(orient="records")


def build_dept_aliases():
    df = pd.read_csv(DATA_DIR / "dept_mapping.csv", encoding="utf-8-sig")
    records = []
    for row in df.itertuples(index=False):
        aliases_raw = "" if pd.isna(row.aliases) else str(row.aliases)
        aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()]
        records.append({"dept": row.dept, "college": row.college, "aliases": aliases})
    return records


def main():
    enrollment = build_enrollment()
    leave = build_leave()
    dept_aliases = build_dept_aliases()

    check_114_1 = sum(r["count"] for r in enrollment if r["semester"] == "114-1")
    print(f"核對：114-1 在學人數合計 = {check_114_1}（應為 10035）")
    assert check_114_1 == 10035, f"114-1 在學人數合計不是 10035，是 {check_114_1}"

    OUT_PATH.parent.mkdir(exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        f.write("// 由 work/build_data.py 從 data/ 裡的標準 CSV 產生，請不要手動修改。\n")
        f.write(f"const ENROLLMENT = {json.dumps(enrollment, ensure_ascii=False)};\n")
        f.write(f"const LEAVE = {json.dumps(leave, ensure_ascii=False)};\n")
        f.write(f"const DEPT_ALIASES = {json.dumps(dept_aliases, ensure_ascii=False)};\n")

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"輸出：{OUT_PATH}")
    print(f"ENROLLMENT：{len(enrollment)} 列，LEAVE：{len(leave)} 列，DEPT_ALIASES：{len(dept_aliases)} 列")
    print(f"檔案大小：{size_kb:.1f} KB")


if __name__ == "__main__":
    main()
