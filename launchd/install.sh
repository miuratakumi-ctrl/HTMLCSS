#!/bin/bash
# launchd に SEO Auto の定時実行を登録する（毎日 08:00）
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.seoauto.daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.seoauto.daily.plist"

# {{HOME}} を実際のホームディレクトリに置換して LaunchAgents に配置
sed "s|{{HOME}}|$HOME|g" "$PLIST_SRC" > "$PLIST_DST"

# 既に登録済みの場合は一度解除してから再登録
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "✓ 自動実行を設定しました（毎日 08:00）"
echo "  設定ファイル : $PLIST_DST"
echo "  解除するには : launchctl unload $PLIST_DST"
