#!/usr/bin/env python3
"""
使い方: run.command をダブルクリック、または python3 src/main.py
input/ に CSV を置いてください。output/ に結果が出ます。
"""

import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def process(input_path, output_path):
    rows = []
    with open(input_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "article_url": row["article_url"],
                "monthly_expected_pv": int(row["monthly_expected_pv"]),
            })

    total = sum(r["monthly_expected_pv"] for r in rows)

    print(f"\n{'URL':<45} {'月間想定PV':>12}")
    print("-" * 58)
    for r in rows:
        print(f"{r['article_url']:<45} {r['monthly_expected_pv']:>12,}")
    print("-" * 58)
    print(f"{'合計':<45} {total:>12,}")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["article_url", "monthly_expected_pv"])
        writer.writeheader()
        writer.writerows(rows)
        f.write(f"\n合計,{total}\n")

    print(f"\n→ 保存しました: {output_path}")


def main():
    csv_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".csv")]
    if not csv_files:
        print("⚠  input/ に CSV ファイルがありません。")
        sys.exit(0)

    for filename in csv_files:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)
        print(f"処理中: {filename}")
        process(input_path, output_path)


if __name__ == "__main__":
    main()
