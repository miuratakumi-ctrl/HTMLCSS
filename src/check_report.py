"""
output/report.csv をターミナルで見やすく表示するスクリプト
使い方: python src/check_report.py
"""

import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(BASE_DIR, "output", "report.csv")

# 表示する列と幅の定義（順番はそのまま report.csv と同じ）
DISPLAY_COLUMNS = [
    ("ランク",          4),
    ("article_url",    45),
    ("PV",              7),
    ("期待PV",          7),
    ("PV差分",          8),
    ("ペース比",        7),
    ("エンゲージ評価",   8),
    ("掲載順位",        6),
]


def truncate(text: str, width: int) -> str:
    """幅を超える文字列を末尾 … で切り詰める。"""
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "…"


def load_report() -> list[dict]:
    with open(REPORT_PATH, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def print_table(rows: list[dict]):
    header_parts = [truncate(col, w) for col, w in DISPLAY_COLUMNS]
    header = " | ".join(header_parts)
    separator = "-+-".join("-" * w for _, w in DISPLAY_COLUMNS)

    print(header)
    print(separator)
    for row in rows:
        parts = [truncate(str(row.get(col, "")), w) for col, w in DISPLAY_COLUMNS]
        print(" | ".join(parts))


def print_summary(rows: list[dict]):
    total = len(rows)
    over_pace = sum(1 for r in rows if r.get("ペース比", "") not in ("", "0") and float(r.get("ペース比", 0) or 0) >= 1.0)
    under_pace = total - over_pace

    print(f"\n合計: {total} 記事  /  ペース達成: {over_pace} 記事  /  未達: {under_pace} 記事")

    # ワースト3（ペース比が低い順）
    sortable = [r for r in rows if r.get("ペース比", "") not in ("", )]
    sortable.sort(key=lambda r: float(r.get("ペース比", 0) or 0))
    if sortable:
        print("\n── 要注意（ペース比ワースト）──")
        for r in sortable[:3]:
            url = r.get("article_url", "")
            pace = r.get("ペース比", "")
            pv = r.get("PV", "")
            epv = r.get("期待PV", "")
            print(f"  ランク{r.get('ランク','?')}  {url[:50]}  PV:{pv} / 期待:{epv}  ペース比:{pace}")


def main():
    print(f"=== レポート確認: {REPORT_PATH} ===\n")

    try:
        rows = load_report()
    except FileNotFoundError:
        print("[エラー] output/report.csv が見つかりません。")
        print("先に  python src/main.py  を実行してください。")
        return

    if not rows:
        print("[注意] report.csv は空です。main.py を実行してデータを生成してください。")
        return

    print_table(rows)
    print_summary(rows)
    print(f"\nファイルを直接開く場合: {REPORT_PATH}")
    print("  → Excel でダブルクリック、または Google スプレッドシートにインポート")


if __name__ == "__main__":
    main()
