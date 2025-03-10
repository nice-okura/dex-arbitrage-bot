# DEXアービトラージボット

複数の取引所間の価格差を監視し、裁定取引の機会を検出するボットです。DEX（分散型取引所）とCEX（中央集権型取引所）間の価格差に対応しています。

## 機能

1. **価格モニタリング**
   - 複数のDEXとCEXから価格データをリアルタイムで取得
   - 各取引所のAPIを利用した安定的な価格取得
   - 価格データをRedisとSQLiteに保存

2. **裁定機会検出**
   - 取引所間の価格差を監視
   - 手数料とスリッページを考慮した利益計算
   - 設定可能な裁定閾値（デフォルト0.5%）
   - Slack通知機能

## 対応する取引所

### DEX（分散型取引所）
- Uniswap V3
- QuickSwap
- SushiSwap
- Curve
- Balancer

### CEX（中央集権型取引所）
- Bitbank
- BitFlyer
- Coincheck
- Zaif
- BitTrade

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
   - 各取引所のAPIキーやSlack Webhook URLなどを設定

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
│   └── notification.py  # 通知モジュール
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
   - `src/price_monitoring.py`に対応する取得メソッドを追加

3. **通知方法の拡張**
   - `src/notification.py`に新しい通知クラスを追加

## 注意事項

- このボットは情報提供目的のみで利用してください
- 実際の取引を行う前にリスク管理を徹底してください
- APIキーやウォレットの秘密鍵は安全に管理してください
- 各取引所のAPI利用規約を遵守してください

## ライセンス

MIT