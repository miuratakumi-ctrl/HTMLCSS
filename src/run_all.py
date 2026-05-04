#!/usr/bin/env python3
"""
全ステップを一括実行する。

使い方:
  python3 src/run_all.py                    # 昨日基準で全ステップ実行
  python3 src/run_all.py --date 2026-04-30  # 指定日のデータを集計
  python3 src/run_all.py --skip-ahrefs      # Ahrefs 取得をスキップ
  python3 src/run_all.py --only-analyze     # 分析レポートのみ再生成

ステップ:
  1. GA4 データ取得        → input/ga4.csv
  2. GSC データ取得        → input/gsc.csv
  3. GA4/GSC 月次取得      → input/ga4_current_month.csv 等
  4. Ahrefs データ取得     → input/ahrefs_pages.csv
  5. 集計・レポート生成    → output/report.csv
  6. SEO 分析レポート生成  → output/seo_analysis.csv / backlink_targets.csv

ログ: logs/YYYY-MM-DD.log
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ── ロガー ────────────────────────────────────────────────────────────────────
log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_step(label, fn):
    logger.info(f"--- {label} 開始 ---")
    try:
        fn()
        logger.info(f"--- {label} 完了 ---")
    except Exception as exc:
        logger.error(f"--- {label} 失敗: {exc} ---", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="SEO Auto 全ステップ実行")
    parser.add_argument("--date", help="集計日 YYYY-MM-DD（省略時は昨日）")
    parser.add_argument("--skip-ahrefs", action="store_true",
                        help="Ahrefs データ取得をスキップ")
    parser.add_argument("--only-analyze", action="store_true",
                        help="SEO 分析レポートのみ再生成（API 呼び出しなし）")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None

    started_at = datetime.now()
    logger.info("=" * 60)
    logger.info(f"SEO Auto 開始  {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if target_date:
        logger.info(f"集計日: {target_date}")
    logger.info("=" * 60)

    try:
        from _config import load_config
        import fetch_ga4
        import fetch_gsc
        import fetch_monthly
        import fetch_ahrefs
        import main as aggregate
        import analyze_seo

        config = load_config()

        if args.only_analyze:
            run_step("SEO 分析レポート生成", analyze_seo.main)
        else:
            run_step("GA4 データ取得",
                     lambda: fetch_ga4.fetch(config, target_date=target_date))
            run_step("GSC データ取得",
                     lambda: fetch_gsc.fetch(config, target_date=target_date))
            run_step("GA4/GSC 月次データ取得",
                     lambda: fetch_monthly.fetch(config, target_date=target_date))

            if not args.skip_ahrefs:
                run_step("Ahrefs データ取得",
                         lambda: fetch_ahrefs.fetch(config))

            run_step("集計・レポート生成", aggregate.main)
            run_step("SEO 分析レポート生成", analyze_seo.main)

        elapsed = (datetime.now() - started_at).seconds
        logger.info("=" * 60)
        logger.info(f"✓ 全ステップ完了  所要 {elapsed}s")
        logger.info("  output/report.csv        — PV 集計レポート")
        logger.info("  output/seo_analysis.csv  — リライト優先度分析")
        logger.info("  output/backlink_targets.csv — 被リンク獲得候補")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"✗ 失敗: {exc}")
        logger.error(f"  詳細は {log_file} を確認してください")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
