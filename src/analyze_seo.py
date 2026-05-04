#!/usr/bin/env python3
"""
input/ahrefs_pages.csv を読み込み、記事ごとにリライト優先度（A/B/C/D）と
被リンク獲得候補フラグを付与して出力する。

出力:
  output/seo_analysis.csv     — 全記事の優先度分類
  output/backlink_targets.csv — 被リンク獲得候補記事
"""

import csv
import os
import sys
from datetime import date

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# MOFU/BOFU 判定キーワード（URL + top_keyword から探索）
_MOFU = ["アルゴリズム", "フォロワー", "収益化", "インプレッション", "エンゲージメント",
         "増やし方", "伸びる", "運用", "投稿時間", "ベストタイム"]
_BOFU = ["訴求力", "商用利用", "代行", "コンサル", "費用", "マーケティング"]

# 被リンクが集まりやすいトピック（既存高RD記事から帰納）
_LINKBAIT = ["音楽", "バグ", "できない", "エラー", "不具合", "凍結", "制限",
             "著作権", "シャドウバン", "確認", "アルゴリズム", "解除",
             "ログインできない", "スクショ", "保存方法", "年齢制限"]

# 被リンク記事として既に機能している（別枠管理）
_EXISTING_LINKBAIT_RD_THRESHOLD = 100


def _text(row):
    return (row.get("url", "") + " " + row.get("top_keyword", "")).lower()


def classify_type(row):
    t = _text(row)
    for kw in _BOFU:
        if kw in t:
            return "BOFU"
    for kw in _MOFU:
        if kw in t:
            return "MOFU"
    return "TOFU"


def classify_priority(row):
    try:
        traffic = int(row.get("sum_traffic") or 0)
        pos     = int(row.get("top_keyword_best_position") or 99)
        vol     = int(row.get("top_keyword_volume") or 0)
        kws     = int(row.get("keywords") or 0)
        rd      = int(row.get("referring_domains") or 0)
    except ValueError:
        return "C"

    article_type = row.get("article_type", "TOFU")
    daily = traffic / 30

    # 高RD → 被リンク記事として別枠
    if rd >= _EXISTING_LINKBAIT_RD_THRESHOLD:
        return "C（被リンク記事）"

    # D: 既存記事が薄すぎる → 新規記事で攻めた方が速い
    if traffic < 80 and kws < 10:
        return "D"

    # A: 最優先リライト
    #   MOFU/BOFU で 6-15 位
    if article_type in ("MOFU", "BOFU") and 6 <= pos <= 15:
        return "A"
    #   高 vol KW で 6-20 位（大量流入回収チャンス）
    if vol >= 5000 and 6 <= pos <= 20:
        return "A"
    #   超高 vol で 20 位以内
    if vol >= 10000 and pos <= 20:
        return "A"

    # B: リライト候補
    if 6 <= pos <= 20:
        return "B"
    if daily < 10 and vol >= 500:
        return "B"

    return "C"


def is_linkbait(row):
    t = _text(row)
    return any(p in t for p in _LINKBAIT)


def main():
    ahrefs_path = os.path.join(BASE_DIR, "input", "ahrefs_pages.csv")
    if not os.path.exists(ahrefs_path):
        print("⚠  input/ahrefs_pages.csv が見つかりません。"
              "先に python3 src/fetch_ahrefs.py を実行してください。")
        sys.exit(1)

    with open(ahrefs_path, newline="", encoding="utf-8") as f:
        pages = list(csv.DictReader(f))

    # /media/ 配下のみを対象
    pages = [p for p in pages if "/media/" in p.get("url", "")]

    rows = []
    for p in pages:
        p["article_type"] = classify_type(p)
        p["priority"]     = classify_priority(p)
        p["linkbait"]     = "○" if is_linkbait(p) else ""
        rows.append(p)

    _ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "C（被リンク記事）": 4}
    rows.sort(key=lambda r: (
        _ORDER.get(r["priority"], 9),
        -int(r.get("sum_traffic") or 0),
    ))

    a_rows   = [r for r in rows if r["priority"] == "A"]
    b_rows   = [r for r in rows if r["priority"] == "B"]
    c_rows   = [r for r in rows if r["priority"] == "C"]
    d_rows   = [r for r in rows if r["priority"] == "D"]
    cl_rows  = [r for r in rows if "被リンク" in r["priority"]]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── seo_analysis.csv ──────────────────────────────────────────────────────
    fields = ["url", "article_type", "priority", "sum_traffic",
              "top_keyword", "top_keyword_best_position", "top_keyword_volume",
              "keywords", "referring_domains", "linkbait"]
    out_path = os.path.join(OUTPUT_DIR, "seo_analysis.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # ── backlink_targets.csv ──────────────────────────────────────────────────
    link_rows = [r for r in rows if r["linkbait"] == "○"]
    link_rows.sort(key=lambda r: -int(r.get("top_keyword_volume") or 0))
    link_path = os.path.join(OUTPUT_DIR, "backlink_targets.csv")
    with open(link_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(link_rows)

    # ── ターミナル表示 ────────────────────────────────────────────────────────
    W = 72
    print("\n" + "=" * W)
    print(f"  SEO 分析レポート  {date.today()}")
    print("=" * W)
    print(f"  対象記事数            : {len(rows)}")
    print(f"  A（最優先リライト）   : {len(a_rows):>3} 記事")
    print(f"  B（リライト候補）     : {len(b_rows):>3} 記事")
    print(f"  C（保留）             : {len(c_rows):>3} 記事")
    print(f"  D（新規記事を優先）   : {len(d_rows):>3} 記事")
    print(f"  C（被リンク記事）     : {len(cl_rows):>3} 記事（別枠管理）")

    def _slug(url):
        return url.rstrip("/").split("/")[-1][:30]

    def _hdr(label):
        print(f"\n── {label} " + "─" * (W - len(label) - 4))
        print(f"{'URL末尾':<32} {'タイプ':<5} {'流入':>7} {'順位':>5}"
              f" {'vol':>7} {'KW数':>5} {'RD':>5}")
        print("─" * W)

    def _row(r):
        print(f"{_slug(r['url']):<32} {r['article_type']:<5}"
              f" {int(r.get('sum_traffic') or 0):>7,}"
              f" {int(r.get('top_keyword_best_position') or 0):>5}"
              f" {int(r.get('top_keyword_volume') or 0):>7,}"
              f" {int(r.get('keywords') or 0):>5}"
              f" {int(r.get('referring_domains') or 0):>5}")

    _hdr("A: 最優先リライト")
    for r in a_rows:
        _row(r)

    _hdr("B: リライト候補（上位 10 件）")
    for r in b_rows[:10]:
        _row(r)

    if cl_rows:
        _hdr("被リンク記事（別枠管理）")
        for r in cl_rows:
            _row(r)

    print(f"\n── 被リンク獲得向け新規記事ターゲット（難易度0） " + "─" * 20)
    print(f"  {'キーワード':<38} {'vol':>7}  traffic_potential")
    print("  " + "─" * 60)
    _candidates = [
        ("インスタ ブロックされてるか確認",  15000, 91000),
        ("インスタ ログインできない",         18000, 17000),
        ("インスタ スクショ 通知",             3900, 33000),
        ("x ログインしないで見る",              450, 27000),
        ("インスタ バグ",                      2500, 15000),
        ("x シャドウバン 解除",               1700,  8600),
        ("youtube 制限付きモード 解除",        1700,  8600),
        ("youtube 年齢制限解除",              2700,  8400),
        ("x 凍結 なぜ",                       1400, 13000),
        ("tiktok シャドウバン 確認",           1200,  2400),
    ]
    for kw, vol, tp in _candidates:
        print(f"  {kw:<38} {vol:>7,}  {tp:>7,}")

    print(f"\n  → {out_path}")
    print(f"  → {link_path}")
    print("=" * W + "\n")


if __name__ == "__main__":
    main()
