#!/usr/bin/env python3
"""
指定した1日分の GA4 + GSC データを取得してレポートを生成する。

使い方:
  python3 src/daily_report.py --date 2026-05-06
  python3 src/daily_report.py              # 昨日分
"""

import argparse
import csv
import os
import sys
from datetime import date, datetime, timedelta

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
INPUT_DIR  = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_FIELDNAMES = [
    "article_url", "PV", "アクティブユーザー", "平均エンゲージメント（秒）", "エンゲージ評価",
    "イベント数", "キーイベント", "CTAクリック数",
    "インプレッション", "記事クリック数", "記事CTR%", "掲載順位",
]


def normalize(u): return u.strip().rstrip("/").lower()


def grade(s):
    try: v = float(s)
    except: return "-"
    return "S" if v >= 180 else "A" if v >= 120 else "B" if v >= 60 else "C" if v >= 30 else "D"


def main():
    parser = argparse.ArgumentParser(description="1日分PV集計レポート")
    parser.add_argument("--date", help="集計日 YYYY-MM-DD（省略時は昨日）")
    args = parser.parse_args()

    target = (
        date.fromisoformat(args.date) if args.date
        else date.today() - timedelta(days=1)
    )

    # ── APIからデータ取得 ──────────────────────────────────────────────────────
    from _config import load_config
    import fetch_ga4
    import fetch_gsc

    config = load_config()
    print(f"📥 {target} のデータを取得中...")
    fetch_ga4.fetch(config, target_date=target)
    fetch_gsc.fetch(config, target_date=target)

    # ── CSV 読み込み ───────────────────────────────────────────────────────────
    def read_idx(path, key):
        if not os.path.exists(path): return {}
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return {normalize(r[key]): r for r in rows if r.get(key)}

    ga4 = read_idx(os.path.join(INPUT_DIR, "ga4.csv"), "url")
    gsc = read_idx(os.path.join(INPUT_DIR, "gsc.csv"), "url")

    # ── 記事リストで絞り込み ──────────────────────────────────────────────────
    alp = os.path.join(INPUT_DIR, "article_list.csv")
    article_index = {}
    if os.path.exists(alp):
        with open(alp, newline="", encoding="utf-8") as f:
            seen = set()
            for row in csv.DictReader(f):
                orig = row["article_url"].strip()
                k = normalize(orig)
                if k not in seen:
                    article_index[k] = orig
                    seen.add(k)
        urls = set(article_index.keys())
    else:
        urls = set(ga4) | set(gsc)

    # ── 突合 ──────────────────────────────────────────────────────────────────
    rows = []
    for url in urls:
        g = ga4.get(url, {})
        s = gsc.get(url, {})
        pv = int(g.get("pv", 0))
        eng = g.get("avg_engagement_sec", "")
        rows.append({
            "_pv": pv,
            "article_url":        g.get("url") or article_index.get(url, url),
            "PV":                 pv,
            "アクティブユーザー": int(g.get("active_users", 0)),
            "平均エンゲージメント（秒）": eng,
            "エンゲージ評価":     grade(eng),
            "イベント数":        int(g.get("event_count", 0)),
            "キーイベント":      int(g.get("key_events", 0)),
            "CTAクリック数":      int(g.get("cta_clicks", 0)),
            "インプレッション":   int(s.get("impressions", 0)),
            "記事クリック数":     int(s.get("clicks", 0)),
            "記事CTR%":           float(s.get("ctr", 0) or 0),
            "掲載順位":           s.get("position", ""),
        })

    rows.sort(key=lambda r: -r["_pv"])
    for r in rows:
        del r["_pv"]

    # ── CSV 保存 ──────────────────────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"daily_{target}.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    # ── ターミナル表示 ────────────────────────────────────────────────────────
    W = 90
    total_pv = sum(r["PV"] for r in rows)
    hit = sum(1 for r in rows if r["PV"] > 0)
    print(f"\n{'='*W}")
    print(f"  日次PVレポート  {target}  対象{len(rows)}記事 / PVあり{hit}記事 / 合計PV {total_pv:,}")
    print(f"{'='*W}")
    print(f"{'#':>4}  {'記事URL末尾':<36} {'PV':>6} {'AU':>5} {'Eng':>6} 評価  {'IMP':>7} {'CLK':>5} {'CTR':>5} {'順位':>5}")
    print("─" * W)
    for i, r in enumerate(rows, 1):
        if r["PV"] == 0 and r["インプレッション"] == 0:
            continue
        slug = r["article_url"].rstrip("/").split("/")[-1][:36]
        eng_str = f"{float(r['平均エンゲージメント（秒）']):.0f}s" if r["平均エンゲージメント（秒）"] else "  -"
        ctr_str = f"{r['記事CTR%']:.1f}%" if r["記事CTR%"] else "  -"
        pos_str = f"{float(r['掲載順位']):.1f}" if r["掲載順位"] else "  -"
        print(f"{i:>4}  {slug:<36} {r['PV']:>6,} {r['アクティブユーザー']:>5,}"
              f" {eng_str:>6} {r['エンゲージ評価']:^4}"
              f" {r['インプレッション']:>7,} {r['記事クリック数']:>5,}"
              f" {ctr_str:>5} {pos_str:>5}")
    print("─" * W)
    print(f"  合計PV: {total_pv:,}  （データなし記事は非表示）")
    print(f"\n→ 保存: {out_path}  （{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n")


if __name__ == "__main__":
    main()
