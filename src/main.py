"""
GA4 / GSC / expected_pv を突合して output/report.csv を生成するスクリプト
"""

import os
import calendar
from datetime import date

import pandas as pd

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
    "PV": ["PV", "pv", "ページビュー", "page_views", "pageviews", "セッション"],
    "アクティブユーザー": [
        "アクティブユーザー",
        "active_users",
        "activeUsers",
        "ユーザー",
        "users",
    ],
    "平均エンゲージメント": [
        "平均エンゲージメント",
        "avg_engagement_time",
        "平均エンゲージメント時間",
        "averageEngagementTime",
        "engagement_time",
        "エンゲージメント時間",
    ],
    "イベント数": ["イベント数", "event_count", "events", "eventCount"],
    "キーイベント": [
        "キーイベント",
        "key_events",
        "conversions",
        "コンバージョン",
        "keyEvents",
    ],
    # CTAクリック数は CTA_COLUMN_CANDIDATES で別管理
}

# GSC 列名候補
GSC_COLUMN_MAP = {
    "article_url": ["article_url", "URL", "url", "ページ", "page", "ページURL", "記事URL"],
    "インプレッション": [
        "インプレッション",
        "impressions",
        "Impressions",
        "表示回数",
    ],
    "記事クリック数": [
        "記事クリック数",
        "clicks",
        "Clicks",
        "クリック数",
        "クリック",
    ],
    "記事CTR": [
        "記事CTR",
        "ctr",
        "CTR",
        "クリック率",
    ],
    "掲載順位": [
        "掲載順位",
        "position",
        "Position",
        "平均掲載順位",
        "avg_position",
    ],
}

# expected_pv 列名候補
EPV_COLUMN_MAP = {
    "article_url": ["article_url", "URL", "url", "記事URL", "page_url"],
    "monthly_expected_pv": [
        "monthly_expected_pv",
        "expected_pv",
        "月間期待PV",
        "目標PV",
        "target_pv",
    ],
}

# ─────────────────────────────────────────────
# ユーティリティ: 列名の正規化
# ─────────────────────────────────────────────

def resolve_column(df: pd.DataFrame, candidates: list[str], default_name: str) -> str:
    """候補リストの中で DataFrame に実在する最初の列名を返す。なければ default_name を返す。"""
    for c in candidates:
        if c in df.columns:
            return c
    return default_name


def normalize_columns(df: pd.DataFrame, column_map: dict[str, list[str]]) -> pd.DataFrame:
    """column_map に従って列名を正規化（リネーム）した DataFrame を返す。"""
    rename = {}
    for target, candidates in column_map.items():
        found = resolve_column(df, candidates, "")
        if found and found != target:
            rename[found] = target
    return df.rename(columns=rename)


def to_numeric_safe(series: pd.Series) -> pd.Series:
    """文字列混じりの列を数値型に変換。変換できない値は 0 にする。"""
    return pd.to_numeric(series, errors="coerce").fillna(0)


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
    elapsed_days = today.day
    return monthly * (elapsed_days / days_in_month)


# ─────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────

def load_ga4() -> pd.DataFrame:
    df = pd.read_csv(GA4_PATH, dtype=str)
    df.columns = df.columns.str.strip()

    # CTAクリック数列を探す（CTA_COLUMN_CANDIDATES で管理）
    cta_col = resolve_column(df, CTA_COLUMN_CANDIDATES, "")
    if cta_col and cta_col != "CTAクリック数":
        df = df.rename(columns={cta_col: "CTAクリック数"})
    elif not cta_col:
        df["CTAクリック数"] = "0"

    df = normalize_columns(df, GA4_COLUMN_MAP)
    df["article_url"] = df["article_url"].str.strip()

    for col in ["PV", "アクティブユーザー", "平均エンゲージメント", "イベント数", "キーイベント", "CTAクリック数"]:
        if col in df.columns:
            df[col] = to_numeric_safe(df[col])
        else:
            df[col] = 0

    return df[["article_url", "PV", "アクティブユーザー", "平均エンゲージメント", "イベント数", "キーイベント", "CTAクリック数"]]


def load_gsc() -> pd.DataFrame:
    df = pd.read_csv(GSC_PATH, dtype=str)
    df.columns = df.columns.str.strip()
    df = normalize_columns(df, GSC_COLUMN_MAP)
    df["article_url"] = df["article_url"].str.strip()

    for col in ["インプレッション", "記事クリック数", "記事CTR", "掲載順位"]:
        if col in df.columns:
            df[col] = to_numeric_safe(df[col])
        else:
            df[col] = 0

    return df[["article_url", "インプレッション", "記事クリック数", "記事CTR", "掲載順位"]]


def load_epv() -> pd.DataFrame:
    df = pd.read_csv(EPV_PATH, dtype=str)
    df.columns = df.columns.str.strip()
    df = normalize_columns(df, EPV_COLUMN_MAP)
    df["article_url"] = df["article_url"].str.strip()
    df["monthly_expected_pv"] = to_numeric_safe(df["monthly_expected_pv"])
    return df[["article_url", "monthly_expected_pv"]]


def build_report() -> pd.DataFrame:
    today = date.today()

    ga4 = load_ga4()
    gsc = load_gsc()
    epv = load_epv()

    # article_url を主キーとして結合（outer で欠損も保持）
    df = ga4.merge(gsc, on="article_url", how="outer")
    df = df.merge(epv, on="article_url", how="outer")

    # 欠損数値を 0 で埋める
    numeric_cols = [
        "PV", "アクティブユーザー", "平均エンゲージメント", "イベント数",
        "キーイベント", "CTAクリック数", "インプレッション", "記事クリック数",
        "記事CTR", "掲載順位", "monthly_expected_pv",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # ── 計算列 ──────────────────────────────
    df["期待PV"] = df["monthly_expected_pv"].apply(
        lambda m: round(calc_expected_pv(m, today), 1)
    )

    df["PV差分"] = df["PV"] - df["期待PV"]

    # 0除算ガード: 期待PV が 0 の行は NaN → 空欄
    df["増減率"] = df.apply(
        lambda r: (r["PV"] - r["期待PV"]) / r["期待PV"] if r["期待PV"] != 0 else None,
        axis=1,
    )

    df["ペース比"] = df.apply(
        lambda r: r["PV"] / r["期待PV"] if r["期待PV"] != 0 else None,
        axis=1,
    )

    # ランク: ペース比の高い順（NaN は末尾）
    df["ランク"] = df["ペース比"].rank(ascending=False, na_option="bottom").astype(int)

    df["エンゲージ評価"] = df["平均エンゲージメント"].apply(evaluate_engagement)

    # ── 出力列順 ────────────────────────────
    output_cols = [
        "article_url",
        "PV",
        "期待PV",
        "PV差分",
        "増減率",
        "ペース比",
        "ランク",
        "アクティブユーザー",
        "平均エンゲージメント",
        "エンゲージ評価",
        "イベント数",
        "キーイベント",
        "インプレッション",
        "記事クリック数",
        "CTAクリック数",
        "記事CTR",
        "掲載順位",
    ]

    report = df[output_cols].copy()

    # 増減率・ペース比を小数点2桁に丸める
    report["増減率"] = report["増減率"].apply(
        lambda x: round(x, 4) if pd.notna(x) else ""
    )
    report["ペース比"] = report["ペース比"].apply(
        lambda x: round(x, 4) if pd.notna(x) else ""
    )

    # ランク順にソート
    report = report.sort_values("ランク").reset_index(drop=True)

    return report


def main():
    print("=== CSV集計レポート生成 ===")
    print(f"読込: {GA4_PATH}")
    print(f"読込: {GSC_PATH}")
    print(f"読込: {EPV_PATH}")

    try:
        report = build_report()
    except FileNotFoundError as e:
        print(f"\n[エラー] ファイルが見つかりません: {e}")
        print("input/ フォルダに ga4.csv / gsc.csv / expected_pv.csv を配置してください。")
        return
    except KeyError as e:
        print(f"\n[エラー] 列名が見つかりません: {e}")
        print("CSVの列名を確認し、main.py の列名候補リストを更新してください。")
        return

    report.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n出力完了: {OUTPUT_PATH}")
    print(f"行数: {len(report)} 記事")
    print("\n── プレビュー（先頭3件）──")
    print(report.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
