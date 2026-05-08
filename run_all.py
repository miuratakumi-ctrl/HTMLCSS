#!/usr/bin/env python3
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
        logger.error(f"--- {label} 失敗: {exc} ---")
        logger.error(str(exc), exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="集計日 YYYY-MM-DD")
    args = parser.parse_args()
    target_date = date.fromisoformat(args.date) if args.date else None

    started_at = datetime.now()
    logger.info("=" * 60)
    logger.info(f"SEO Auto 自動実行 開始  {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if target_date:
        logger.info(f"集計日: {target_date}")
    logger.info("=" * 60)

    try:
        from _config import load_config
        import fetch_ga4
        import fetch_gsc
        import fetch_monthly
        import main as aggregate
        import weekly_report          # 週次レポート

        config = load_config()

        run_step("GA4 データ取得（日次）",   lambda: fetch_ga4.fetch(config, target_date=target_date))
        run_step("GSC データ取得（日次）",   lambda: fetch_gsc.fetch(config, target_date=target_date))
        run_step("GA4 月次データ取得",       lambda: fetch_monthly.fetch(config, target_date=target_date))
        run_step("集計・月次レポート更新",    aggregate.main)
        run_step("週次 click レポート生成",   lambda: weekly_report.main(end_date=target_date))  # ← 追加

        elapsed = (datetime.now() - started_at).seconds
        logger.info("=" * 60)
        logger.info(f"✓ 全ステップ完了  所要 {elapsed}s")
        logger.info(f"  output/report.csv         … 月次レポート")
        logger.info(f"  output/weekly_YYYY-MM-DD.csv … 週次clickレポート")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"✗ 失敗: {exc}")
        logger.error(f"  詳細は {log_file} を確認してください")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
