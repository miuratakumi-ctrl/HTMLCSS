"""
GA4 / GSC / expected_pv を突合して output/report.csv を生成するスクリプト
標準ライブラリのみで動作します（pandas 不要）
"""

import csv
import os
import calendar
from datetime import date

# ─────────────────────────────────────────────
# 設定: ファイルパス
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GA4_PATH = os.path.join(BASE_DIR, "input", "ga4.csv")
GSC_PATH = os.path.join(BASE_DIR, "input", "gsc.csv")
EPV_PATH = os.path.join(BASE_DIR, "input", "expected_pv.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "output", "report.csv")

# ─────────────────────────────────────────────
# 設定: CTAクリック数の列名候補
# 将来イベント名を変更する場合はここを編集してください
# ─────────────────────────────────────────────
CTA_COLUMN_CANDIDATES = [
    "CTAクリック数",
    "cta_clicks",
    "CTA clicks",
    "cta_click",
    "CTAクリック",
]

# ─────────────────────────────────────────────
# 設定: 各CSVの列名候補（表記ゆれ対応）
# ─────────────────────────────────────────────

# GA4 列名候補
GA4_COLUMN_MAP = {
    "article_url": ["article_url", "URL", "url", "ページURL", "page_url", "記事URL"],
    "PV":          ["PV", "pv", "ページビュー", "page_views", "pageviews", "セッション"],
    "アクティブユーザー": [
        "アクティブユーザー", "active_users", "activeUsers", "ユーザー", "users",
    ],
    "平均エンゲージメント": [
        "平均エンゲージメント", "avg_engagement_time", "平均エンゲージメント時間",
        "averageEngagementTime", "engagement_time", "エンゲージメント時間",
    ],
    "イベント数":   ["イベント数", "event_count", "events", "eventCount"],
    "キーイベント": [
        "キーイベント", "key_events", "conversions", "コンバージョン", "keyEvents",
    ],
    # CTAクリック数は CTA_COLUMN_CANDIDATES で別管理
}

# GSC 列名候補
GSC_COLUMN_MAP = {
    "article_url":  ["article_url", "URL", "url", "ページ", "page", "ページURL", "記事URL"],
    "インプレッション": ["インプレッション", "impressions", "Impressions", "表示回数"],
    "記事クリック数":   ["記事クリック数", "clicks", "Clicks", "クリック数", "クリック"],
    "記事CTR":     ["記事CTR", "ctr", "CTR", "クリック率"],
    "掲載順位":     ["掲載順位", "position", "Position", "平均掲載順位", "avg_position"],
}

# expected_pv 列名候補
EPV_COLUMN_MAP = {
    "article_url":        ["article_url", "URL", "url", "記事URL", "page_url"],
    "monthly_expected_pv": [
        "monthly_expected_pv", "expected_pv", "月間期待PV", "目標PV", "target_pv",
    ],
}

# ─────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────

def to_float(value, default=0.0):
    """文字列を float に変換。失敗したら default を返す。"""
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def resolve_key(row_keys: list[str], candidates: list[str]) -> str:
    """候補リストの中で row_keys に存在する最初のキーを返す。なければ空文字。"""
    for c in candidates:
        if c in row_keys:
            return c
    return ""


def normalize_row(raw_row: dict, column_map: dict) -> dict:
    """column_map に従って辞書のキーを正規化して返す。"""
    keys = list(raw_row.keys())
    result = {}
    for target, candidates in column_map.items():
        found = resolve_key(keys, candidates)
        result[target] = raw_row.get(found, "").strip() if found else ""
    return result


def load_csv(path: str) -> list[dict]:
    """UTF-8（BOM付き対応）で CSV を読み込み、辞書のリストを返す。"""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # 列名の前後空白を除去
        rows = []
        for raw in reader:
            rows.append({k.strip(): v for k, v in raw.items()})
    return rows


# ─────────────────────────────────────────────
# エンゲージ評価
# ─────────────────────────────────────────────

def evaluate_engagement(seconds: float) -> str:
    """平均エンゲージメント時間（秒）をもとに 高/中/低 を返す。"""
    if seconds >= 120:
        return "高"
    elif seconds >= 60:
        return "中"
    else:
        return "低"


# ─────────────────────────────────────────────
# 期待PV の計算
# ─────────────────────────────────────────────

def calc_expected_pv(monthly: float, today: date | None = None) -> float:
    """当月経過日数ベースで期待PVを算出する。"""
    if today is None:
        today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return monthly * (today.day / days_in_month)


# ─────────────────────────────────────────────
# 各CSVの読み込みと正規化
# ─────────────────────────────────────────────

def load_ga4() -> dict[str, dict]:
    rows = load_csv(GA4_PATH)
    result = {}
    for raw in rows:
        row = normalize_row(raw, GA4_COLUMN_MAP)

        # CTAクリック数: CTA_COLUMN_CANDIDATES で検索
        cta_key = resolve_key(list(raw.keys()), CTA_COLUMN_CANDIDATES)
        row["CTAクリック数"] = raw.get(cta_key, "0").strip() if cta_key else "0"

        url = row["article_url"].strip()
        if not url:
            continue
        result[url] = {
            "PV":             to_float(row["PV"]),
            "アクティブユーザー": to_float(row["アクティブユーザー"]),
            "平均エンゲージメント": to_float(row["平均エンゲージメント"]),
            "イベント数":      to_float(row["イベント数"]),
            "キーイベント":    to_float(row["キーイベント"]),
            "CTAクリック数":   to_float(row["CTAクリック数"]),
        }
    return result


def load_gsc() -> dict[str, dict]:
    rows = load_csv(GSC_PATH)
    result = {}
    for raw in rows:
        row = normalize_row(raw, GSC_COLUMN_MAP)
        url = row["article_url"].strip()
        if not url:
            continue
        result[url] = {
            "インプレッション": to_float(row["インプレッション"]),
            "記事クリック数":   to_float(row["記事クリック数"]),
            "記事CTR":     to_float(row["記事CTR"]),
            "掲載順位":     to_float(row["掲載順位"]),
        }
    return result


def load_epv() -> dict[str, float]:
    rows = load_csv(EPV_PATH)
    result = {}
    for raw in rows:
        row = normalize_row(raw, EPV_COLUMN_MAP)
        url = row["article_url"].strip()
        if not url:
            continue
        result[url] = to_float(row["monthly_expected_pv"])
    return result


# ─────────────────────────────────────────────
# レポート生成
# ─────────────────────────────────────────────

def build_report() -> list[dict]:
    today = date.today()

    ga4 = load_ga4()
    gsc = load_gsc()
    epv = load_epv()

    # 全URLの和集合を主キーとして結合
    all_urls = sorted(set(ga4) | set(gsc) | set(epv))

    ga4_zero = {"PV": 0, "アクティブユーザー": 0, "平均エンゲージメント": 0,
                "イベント数": 0, "キーイベント": 0, "CTAクリック数": 0}
    gsc_zero = {"インプレッション": 0, "記事クリック数": 0, "記事CTR": 0, "掲載順位": 0}

    rows = []
    for url in all_urls:
        g = ga4.get(url, ga4_zero)
        s = gsc.get(url, gsc_zero)
        monthly = epv.get(url, 0.0)

        pv          = g["PV"]
        expected_pv = round(calc_expected_pv(monthly, today), 1)
        pv_diff     = round(pv - expected_pv, 1)

        if expected_pv != 0:
            zougen   = round((pv - expected_pv) / expected_pv, 4)
            pace     = round(pv / expected_pv, 4)
        else:
            zougen   = ""
            pace     = ""

        engage = g["平均エンゲージメント"]

        rows.append({
            "article_url":     url,
            "PV":              pv,
            "期待PV":          expected_pv,
            "PV差分":          pv_diff,
            "増減率":          zougen,
            "ペース比":        pace,
            "ランク":          None,          # 後で付与
            "アクティブユーザー": g["アクティブユーザー"],
            "平均エンゲージメント": engage,
            "エンゲージ評価":  evaluate_engagement(engage),
            "イベント数":      g["イベント数"],
            "キーイベント":    g["キーイベント"],
            "インプレッション": s["インプレッション"],
            "記事クリック数":   s["記事クリック数"],
            "CTAクリック数":   g["CTAクリック数"],
            "記事CTR":     s["記事CTR"],
            "掲載順位":     s["掲載順位"],
        })

    # ランク付け: ペース比の高い順（空欄は末尾）
    def pace_sort_key(r):
        p = r["ペース比"]
        return (0, -p) if isinstance(p, (int, float)) else (1, 0)

    rows.sort(key=pace_sort_key)
    for i, row in enumerate(rows, start=1):
        row["ランク"] = i

    return rows


# ─────────────────────────────────────────────
# 出力
# ─────────────────────────────────────────────

OUTPUT_COLUMNS = [
    "article_url", "PV", "期待PV", "PV差分", "増減率", "ペース比", "ランク",
    "アクティブユーザー", "平均エンゲージメント", "エンゲージ評価",
    "イベント数", "キーイベント", "インプレッション", "記事クリック数",
    "CTAクリック数", "記事CTR", "掲載順位",
]


def write_report(rows: list[dict]):
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def preview(rows: list[dict], n: int = 3):
    """先頭 n 件を簡易表示する。"""
    col_widths = {c: max(len(c), 6) for c in OUTPUT_COLUMNS}
    header = "  ".join(c.ljust(col_widths[c]) for c in OUTPUT_COLUMNS)
    print(header)
    print("-" * len(header))
    for row in rows[:n]:
        line = "  ".join(
            str(row.get(c, "")).ljust(col_widths[c]) for c in OUTPUT_COLUMNS
        )
        print(line)


def main():
    print("=== CSV集計レポート生成 ===")
    print(f"読込: {GA4_PATH}")
    print(f"読込: {GSC_PATH}")
    print(f"読込: {EPV_PATH}")

    try:
        rows = build_report()
    except FileNotFoundError as e:
        print(f"\n[エラー] ファイルが見つかりません: {e}")
        print("input/ フォルダに ga4.csv / gsc.csv / expected_pv.csv を配置してください。")
        return
    except Exception as e:
        print(f"\n[エラー] {e}")
        return

    write_report(rows)
    print(f"\n出力完了: {OUTPUT_PATH}")
    print(f"行数: {len(rows)} 記事")
    print("\n── プレビュー（先頭3件）──")
    preview(rows)


if __name__ == "__main__":
    main()
