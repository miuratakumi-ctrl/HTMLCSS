# SPROUT 自動集計・データ分析ツール

SNS投稿管理・クラウドファンディング・フォロワー推移を自動集計し、Google スプレッドシートに同期するツールです。

---

## フォルダ構成

```
HTMLCSS/
├── input/                    ← データを入力するCSVを置く
│   ├── posts.csv             　投稿データ（いいね・インプレッション等）
│   ├── cf_supporters.csv     　CF支援者データ
│   └── followers.csv         　フォロワー推移データ
├── output/                   ← 集計結果CSVが出力される
├── config/
│   └── sprout_config.json    ← 設定ファイル（CF目標額・スプレッドシートID等）
├── credentials/
│   └── service_account.json  ← Google API認証ファイル（手順参照）
├── src/
│   └── sprout_analyzer.py    ← 分析スクリプト本体
└── run_sprout.command         ← Mac でダブルクリック実行
```

---

## 使い方

### 1. CSVにデータを入力する

#### `input/posts.csv`（投稿管理）
| 列名 | 内容 | 例 |
|------|------|-----|
| date | 投稿日（YYYY-MM-DD） | 2024-05-01 |
| platform | SNS媒体 | Instagram / Twitter / YouTube |
| post_type | 投稿種別 | 画像 / リール / テキスト / 動画 |
| likes | いいね数 | 120 |
| comments | コメント数 | 15 |
| shares | シェア数 | 8 |
| saves | 保存数 | 30 |
| impressions | インプレッション数 | 2500 |
| url | 投稿URL | https://... |
| memo | メモ | CF告知投稿 |

#### `input/cf_supporters.csv`（CF支援データ）
| 列名 | 内容 | 例 |
|------|------|-----|
| date | 支援日 | 2024-05-01 |
| return_tier | リターン金額 | 1000 |
| amount | 支援金額（1件） | 1000 |
| count | 支援件数 | 2 |
| memo | メモ | SNS経由 |

#### `input/followers.csv`（フォロワー推移）
| 列名 | 内容 | 例 |
|------|------|-----|
| date | 記録日 | 2024-05-01 |
| instagram | IGフォロワー数 | 2600 |
| twitter | TWフォロワー数 | 800 |
| youtube | YTフォロワー数 | 150 |
| tiktok | TTフォロワー数 | 0 |
| memo | メモ | 計測開始 |

---

### 2. 設定ファイルを編集する（初回のみ）

`config/sprout_config.json` を開いて以下を確認・変更：

```json
{
  "cf": {
    "goal_amount": 500000,          ← CF目標金額（円）
    "return_tiers": [1000, 5000, 10000, 30000, 100000]  ← リターン金額
  },
  "google_sheets": {
    "spreadsheet_id": "YOUR_SPREADSHEET_ID_HERE"  ← スプレッドシートIDに変更
  }
}
```

---

### 3. 実行する

```bash
# コンソールに集計結果を表示
python3 src/sprout_analyzer.py

# CSV ファイルも出力する
python3 src/sprout_analyzer.py --output

# Google スプレッドシートにも同期する
python3 src/sprout_analyzer.py --sheets

# 両方
python3 src/sprout_analyzer.py --output --sheets
```

Mac では `run_sprout.command` をダブルクリックでも実行できます。

---

## Google スプレッドシート連携手順

### Step 1: ライブラリのインストール

```bash
pip install gspread google-auth
```

### Step 2: Google Cloud でサービスアカウントを作成

1. [Google Cloud Console](https://console.cloud.google.com/) を開く
2. プロジェクトを作成（または既存を選択）
3. 「APIとサービス」→「ライブラリ」→「Google Sheets API」を有効化
4. 「APIとサービス」→「ライブラリ」→「Google Drive API」を有効化
5. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」
6. 作成したサービスアカウントの「キー」→「鍵を追加」→「JSON」
7. ダウンロードしたJSONを `credentials/service_account.json` に置く

### Step 3: スプレッドシートを共有する

1. Google スプレッドシートを新規作成（または既存のものを使用）
2. URLから **スプレッドシートID** をコピー
   ```
   https://docs.google.com/spreadsheets/d/【ここがID】/edit
   ```
3. `config/sprout_config.json` の `spreadsheet_id` に貼り付け
4. スプレッドシートの共有設定でサービスアカウントのメールアドレスを **編集者** として追加

### Step 4: 同期実行

```bash
python3 src/sprout_analyzer.py --sheets
```

---

## 集計・分析内容

| 分析項目 | 内容 |
|----------|------|
| **エンゲージメント率** | (いいね+コメント+シェア+保存) ÷ IMP × 100 |
| **CF達成率** | 累計支援額 ÷ 目標金額 × 100 |
| **リターン別売上** | 各リターン金額ごとの販売数・売上合計 |
| **プラットフォーム別集計** | 媒体ごとの投稿数・IMP合計・平均ENG率 |
| **週次集計** | 週ごとの投稿数・IMP・ENG率・CF支援額 |
| **フォロワー増減** | 記録日ごとの各SNSフォロワー数と増減 |

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `gspread` が見つからない | `pip install gspread google-auth` を実行 |
| `credentials/service_account.json` が見つからない | Google Cloud でサービスアカウントキーを作成 |
| スプレッドシートに書き込めない | サービスアカウントのメールをスプレッドシートの編集者に追加 |
| CSVが読み込めない | ファイル名・文字コード（UTF-8）を確認 |
