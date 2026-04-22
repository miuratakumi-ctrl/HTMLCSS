#!/usr/bin/env python3
"""
SEO Auto - メインスクリプト
使い方: run.command をダブルクリック、または python3 src/main.py
入力ファイルは input/ に置いてください。出力は output/ に書き出されます。
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def main():
    print("=== SEO Auto ===")
    print(f"入力フォルダ : {INPUT_DIR}")
    print(f"出力フォルダ : {OUTPUT_DIR}")

    files = [f for f in os.listdir(INPUT_DIR) if not f.startswith(".")]
    if not files:
        print("\n⚠  input/ にファイルがありません。処理するファイルを置いてから再実行してください。")
        sys.exit(0)

    print(f"\n対象ファイル ({len(files)} 件):")
    for f in files:
        print(f"  - {f}")

    # ここに SEO 処理ロジックを追加してください


if __name__ == "__main__":
    main()
