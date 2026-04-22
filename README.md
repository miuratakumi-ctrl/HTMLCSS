# CSV 記事集計ツール

## このツールの目的

GA4・GSC・expected_pv の3つの CSV を `input/` フォルダに置いて `main.py` を実行するだけで、  
記事URL単位の集計表（`output/report.csv`）を生成します。  
毎回同じ列順で出力されるため、Googleスプレッドシートへの貼り付けをそのまま定型化できます。

---

## フォルダ構成

```
プロジェクトルート/
├── input/
│   ├── ga4.csv
│   ├── gsc.csv
│   └── expected_pv.csv
├── output/
│   └── report.csv          ← ここに結果が出力される
├── src/
│   └── main.py
├── requirements.txt
└── README.md
```

---

## input フォルダに置くファイル

| ファイル名 | 内容 |
|---|---|
| `ga4.csv` | GA4 からエクスポートした記事URL単位のデータ |
| `gsc.csv` | Google Search Console からエクスポートした記事URL単位のデータ |
| `expected_pv.csv` | 記事ごとの月間期待PVを定義したファイル |

### GA4 CSV の想定列

| 列名（例） | 内容 |
|---|---|
| `article_url` | 記事URL（主キー） |
| `PV` | ページビュー数 |
| `アクティブユーザー` | アクティブユーザー数 |
| `平均エンゲージメント` | 平均エンゲージメント時間（秒） |
| `イベント数` | イベント総数 |
| `キーイベント` | キーイベント数（コンバージョン） |
| `CTAクリック数` | CTAボタンクリック数 |

### GSC CSV の想定列

| 列名（例） | 内容 |
|---|---|
| `article_url` | 記事URL（主キー） |
| `インプレッション` | 検索インプレッション数 |
| `記事クリック数` | 検索クリック数 |
| `記事CTR` | クリック率（0〜1の小数） |
| `掲載順位` | 平均掲載順位 |

### expected_pv.csv のサンプル

```csv
article_url,monthly_expected_pv
https://example.com/article-01,1500
https://example.com/article-02,1000
https://example.com/article-03,600
```

- `article_url`: 記事の完全URL（GA4・GSC と完全一致させること）
- `monthly_expected_pv`: その記事の月間目標PV（整数）

---

## 実行方法

### 1. Python のインストール

Python 3.10 以上をインストールしてください。  
https://www.python.org/downloads/

インストール確認:
```bash
python --version
```

### 2. 依存ライブラリのインストール

プロジェクトルートで以下を実行してください:
```bash
pip install -r requirements.txt
```

### 3. main.py の実行

```bash
python src/main.py
```

実行後、`output/report.csv` に結果が出力されます。

---

## output/report.csv に出る列

| 列名 | 内容 |
|---|---|
| `article_url` | 記事URL |
| `PV` | ページビュー数（GA4） |
| `期待PV` | 当月経過日数ベースの期待PV |
| `PV差分` | PV − 期待PV |
| `増減率` | (PV − 期待PV) / 期待PV |
| `ペース比` | PV / 期待PV |
| `ランク` | ペース比の高い順の順位 |
| `アクティブユーザー` | アクティブユーザー数（GA4） |
| `平均エンゲージメント` | 平均エンゲージメント時間・秒（GA4） |
| `エンゲージ評価` | 高／中／低（120秒以上＝高、60〜120秒＝中、60秒未満＝低） |
| `イベント数` | イベント数（GA4） |
| `キーイベント` | キーイベント数（GA4） |
| `インプレッション` | 検索インプレッション数（GSC） |
| `記事クリック数` | 検索クリック数（GSC） |
| `CTAクリック数` | CTAクリック数（GA4） |
| `記事CTR` | クリック率（GSC） |
| `掲載順位` | 平均掲載順位（GSC） |

出力はペース比の高い順（ランク昇順）にソートされます。

---

## 期待PV の計算式

```
期待PV = monthly_expected_pv × (当月の経過日数 / 当月の日数)
```

例: 月間期待PV が 1,500 で、4月22日（30日中22日経過）の場合
```
期待PV = 1500 × (22 / 30) = 1100
```

---

## よくあるエラーと対処法

### `FileNotFoundError: input/ga4.csv が見つかりません`

**原因**: ファイルが `input/` フォルダに置かれていない  
**対処**: `input/ga4.csv`（または `gsc.csv` / `expected_pv.csv`）を配置してから再実行

---

### `KeyError: '列名'`

**原因**: CSVの列名がスクリプトの候補リストに一致しない  
**対処**: `src/main.py` の `GA4_COLUMN_MAP` / `GSC_COLUMN_MAP` / `EPV_COLUMN_MAP` に  
実際の列名を追記してください

---

### 結果が 0 ばかりになる

**原因**: 数値列に文字列や単位が混入している（例: `1,200` や `1200回`）  
**対処**: CSVを開いてカンマや単位を取り除いてから再実行

---

### article_url が突合されない

**原因**: URL の末尾スラッシュや大文字小文字の違い  
**対処**: 3ファイルの URL 表記を統一する（スクリプトは前後空白のみ自動除去）

---

### CTAクリック数のイベント名を変更したい

`src/main.py` の先頭にある `CTA_COLUMN_CANDIDATES` リストに新しい列名を追加してください:

```python
CTA_COLUMN_CANDIDATES = [
    "CTAクリック数",
    "新しいイベント名",   # ← ここに追加
    ...
]
```
