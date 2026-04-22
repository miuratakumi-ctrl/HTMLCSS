#!/bin/bash
# ダブルクリックで実行できます（Finder からそのまま起動）

# スクリプトのある場所に移動
cd "$(dirname "$0")"

echo "=== SEO Auto 起動中 ==="
python3 src/main.py

echo ""
echo "完了しました。このウィンドウを閉じてください。"
read -p "Enter キーで終了..." _
