#!/usr/bin/env python3
"""
input/ga4.csv + input/gsc.csv + input/expected_pv.csv を突合して
output/report.csv を生成する。
使い方: python3 src/main.py  または run.command をダブルクリック
"""

import csv
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def normalize(url):
    """URL を小文字・末尾スラッシュなしに統一する"""
    return url.strip().rstrip("/").lower()


def read_csv(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_index(rows, key_col):
    return {normalize(r[key_col]): r for r in rows if r.get(key_col)}


def main():
    # ── データ読み込み ─────────────────────────────────────────────────────────
    expected = build_index(
        read_csv(os.path.join(INPUT_DIR, "expected_pv.csv")), "article_url"
    )
    ga4 = build_index(read_csv(os.path.join(INPUT_DIR, "ga4.csv")), "url")
    gsc = build_index(read_csv(os.path.join(INPUT_DIR, "gsc.csv")), "url")

    if not expected:
        print("⚠  input/expected_pv.csv が見つかりません。")
        sys.exit(1)

    # ── 突合 ──────────────────────────────────────────────────────────────────
    out_rows = []
    for norm_url, exp in expected.items():
        g4 = ga4.get(norm_url, {})
        gs = gsc.get(norm_url, {})

        pv = int(g4.get("pv", 0))
        monthly_expected = int(exp.get("monthly_expected_pv", 0))
        pv_rate = round(pv / monthly_expected * 100, 1) if monthly_expected else ""

        period = g4.get("period_start", gs.get("period_start", ""))
        if period:
            period_end = g4.get("period_end", gs.get("period_end", ""))
            period = f"{period} ~ {period_end}"

        out_rows.append({
            "article_url": exp["article_url"],
            "monthly_expected_pv": monthly_expected,
            "pv": pv,
            "pv_rate_%": pv_rate,
            "active_users": int(g4.get("active_users", 0)),
            "avg_engagement_sec": g4.get("avg_engagement_sec", ""),
            "event_count": int(g4.get("event_count", 0)),
            "key_events": int(g4.get("key_events", 0)),
            "cta_clicks": int(g4.get("cta_clicks", 0)),
            "impressions": int(gs.get("impressions", 0)),
            "clicks": int(gs.get("clicks", 0)),
            "ctr_%": gs.get("ctr", ""),
            "position": gs.get("position", ""),
            "data_period": period,
        })

    # ── 出力 ──────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "report.csv")
    fieldnames = [
        "article_url", "monthly_expected_pv", "pv", "pv_rate_%",
        "active_users", "avg_engagement_sec", "event_count", "key_events", "cta_clicks",
        "impressions", "clicks", "ctr_%", "position", "data_period",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # ── サマリー表示 ──────────────────────────────────────────────────────────
    print(f"\n{'記事URL':<45} {'想定PV':>8} {'実PV':>8} {'達成率':>7}")
    print("-" * 72)
    for r in out_rows:
        rate = f"{r['pv_rate_%']}%" if r["pv_rate_%"] != "" else "  -"
        print(f"{r['article_url']:<45} {r['monthly_expected_pv']:>8,} "
              f"{r['pv']:>8,} {rate:>7}")
    print("-" * 72)
    total_exp = sum(r["monthly_expected_pv"] for r in out_rows)
    total_pv = sum(r["pv"] for r in out_rows)
    total_rate = round(total_pv / total_exp * 100, 1) if total_exp else 0
    print(f"{'合計':<45} {total_exp:>8,} {total_pv:>8,} {total_rate:>6}%")
    print(f"\n→ 保存: {out_path}  （{datetime.now().strftime('%Y-%m-%d %H:%M')}）")


if __name__ == "__main__":
    main()
