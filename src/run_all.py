#!/usr/bin/env python3
"""
1コマンドで GA4取得 → GSC取得 → 集計 → report.csv 更新 を実行する。
ログは logs/YYYY-MM-DD.log に書き出す。
"""

import logging
import os
import sys
from datetime import datetime

_SRC = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_SRC)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ── ロガー設定 ────────────────────────────────────────────────────────────────
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
        logger.error(f"--- {label} 失敗 ---")
        logger.error(str(exc), exc_info=True)
        raise


def main():
    started_at = datetime.now()
    logger.info("=" * 60)
    logger.info(f"SEO Auto 自動実行 開始  {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        from _config import load_config
        import fetch_ga4
        import fetch_gsc
        import main as aggregate

        config = load_config()

        run_step("GA4 データ取得", lambda: fetch_ga4.fetch(config))
        run_step("GSC データ取得", lambda: fetch_gsc.fetch(config))
        run_step("集計・レポート更新", aggregate.main)

        elapsed = (datetime.now() - started_at).seconds
        logger.info("=" * 60)
        logger.info(f"✓ 全ステップ完了  所要 {elapsed}s")
        logger.info(f"  output/report.csv を確認してください")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"✗ 実行失敗: {exc}")
        logger.error(f"  詳細は {log_file} を確認してください")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
