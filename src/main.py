#!/usr/bin/env python3
"""
ga4_current_month.csv / ga4_prev_month.csv / gsc_current_month.csv / gsc_prev_month.csv
を突合して output/report.csv を生成する（月次比較レポート）。

使い方:
  python3 src/main.py
  python3 src/main.py --date 2026-04-30
"""

import argparse
import calendar
import csv
import os
import sys
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

_FIELDNAMES = [
    "article_url",
    "PV（当月累計）", "PV（先月全期間）", "期待PV（先月ペース換算）",
    "PV差分（実績−期待）", "増減率（対期待）%", "ペース比", "ランク",
    "アクティブユーザー", "平均エンゲージメント（秒）", "エンゲージ評価",
    "イベント数", "キーイベント",
    "インプレッション", "記事クリック数", "CTAクリック数",
    "記事CTR%", "掲載順位",
    "補助シグナル（自動）",
]


def normalize(url):
    return url.strip().rstrip("/").lower()


def read_csv_index(path, key_col):
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {normalize(r[key_col]): r for r in rows if r.get(key_col)}


def engage_grade(secs):
    try:
        s = float(secs)
    except (ValueError, TypeError):
        return "-"
    if s >= 180:
        return "S"
    if s >= 120:
        return "A"
    if s >= 60:
        return "B"
    if s >= 30:
        return "C"
    return "D"


_CTR_BY_POS = {
    1: 28.5, 2: 15.7, 3: 11.0, 4: 8.0, 5: 7.2,
    6: 5.1, 7: 4.0, 8: 3.2, 9: 2.8, 10: 2.5,
}


def _expected_ctr(pos_str):
    try:
        return _CTR_BY_POS.get(int(round(float(pos_str))), 1.5)
    except (ValueError, TypeError):
        return None


def aux_signal(pace, position, ctr_pct, engagement_sec, prev_pos):
    signals = []

    try:
        p = float(pace)
        if p >= 1.3:
            signals.append("急上昇")
        elif p >= 1.1:
            signals.append("好調")
        elif p <= 0.5:
            signals.append("急落")
        elif p <= 0.8:
            signals.append("低調")
    except (ValueError, TypeError):
        pass

    exp_ctr = _expected_ctr(position)
    if exp_ctr is not None:
        try:
            if float(ctr_pct) < exp_ctr * 0.6:
                signals.append("CTR低下")
        except (ValueError, TypeError):
            pass

    try:
        pos = float(position)
        if prev_pos:
            pp = float(prev_pos)
            if pos < pp - 3:
                signals.append("順位上昇")
            elif pos > pp + 3:
                signals.append("順位低下")
    except (ValueError, TypeError):
        pass

    try:
        if float(engagement_sec) < 30:
            signals.append("離脱率高")
    except (ValueError, TypeError):
        pass

    return " / ".join(signals) if signals else "安定"


def main(reference_date=None):
    if reference_date is None:
        parser = argparse.ArgumentParser(description="月次PV比較レポート生成")
        parser.add_argument("--date", help="基準日 YYYY-MM-DD（省略時は昨日）")
        args, _ = parser.parse_known_args()
        reference_date = (
            date.fromisoformat(args.date) if args.date
            else date.today() - timedelta(days=1)
        )

    reference = (
        reference_date if isinstance(reference_date, date)
        else date.fromisoformat(str(reference_date))
    )

    cur_month_start = date(reference.year, reference.month, 1)
    days_elapsed = (reference - cur_month_start).days + 1

    if reference.month == 1:
        prev_year, prev_month = reference.year - 1, 12
    else:
        prev_year, prev_month = reference.year, reference.month - 1
    days_in_prev = calendar.monthrange(prev_year, prev_month)[1]

    ga4_cur  = read_csv_index(os.path.join(INPUT_DIR, "ga4_current_month.csv"),  "article_url")
    ga4_prev = read_csv_index(os.path.join(INPUT_DIR, "ga4_prev_month.csv"),     "article_url")
    gsc_cur  = read_csv_index(os.path.join(INPUT_DIR, "gsc_current_month.csv"),  "article_url")
    gsc_prev = read_csv_index(os.path.join(INPUT_DIR, "gsc_prev_month.csv"),     "article_url")

    if not ga4_cur:
        print("⚠  input/ga4_current_month.csv が見つかりません。"
              "先に python3 src/fetch_monthly.py を実行してください。")
        sys.exit(1)

    all_urls = set(ga4_cur) | set(ga4_prev) | set(gsc_cur)

    rows = []
    for url in all_urls:
        c4  = ga4_cur.get(url, {})
        p4  = ga4_prev.get(url, {})
        cgs = gsc_cur.get(url, {})
        pgs = gsc_prev.get(url, {})

        cur_pv  = int(c4.get("pv", 0))
        prev_pv = int(p4.get("pv", 0))

        expected_pv = round(prev_pv / days_in_prev * days_elapsed) if prev_pv else 0
        pv_diff     = cur_pv - expected_pv
        pace        = round(cur_pv / expected_pv, 3) if expected_pv else ""
        inc_rate    = round((cur_pv - expected_pv) / expected_pv * 100, 1) if expected_pv else ""

        engagement = c4.get("avg_engagement_sec", "")
        position   = cgs.get("position", "")
        ctr_val    = float(cgs.get("ctr_%", 0) or 0)
        prev_pos   = pgs.get("position")
        article_url = c4.get("article_url") or p4.get("article_url") or url

        rows.append({
            "_cur_pv": cur_pv,
            "article_url":              article_url,
            "PV（当月累計）":            cur_pv,
            "PV（先月全期間）":          prev_pv,
            "期待PV（先月ペース換算）":   expected_pv,
            "PV差分（実績−期待）":       pv_diff,
            "増減率（対期待）%":         inc_rate,
            "ペース比":                 pace,
            "ランク":                   "",
            "アクティブユーザー":        int(c4.get("active_users", 0)),
            "平均エンゲージメント（秒）": engagement,
            "エンゲージ評価":            engage_grade(engagement),
            "イベント数":               int(c4.get("event_count", 0)),
            "キーイベント":             int(c4.get("key_events", 0)),
            "インプレッション":          int(cgs.get("impressions", 0)),
            "記事クリック数":            int(cgs.get("clicks", 0)),
            "CTAクリック数":             int(c4.get("cta_clicks", 0)),
            "記事CTR%":                 ctr_val,
            "掲載順位":                 position,
            "補助シグナル（自動）":      aux_signal(pace, position, ctr_val, engagement, prev_pos),
        })

    rows.sort(key=lambda r: -r["_cur_pv"])
    for i, r in enumerate(rows, 1):
        r["ランク"] = i
        del r["_cur_pv"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "report.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    # ── ターミナル表示 ────────────────────────────────────────────────────────
    W = 100
    print(f"\n{'='*W}")
    print(f"  月次PV比較レポート  基準日: {reference}"
          f"  （当月 {days_elapsed} 日経過 / 前月 {days_in_prev} 日）")
    print(f"{'='*W}")
    print(f"{'#':>4}  {'記事URL末尾':<36} {'当月PV':>8} {'先月PV':>8}"
          f" {'期待PV':>8} {'差分':>7} {'ペース':>6} {'評価':<2} {'シグナル'}")
    print("─" * W)

    def _slug(url):
        return url.rstrip("/").split("/")[-1][:36]

    for r in rows[:40]:
        pace_str = f"{r['ペース比']:.2f}" if r["ペース比"] != "" else "  -"
        diff_str = f"{r['PV差分（実績−期待）']:+,}"
        print(f"{r['ランク']:>4}  {_slug(r['article_url']):<36}"
              f" {r['PV（当月累計）']:>8,} {r['PV（先月全期間）']:>8,}"
              f" {r['期待PV（先月ペース換算）']:>8,} {diff_str:>7} {pace_str:>6}"
              f"  {r['エンゲージ評価']:<2} {r['補助シグナル（自動）']}")

    total_cur  = sum(r["PV（当月累計）"]          for r in rows)
    total_prev = sum(r["PV（先月全期間）"]         for r in rows)
    total_exp  = sum(r["期待PV（先月ペース換算）"] for r in rows)
    overall    = round(total_cur / total_exp, 3) if total_exp else 0
    diff_total = total_cur - total_exp

    print("─" * W)
    print(f"{'合計':>4}  {'':36} {total_cur:>8,} {total_prev:>8,}"
          f" {total_exp:>8,} {diff_total:>+7,} {overall:>6.2f}")
    print(f"\n→ 保存: {out_path}  （{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n")


if __name__ == "__main__":
    main()
