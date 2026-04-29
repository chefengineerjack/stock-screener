# Stock Screener

テクニカル指標ベースの株式スクリーニングアプリ。複数の条件パターンを登録し、米国株（S&P500）または日本株（J-Quants API）を対象に合致銘柄をピックアップします。

## 技術スタック

- **バックエンド**: FastAPI (Python 3.11+) + SQLite
- **フロントエンド**: React + TypeScript (Vite) + Tailwind CSS
- **米国株データ**: yfinance
- **日本株データ**: J-Quants API
- **テクニカル指標**: pandas-ta

## プリセット条件（16種類）

| カテゴリ | 条件 |
|---|---|
| RSI | RSI売られすぎ(< 30)、RSI買われすぎ(> 70) |
| 移動平均 | ゴールデンクロス、デッドクロス、SMA200上抜け/下抜け、SMA50上抜け |
| 価格帯 | 52週高値付近、52週安値付近、5日間+5%以上、5日間-5%以下 |
| 出来高 | 出来高急増（20日平均×2） |
| MACD | MACDゴールデンクロス、MACDデッドクロス |
| ボリンジャーバンド | 上限突破、下限割れ |

## セットアップ

### 1. リポジトリクローン

```bash
git clone <repository-url>
cd stock-screener
```

### 2. 環境変数設定

```bash
cp .env.example .env
```

`.env` を編集し、J-Quants APIの認証情報を設定してください（日本株を使用する場合）。

```
JQUANTS_EMAIL=your_email@example.com
JQUANTS_PASSWORD=your_password
DATABASE_URL=sqlite:///./screener.db
```

### 3. バックエンドセットアップ

```bash
cd backend
pip install -r requirements.txt
```

### 4. フロントエンドセットアップ

```bash
cd frontend
npm install
```

## 起動方法

### バックエンド

```bash
cd /path/to/stock-screener
uvicorn backend.main:app --reload
```

API は http://localhost:8000 で起動します。  
Swagger UI: http://localhost:8000/docs

### フロントエンド

```bash
cd frontend
npm run dev
```

フロントエンドは http://localhost:5173 で起動します。

## 使い方

1. 左サイドバーの「+ 新規」ボタンでスクリーニングパターンを作成
2. パターン名、対象市場（US/JP）、条件ロジック（AND/OR）を設定
3. プリセット条件からスクリーニング条件を選択
4. 保存後、「スクリーニング実行」ボタンをクリック
5. 結果テーブルに合致銘柄が表示される

## API エンドポイント

### パターン管理
- `GET /api/patterns` — 全パターン取得
- `POST /api/patterns` — パターン作成
- `PUT /api/patterns/{id}` — パターン更新
- `DELETE /api/patterns/{id}` — パターン削除

### スクリーニング
- `POST /api/screening/run` — スクリーニング実行
- `GET /api/screening/history` — 過去の実行結果一覧

## 注意事項

- **米国株**: yfinance は非公式APIです。S&P500全銘柄のスクリーニングには数分かかる場合があります
- **日本株**: J-Quants API の無料プランには API 呼び出し制限があります。キャッシュ機構を実装済みです
- pandas-ta で計算できない指標（データ不足など）は自動的にスキップされます
