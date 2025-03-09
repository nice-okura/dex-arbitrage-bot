# DEXアービトラージボット

Polygonチェーン上で動作するDEXアービトラージボットです。価格モニタリングと裁定機会検出の機能を備えています。

## 機能

1. **価格モニタリング**
   - 複数のDEXとCEXから価格データをリアルタイムで取得
   - The GraphとPolygonScan APIを利用したオンチェーンデータの取得
   - 価格データをRedisとSQLiteに保存

2. **裁定機会検出**
   - 取引所間の価格差を監視
   - 手数料とスリッページを考慮した利益計算
   - 設定可能な裁定閾値（デフォルト0.5%）
   - Slack通知機能

## インストール方法

### 前提条件

- Python 3.8以上
- Redis（オプショナル、ローカルキャッシュも利用可能）

### 手順

1. リポジトリをクローン
   ```
   git clone https://github.com/yourusername/dex-arbitrage-bot.git
   cd dex-arbitrage-bot
   ```

2. 仮想環境を作成
   ```
   python -m venv venv
   source venv/bin/activate  # Linuxの場合
   venv\Scripts\activate     # Windowsの場合
   ```

3. 依存ライブラリをインストール
   ```
   pip install -r requirements.txt
   ```

4. 設定ファイルを作成
   - `.env.example`を`.env`にコピーして必要な設定を行う
   ```
   cp .env.example .env
   ```
   - 各APIキーやSlack Webhook URLなどを設定

## 使用方法

### 実行方法

```
python main.py
```

### 設定パラメータ

- `PRICE_UPDATE_INTERVAL`: 価格更新間隔（秒）
- `ARBITRAGE_THRESHOLD`: 裁定閾値（%）
- `SLIPPAGE_TOLERANCE`: スリッページ許容値（%）
- `MIN_PROFIT_USD`: 最小利益額（USD）
- `NOTIFICATION_COOLDOWN`: 通知クールダウン（秒）
- `TOKEN_PAIRS`: 監視対象の通貨ペア（カンマ区切り）
- `POLYGON_RPC_URL`: Polygon RPCのURL
- `SLACK_WEBHOOK_URL`: Slack通知用Webhook URL

## プロジェクト構成

```
dex-arbitrage-bot/
├── main.py              # メインプログラム
├── src/
│   ├── config.py        # 設定モジュール
│   ├── price_monitoring.py # 価格モニタリングモジュール
│   ├── arbitrage_detection.py # 裁定機会検出モジュール
│   ├── data_management.py # データ管理モジュール
│   ├── notification.py  # 通知モジュール
│   └── contracts.py     # コントラクト関連モジュール
├── data/                # データ保存ディレクトリ
│   └── arbitrage.db     # SQLiteデータベース
├── logs/                # ログディレクトリ
│   └── app.log          # アプリケーションログ
├── .env                 # 環境変数設定ファイル
├── requirements.txt     # 依存ライブラリ
└── README.md            # ドキュメント
```

## 拡張性

このボットは以下の拡張が容易になるように設計されています：

1. **監視対象の通貨ペアの追加**
   - `.env`ファイルの`TOKEN_PAIRS`パラメータを更新

2. **新しいDEXまたはCEXの追加**
   - `src/config.py`の`_load_dexes()`または`_load_cexes()`メソッドを更新

3. **通知方法の拡張**
   - `src/notification.py`に新しい通知クラスを追加

4. **AWS環境への移行**
   - SQLiteからRDSへ
   - ローカルスクリプトからLambdaへ

## 注意事項

- このボットは情報提供目的のみで利用してください
- 実際の取引を行う前にリスク管理を徹底してください
- APIキーやウォレットの秘密鍵は安全に管理してください

## ライセンス

MIT