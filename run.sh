#!/bin/bash
# ダブルクリックまたはターミナルで実行するだけで集計が完了します
cd "$(dirname "$0")"
python src/main.py && python src/check_report.py
echo ""
echo "完了しました。output/report.csv を確認してください。"
read -p "Enterキーで閉じる..."
