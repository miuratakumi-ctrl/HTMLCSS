#!/usr/bin/env python3
"""
過去7日分の GA4 click数 + GSC データを集計してweeklyレポートを生成する。

使い方:
  python3 src/weekly_report.py              # 昨日を末日とした7日間
  python3 src/weekly_report.py --date 2026-05-08   # 指定日を末日とした7日間
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
    "article_url",
    "click数（7日間）",
    "PV（7日間）",
    "アクティブユーザー（7日間）",
    "平均エンゲージメント（秒）",
    "エンゲージ評価",
    "イベント数（7日間）",
    "キーイベント（7日間）",
    "インプレッション（7日間）",
    "記事クリック数（GSC・7日間）",
    "記事CTR%",
    "掲載順位",
]


def normalize(u): return u.strip().rstrip("/").lower()


def grade(s):
    try: v = float(s)
    except: return "-"
    return "S" if v >= 180 else "A" if v >= 120 else "B" if v >= 60 else "C" if v >= 30 else "D"


def main(end_date=None):
    if end_date is None:
        parser = argparse.ArgumentParser(description="週次clickレポート")
        parser.add_argument("--date", help="末日 YYYY-MM-DD（省略時は昨日）")
        args = parser.parse_args()
        end_date = (
            date.fromisoformat(args.date) if args.date
            else date.today() - timedelta(days=1)
        )
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    start_date = end_date - timedelta(days=6)

    from _config import load_config
    import fetch_ga4
    import fetch_gsc

    config = load_config()
    print(f"📥 {start_date} 〜 {end_date}（7日間）のデータを取得中...")

    ga4_path = os.path.join(INPUT_DIR, "ga4_weekly.csv")
    gsc_path = os.path.join(INPUT_DIR, "gsc_weekly.csv")

    fetch_ga4.fetch(config, start_date=start_date, end_date=end_date, out_path=ga4_path)
    fetch_gsc.fetch(config, start_date=start_date, end_date=end_date, out_path=gsc_path)

    def read_idx(path, key):
        if not os.path.exists(path): return {}
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return {normalize(r[key]): r for r in rows if r.get(key)}

    ga4 = read_idx(ga4_path, "url")
    gsc = read_idx(gsc_path, "url")

    # article_list.csv があれば対象を絞り込む
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

    rows = []
    for url in urls:
        g = ga4.get(url, {})
        s = gsc.get(url, {})
        clicks = int(g.get("cta_clicks", 0))   # fetch_ga4 が "click" イベントで集計した数
        pv     = int(g.get("pv", 0))
        eng    = g.get("avg_engagement_sec", "")
        rows.append({
            "_clicks": clicks,
            "article_url":                  g.get("url") or article_index.get(url, url),
            "click数（7日間）":              clicks,
            "PV（7日間）":                  pv,
            "アクティブユーザー（7日間）":   int(g.get("active_users", 0)),
            "平均エンゲージメント（秒）":     eng,
            "エンゲージ評価":               grade(eng),
            "イベント数（7日間）":           int(g.get("event_count", 0)),
            "キーイベント（7日間）":         int(g.get("key_events", 0)),
            "インプレッション（7日間）":     int(s.get("impressions", 0)),
            "記事クリック数（GSC・7日間）":  int(s.get("clicks", 0)),
            "記事CTR%":                     float(s.get("ctr", 0) or 0),
            "掲載順位":                     s.get("position", ""),
        })

    # click数の多い順にソート
    rows.sort(key=lambda r: -r["_clicks"])
    for r in rows:
        del r["_clicks"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"weekly_{end_date}.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    W = 95
    total_clicks = sum(r["click数（7日間）"] for r in rows)
    total_pv     = sum(r["PV（7日間）"] for r in rows)
    print(f"\n{'='*W}")
    print(f"  週次clickレポート  {start_date} 〜 {end_date}  "
          f"対象{len(rows)}記事 / 合計click {total_clicks:,} / 合計PV {total_pv:,}")
    print(f"{'='*W}")
    print(f"{'#':>4}  {'記事URL末尾':<36} {'click':>6} {'PV':>7} {'Eng':>6} 評価  "
          f"{'IMP':>8} {'GSC_CLK':>7} {'CTR':>5} {'順位':>5}")
    print("─" * W)
    for i, r in enumerate(rows, 1):
        if r["click数（7日間）"] == 0 and r["PV（7日間）"] == 0:
            continue
        slug    = r["article_url"].rstrip("/").split("/")[-1][:36]
        eng_str = f"{float(r['平均エンゲージメント（秒）']):.0f}s" if r["平均エンゲージメント（秒）"] else "  -"
        ctr_str = f"{r['記事CTR%']:.1f}%" if r["記事CTR%"] else "  -"
        pos_str = f"{float(r['掲載順位']):.1f}" if r["掲載順位"] else "  -"
        print(f"{i:>4}  {slug:<36} {r['click数（7日間）']:>6,} {r['PV（7日間）']:>7,}"
              f" {eng_str:>6} {r['エンゲージ評価']:^4}"
              f" {r['インプレッション（7日間）']:>8,} {r['記事クリック数（GSC・7日間）']:>7,}"
              f" {ctr_str:>5} {pos_str:>5}")
    print("─" * W)
    print(f"  合計click: {total_clicks:,}  合計PV: {total_pv:,}  （データなし記事は非表示）")
    print(f"\n→ 保存: {out_path}  （{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n")


if __name__ == "__main__":
    main()
