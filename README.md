# SEO Auto

## セットアップ（初回のみ）

1. このフォルダを **Desktop の `seo_auto` という名前** で保存します。
   ```
   ~/Desktop/seo_auto/
   ```
2. `run.command` を右クリック →「開く」で初回の実行許可を与えます。

---

## 使い方

```
Desktop/
└── seo_auto/         ← Finder でここを開くだけ
    ├── input/        ← 処理したいファイルをここに置く
    ├── output/       ← 結果がここに出てくる
    ├── src/          ← スクリプト本体（通常は触らない）
    ├── run.command   ← ダブルクリックで実行
    └── README.md     ← このファイル
```

### ステップ

1. **Finder** で `Desktop/seo_auto` を開く
2. 処理したいファイルを **`input/`** フォルダに入れる
3. **`run.command`** をダブルクリック
4. 結果を **`output/`** フォルダで確認

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `run.command` が開けない | 右クリック →「開く」→「開く」で許可 |
| `python3: command not found` | [python.org](https://www.python.org/) から Python 3 をインストール |
| 結果が `output/` に出ない | `input/` にファイルが入っているか確認 |

---

**保存場所は常に `~/Desktop/seo_auto` だけです。他の場所には何も置きません。**
