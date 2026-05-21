#!/bin/bash
# SPROUT 自動集計スクリプト（Mac でダブルクリック実行）
cd "$(dirname "$0")"

echo "======================================"
echo "  SPROUT 自動集計・データ分析"
echo "======================================"
echo ""

# Python 確認
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 が見つかりません。インストールしてください。"
  read -p "Enterキーで閉じる..."
  exit 1
fi

# 実行
python3 src/sprout_analyzer.py --output

echo ""
echo "────────────────────────────────────"
echo " Google スプレッドシートにも反映する場合:"
echo "   python3 src/sprout_analyzer.py --sheets"
echo "────────────────────────────────────"
read -p "Enterキーで閉じる..."
