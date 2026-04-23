#!/bin/bash
# ダブルクリックで GA4取得 → GSC取得 → 集計 → report.csv 更新 を一括実行

cd "$(dirname "$0")"

echo "=== SEO Auto 起動中 ==="
python3 src/run_all.py

echo ""
echo "完了しました。output/report.csv を確認してください。"
read -p "Enter キーで終了..." _
