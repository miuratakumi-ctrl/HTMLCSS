#!/usr/bin/env python3
"""
SPROUT 自動集計・データ分析スクリプト
======================================
使い方:
  python3 src/sprout_analyzer.py            # コンソール出力のみ
  python3 src/sprout_analyzer.py --sheets   # Google スプレッドシートにも同期
  python3 src/sprout_analyzer.py --output   # CSV にも出力

必要ライブラリ(--sheets 使用時のみ):
  pip install gspread google-auth
"""

import csv
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────
# 設定読み込み
# ─────────────────────────────────────────
def load_config():
    config_path = os.path.join(BASE_DIR, "config", "sprout_config.json")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────
# CSV 読み込みユーティリティ
# ─────────────────────────────────────────
def read_csv(relative_path):
    path = os.path.join(BASE_DIR, relative_path)
    if not os.path.exists(path):
        print(f"⚠  {relative_path} が見つかりません。スキップします。")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────
# 投稿管理分析
# ─────────────────────────────────────────
def analyze_posts(rows):
    """
    各投稿のエンゲージメント率を計算。
    エンゲージメント率 = (likes + comments + shares + saves) / impressions
    """
    results = []
    for r in rows:
        try:
            likes       = int(r.get("likes", 0) or 0)
            comments    = int(r.get("comments", 0) or 0)
            shares      = int(r.get("shares", 0) or 0)
            saves       = int(r.get("saves", 0) or 0)
            impressions = int(r.get("impressions", 0) or 0)
            engagement  = (likes + comments + shares + saves) / impressions if impressions else 0
            results.append({
                "date":           r["date"],
                "platform":       r["platform"],
                "post_type":      r["post_type"],
                "likes":          likes,
                "comments":       comments,
                "shares":         shares,
                "saves":          saves,
                "impressions":    impressions,
                "engagement_rate": round(engagement * 100, 2),  # %
                "url":            r.get("url", ""),
                "memo":           r.get("memo", ""),
            })
        except (ValueError, ZeroDivisionError):
            continue
    return results


def summarize_posts_by_platform(post_results):
    platform_stats = defaultdict(lambda: {
        "count": 0, "total_impressions": 0,
        "total_engagement": 0, "avg_engagement_rate": 0
    })
    for p in post_results:
        pl = p["platform"]
        platform_stats[pl]["count"] += 1
        platform_stats[pl]["total_impressions"] += p["impressions"]
        platform_stats[pl]["total_engagement"] += p["engagement_rate"]

    for pl, stats in platform_stats.items():
        if stats["count"]:
            stats["avg_engagement_rate"] = round(
                stats["total_engagement"] / stats["count"], 2)
    return dict(platform_stats)


# ─────────────────────────────────────────
# CF管理分析
# ─────────────────────────────────────────
def analyze_cf(rows, config):
    goal = config["cf"]["goal_amount"]
    tiers = {str(t): 0 for t in config["cf"]["return_tiers"]}
    tier_counts = {str(t): 0 for t in config["cf"]["return_tiers"]}

    total_amount = 0
    daily_totals = defaultdict(int)

    for r in rows:
        try:
            amount    = int(r.get("amount", 0) or 0)
            count     = int(r.get("count", 1) or 1)
            tier      = str(r.get("return_tier", ""))
            date      = r.get("date", "")
            total_amount    += amount * count
            daily_totals[date] += amount * count
            if tier in tiers:
                tiers[tier]       += amount * count
                tier_counts[tier] += count
        except ValueError:
            continue

    achievement_rate = round(total_amount / goal * 100, 1) if goal else 0

    return {
        "goal_amount":       goal,
        "total_amount":      total_amount,
        "achievement_rate":  achievement_rate,
        "remaining":         goal - total_amount,
        "tier_amounts":      tiers,
        "tier_counts":       tier_counts,
        "daily_totals":      dict(sorted(daily_totals.items())),
    }


# ─────────────────────────────────────────
# リターン管理分析
# ─────────────────────────────────────────
def analyze_returns(cf_rows, config):
    tiers = config["cf"]["return_tiers"]
    tier_data = {t: {"price": t, "sold": 0, "amount": 0} for t in tiers}

    for r in cf_rows:
        try:
            tier  = int(r.get("return_tier", 0) or 0)
            count = int(r.get("count", 0) or 0)
            if tier in tier_data:
                tier_data[tier]["sold"]   += count
                tier_data[tier]["amount"] += tier * count
        except ValueError:
            continue
    return list(tier_data.values())


# ─────────────────────────────────────────
# フォロワー推移分析
# ─────────────────────────────────────────
def analyze_followers(rows):
    results = []
    prev_total = None
    for r in rows:
        try:
            ig    = int(r.get("instagram", 0) or 0)
            tw    = int(r.get("twitter",   0) or 0)
            yt    = int(r.get("youtube",   0) or 0)
            tt    = int(r.get("tiktok",    0) or 0)
            total = ig + tw + yt + tt
            diff  = total - prev_total if prev_total is not None else 0
            results.append({
                "date":        r["date"],
                "instagram":   ig,
                "twitter":     tw,
                "youtube":     yt,
                "tiktok":      tt,
                "total":       total,
                "diff":        diff,
                "memo":        r.get("memo", ""),
            })
            prev_total = total
        except ValueError:
            continue
    return results


# ─────────────────────────────────────────
# 週次分析
# ─────────────────────────────────────────
def analyze_weekly(post_results, cf_data, follower_results):
    """投稿データを週単位で集計。"""
    weekly = defaultdict(lambda: {
        "post_count": 0, "total_impressions": 0,
        "total_engagement": 0, "cf_amount": 0
    })

    for p in post_results:
        try:
            dt  = datetime.strptime(p["date"], "%Y-%m-%d")
            # 月曜始まりの週番号（ISO）
            week_key = dt.strftime("%Y-W%W")
            weekly[week_key]["post_count"]        += 1
            weekly[week_key]["total_impressions"] += p["impressions"]
            weekly[week_key]["total_engagement"]  += p["engagement_rate"]
        except ValueError:
            continue

    for date, amount in cf_data["daily_totals"].items():
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            week_key = dt.strftime("%Y-W%W")
            weekly[week_key]["cf_amount"] += amount
        except ValueError:
            continue

    results = []
    for week, stats in sorted(weekly.items()):
        avg_eng = round(
            stats["total_engagement"] / stats["post_count"], 2
        ) if stats["post_count"] else 0
        results.append({
            "week":              week,
            "post_count":        stats["post_count"],
            "total_impressions": stats["total_impressions"],
            "avg_engagement":    avg_eng,
            "cf_amount":         stats["cf_amount"],
        })
    return results


# ─────────────────────────────────────────
# コンソール出力
# ─────────────────────────────────────────
def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_report(post_results, platform_stats, cf_data, return_data,
                 follower_results, weekly_data):

    # ── CF サマリー ──────────────────────────
    print_section("🎯 CF管理サマリー")
    print(f"  目標金額   : ¥{cf_data['goal_amount']:>10,}")
    print(f"  現在の支援額: ¥{cf_data['total_amount']:>10,}")
    print(f"  達成率     : {cf_data['achievement_rate']:>9.1f} %")
    print(f"  残り金額   : ¥{cf_data['remaining']:>10,}")

    # ── リターン管理 ──────────────────────────
    print_section("🎁 リターン管理")
    print(f"  {'金額':>10}  {'販売数':>6}  {'売上':>12}")
    print("  " + "-" * 34)
    for t in return_data:
        print(f"  ¥{t['price']:>9,}  {t['sold']:>6}  ¥{t['amount']:>11,}")

    # ── 投稿管理 ──────────────────────────────
    print_section("📅 投稿管理（エンゲージメント率）")
    print(f"  {'日付':<12} {'媒体':<12} {'種別':<8} {'IMP':>7} {'ENG%':>7}")
    print("  " + "-" * 52)
    for p in post_results:
        print(f"  {p['date']:<12} {p['platform']:<12} {p['post_type']:<8}"
              f" {p['impressions']:>7,} {p['engagement_rate']:>6.1f}%")

    # ── プラットフォーム別集計 ─────────────────
    print_section("📊 プラットフォーム別集計")
    print(f"  {'媒体':<12} {'投稿数':>6}  {'合計IMP':>10}  {'平均ENG%':>9}")
    print("  " + "-" * 44)
    for pl, s in platform_stats.items():
        print(f"  {pl:<12} {s['count']:>6,}  {s['total_impressions']:>10,}"
              f"  {s['avg_engagement_rate']:>8.1f}%")

    # ── フォロワー推移 ────────────────────────
    print_section("📈 フォロワー推移")
    print(f"  {'日付':<12} {'IG':>7} {'TW':>7} {'YT':>7} {'TT':>7} {'合計':>8} {'増減':>6}")
    print("  " + "-" * 60)
    for fw in follower_results:
        diff_str = f"+{fw['diff']}" if fw["diff"] > 0 else str(fw["diff"])
        print(f"  {fw['date']:<12} {fw['instagram']:>7,} {fw['twitter']:>7,}"
              f" {fw['youtube']:>7,} {fw['tiktok']:>7,} {fw['total']:>8,} {diff_str:>6}")

    # ── 週次分析 ──────────────────────────────
    print_section("📊 週次分析")
    print(f"  {'週':<10} {'投稿数':>6} {'合計IMP':>10} {'平均ENG%':>9} {'CF支援額':>12}")
    print("  " + "-" * 54)
    for w in weekly_data:
        print(f"  {w['week']:<10} {w['post_count']:>6}"
              f" {w['total_impressions']:>10,} {w['avg_engagement']:>8.1f}%"
              f" ¥{w['cf_amount']:>10,}")

    print(f"\n{'='*60}")
    print(f"  集計完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────
# CSV 出力
# ─────────────────────────────────────────
def save_csv_output(post_results, cf_data, return_data, follower_results, weekly_data):
    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    # 投稿管理
    path = os.path.join(output_dir, "posts_analyzed.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        if post_results:
            writer = csv.DictWriter(f, fieldnames=post_results[0].keys())
            writer.writeheader(); writer.writerows(post_results)
    print(f"→ {path}")

    # CF管理
    path = os.path.join(output_dir, "cf_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["項目", "値"])
        writer.writerow(["目標金額",  cf_data["goal_amount"]])
        writer.writerow(["支援総額",  cf_data["total_amount"]])
        writer.writerow(["達成率(%)", cf_data["achievement_rate"]])
        writer.writerow(["残り金額",  cf_data["remaining"]])
    print(f"→ {path}")

    # リターン管理
    path = os.path.join(output_dir, "returns_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        if return_data:
            writer = csv.DictWriter(f, fieldnames=return_data[0].keys())
            writer.writeheader(); writer.writerows(return_data)
    print(f"→ {path}")

    # フォロワー推移
    path = os.path.join(output_dir, "followers_analyzed.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        if follower_results:
            writer = csv.DictWriter(f, fieldnames=follower_results[0].keys())
            writer.writeheader(); writer.writerows(follower_results)
    print(f"→ {path}")

    # 週次分析
    path = os.path.join(output_dir, "weekly_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        if weekly_data:
            writer = csv.DictWriter(f, fieldnames=weekly_data[0].keys())
            writer.writeheader(); writer.writerows(weekly_data)
    print(f"→ {path}")


# ─────────────────────────────────────────
# Google スプレッドシート同期
# ─────────────────────────────────────────
def sync_to_google_sheets(config, post_results, platform_stats, cf_data,
                           return_data, follower_results, weekly_data):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("❌ gspread / google-auth が未インストールです。")
        print("   pip install gspread google-auth  を実行してください。")
        return

    creds_path = os.path.join(BASE_DIR, config["google_sheets"]["credentials_file"])
    if not os.path.exists(creds_path):
        print(f"❌ 認証ファイルが見つかりません: {creds_path}")
        print("   README.md の「Google スプレッドシート連携手順」を参照してください。")
        return

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc    = gspread.authorize(creds)

    spreadsheet_id = config["google_sheets"]["spreadsheet_id"]
    if spreadsheet_id == "YOUR_SPREADSHEET_ID_HERE":
        print("❌ config/sprout_config.json の spreadsheet_id を設定してください。")
        return

    sh     = gc.open_by_key(spreadsheet_id)
    names  = config["google_sheets"]["sheet_names"]

    def get_or_create_ws(name):
        try:
            return sh.worksheet(name)
        except gspread.WorksheetNotFound:
            return sh.add_worksheet(title=name, rows=200, cols=20)

    def write_rows(ws, header, rows):
        ws.clear()
        ws.append_row(header)
        for row in rows:
            ws.append_row(list(row.values()) if isinstance(row, dict) else row)

    # 📅投稿管理
    ws = get_or_create_ws(names["posts"])
    write_rows(ws,
        ["日付","媒体","種別","いいね","コメント","シェア","保存","IMP","ENG%","URL","メモ"],
        [{
            "date": p["date"], "platform": p["platform"], "post_type": p["post_type"],
            "likes": p["likes"], "comments": p["comments"], "shares": p["shares"],
            "saves": p["saves"], "impressions": p["impressions"],
            "eng": p["engagement_rate"], "url": p["url"], "memo": p["memo"]
        } for p in post_results]
    )
    print(f"✅ {names['posts']} を更新しました")

    # 📊週次分析
    ws = get_or_create_ws(names["weekly"])
    write_rows(ws,
        ["週","投稿数","合計IMP","平均ENG%","CF支援額"],
        weekly_data
    )
    print(f"✅ {names['weekly']} を更新しました")

    # 🎯CF管理
    ws = get_or_create_ws(names["cf"])
    ws.clear()
    ws.append_row(["項目", "値"])
    ws.append_row(["目標金額",   cf_data["goal_amount"]])
    ws.append_row(["支援総額",   cf_data["total_amount"]])
    ws.append_row(["達成率(%)",  cf_data["achievement_rate"]])
    ws.append_row(["残り金額",   cf_data["remaining"]])
    ws.append_row([])
    ws.append_row(["日付", "当日支援額"])
    for date, amount in cf_data["daily_totals"].items():
        ws.append_row([date, amount])
    print(f"✅ {names['cf']} を更新しました")

    # 🎁リターン管理
    ws = get_or_create_ws(names["returns"])
    write_rows(ws, ["金額(円)", "販売数", "売上合計(円)"], return_data)
    print(f"✅ {names['returns']} を更新しました")

    # 📈フォロワー推移
    ws = get_or_create_ws(names["followers"])
    write_rows(ws,
        ["日付","Instagram","Twitter","YouTube","TikTok","合計","増減","メモ"],
        follower_results
    )
    print(f"✅ {names['followers']} を更新しました")

    print(f"\n🔗 スプレッドシート: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SPROUT 自動集計・データ分析")
    parser.add_argument("--sheets", action="store_true",
                        help="Google スプレッドシートに同期する")
    parser.add_argument("--output", action="store_true",
                        help="output/ に CSV を出力する")
    args = parser.parse_args()

    config = load_config()

    # ── データ読み込み ──
    post_rows      = read_csv(config["input"]["posts_csv"])
    cf_rows        = read_csv(config["input"]["cf_csv"])
    follower_rows  = read_csv(config["input"]["followers_csv"])

    # ── 分析 ──
    post_results     = analyze_posts(post_rows)
    platform_stats   = summarize_posts_by_platform(post_results)
    cf_data          = analyze_cf(cf_rows, config)
    return_data      = analyze_returns(cf_rows, config)
    follower_results = analyze_followers(follower_rows)
    weekly_data      = analyze_weekly(post_results, cf_data, follower_results)

    # ── コンソール出力 ──
    print_report(post_results, platform_stats, cf_data, return_data,
                 follower_results, weekly_data)

    # ── CSV 出力（オプション）──
    if args.output:
        print("\n📄 CSV ファイルを出力中...")
        save_csv_output(post_results, cf_data, return_data, follower_results, weekly_data)

    # ── Google スプレッドシート同期（オプション）──
    if args.sheets:
        print("\n☁️  Google スプレッドシートに同期中...")
        sync_to_google_sheets(config, post_results, platform_stats, cf_data,
                               return_data, follower_results, weekly_data)


if __name__ == "__main__":
    main()
