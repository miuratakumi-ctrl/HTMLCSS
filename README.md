# SEO Auto

GA4 / GSC のデータを毎日自動取得し、想定 PV と突合して `output/report.csv` を自動更新するツールです。

---

## フォルダ構成

```
~/Desktop/seo_auto/
├── config.env              ← GA4・GSC の設定（要編集）
├── credentials/
│   └── service_account.json  ← Google 認証 JSON（要配置）
├── input/
│   ├── expected_pv.csv     ← 手元管理の想定 PV（要作成）
│   ├── ga4.csv             ← 自動取得（fetch_ga4.py が更新）
│   └── gsc.csv             ← 自動取得（fetch_gsc.py が更新）
├── output/
│   └── report.csv          ← 自動生成レポート
├── logs/                   ← 実行ログ（日付.log）
├── src/
│   ├── _config.py          ← 設定ローダー
│   ├── fetch_ga4.py        ← GA4 API 取得
│   ├── fetch_gsc.py        ← GSC API 取得
│   ├── main.py             ← CSV 突合 → report.csv 生成
│   └── run_all.py          ← 全ステップを一括実行
├── launchd/
│   ├── com.seoauto.daily.plist  ← 定時実行の設定テンプレート
│   ├── install.sh          ← 定時実行の登録スクリプト
│   └── run_daily.sh        ← launchd から呼ばれる実行スクリプト
├── requirements.txt
└── run.command             ← Finder からダブルクリックで全実行
```

---

## セットアップ（初回のみ）

### 1. リポジトリを Desktop に配置

```bash
git clone https://github.com/miuratakumi-ctrl/HTMLCSS.git ~/Desktop/seo_auto
cd ~/Desktop/seo_auto
```

### 2. Python パッケージのインストール

```bash
pip3 install -r requirements.txt
```

### 3. 認証 JSON の配置

Google Cloud Console でサービスアカウントを作成し、鍵ファイル（JSON）をダウンロードして以下に置きます。

```
~/Desktop/seo_auto/credentials/service_account.json
```

> サービスアカウントには GA4 プロパティと GSC プロパティへのアクセス権を付与してください。

### 4. config.env の設定

`config.env` をテキストエディタで開き、4 箇所を書き換えます。

```
CREDENTIALS_JSON=credentials/service_account.json  # 変更不要

GA4_PROPERTY_ID=properties/123456789   # GA4 管理画面のプロパティ ID
GSC_PROPERTY=https://example.com/      # GSC のプロパティ URL（または sc-domain:...）
GA4_CTA_EVENT=cta_click                # CTA として計測しているイベント名
DAYS_BACK=28                           # 集計期間（日数）
```

**GA4 プロパティ ID の確認方法**
GA4 管理画面 → 管理 → プロパティ設定 → プロパティ ID（数字のみ）を `properties/数字` の形式で入力。

**GSC プロパティの確認方法**
Search Console 画面左上のプロパティセレクタに表示されている文字列をそのまま入力。

### 5. expected_pv.csv の準備

`input/expected_pv.csv` を以下の形式で作成します（手元で管理）。

```csv
article_url,monthly_expected_pv
https://example.com/article-01,3000
https://example.com/article-02,2000
```

---

## 1 回だけ手動で動作確認する方法

```bash
cd ~/Desktop/seo_auto
python3 src/run_all.py
```

成功すると以下のように表示されます。

```
2025-01-01 08:00:00 [INFO] --- GA4 データ取得 開始 ---
2025-01-01 08:00:03 [INFO] GA4: 42 件 → input/ga4.csv
2025-01-01 08:00:03 [INFO] --- GA4 データ取得 完了 ---
...
2025-01-01 08:00:07 [INFO] ✓ 全ステップ完了  所要 7s
```

`output/report.csv` を Finder で確認してください。

---

## 毎日自動実行の設定方法（launchd）

ターミナルで以下を 1 回だけ実行します。

```bash
bash ~/Desktop/seo_auto/launchd/install.sh
```

これで **毎日 08:00** に自動実行されます。

**自動実行を止めたい場合**

```bash
launchctl unload ~/Library/LaunchAgents/com.seoauto.daily.plist
```

**実行時刻を変更したい場合**

`launchd/com.seoauto.daily.plist` の `Hour` の値を変更してから `install.sh` を再実行します。

---

## 失敗時の確認場所

| 確認先 | 内容 |
|--------|------|
| `logs/YYYY-MM-DD.log` | 実行ログ（成功・失敗・エラー詳細） |
| `logs/launchd_stderr.log` | 定時実行時のエラー出力 |
| `logs/launchd_stdout.log` | 定時実行時の標準出力 |

よくあるエラーと対処：

| エラーメッセージ | 対処 |
|-----------------|------|
| `config.env に必須項目が不足` | `config.env` を開いて未設定の項目を入力 |
| `service_account.json が見つからない` | `credentials/` に JSON ファイルを配置 |
| `Permission denied` | GA4 / GSC のプロパティにサービスアカウントを追加 |
| `ModuleNotFoundError` | `pip3 install -r requirements.txt` を再実行 |

---

## report.csv の列定義

| 列名 | 内容 |
|------|------|
| `article_url` | 記事 URL |
| `monthly_expected_pv` | 月間想定 PV（手元管理） |
| `pv` | 実 PV（GA4、集計期間内） |
| `pv_rate_%` | PV 達成率（実 PV / 想定 PV × 100） |
| `active_users` | アクティブユーザー数 |
| `avg_engagement_sec` | 平均エンゲージメント時間（秒） |
| `event_count` | イベント数 |
| `key_events` | キーイベント数 |
| `cta_clicks` | CTA クリック数（`GA4_CTA_EVENT` で指定したイベント） |
| `impressions` | 表示回数（GSC） |
| `clicks` | クリック数（GSC） |
| `ctr_%` | クリック率 ％（GSC） |
| `position` | 平均掲載順位（GSC） |
| `data_period` | 集計期間（開始日 ~ 終了日） |

---

**保存場所は常に `~/Desktop/seo_auto` だけです。**
