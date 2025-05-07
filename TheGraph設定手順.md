# The Graph API設定手順

DEXアービトラージボットがThe Graph APIを使って正確な価格データを取得するための設定手順です。

## 1. The Graph APIキーの取得

1. The Graphの公式サイト [https://thegraph.com/](https://thegraph.com/) にアクセス
2. アカウントを作成またはログイン
3. ダッシュボードから「API Keys」セクションに移動
4. 「Create API Key」をクリックして新しいAPIキーを生成
5. 作成したAPIキーをコピー

## 2. 環境設定ファイルの作成

1. リポジトリのルートディレクトリに `.env` ファイルを作成
2. `.env.example` をテンプレートとして使用
3. 取得したAPIキーを `GRAPH_API_KEY` に設定
4. 必要に応じて他の設定も行う

```
# .envファイル例
GRAPH_API_KEY=your_api_key_here
```

## 3. サブグラフIDの確認

サブグラフIDはデフォルトで以下の値が設定されています：

- Uniswap V3: `5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV`
- SushiSwap: `CKaCne3uUUEqT7Ei9jjZbQqTLntEno9LnFa4JnsqqBma`
- QuickSwap: `FqsRcH1XqSjqVx9GRTvEJe959aCbKrcyGgDWBrUkG24g`
- Balancer: `H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp`

サブグラフIDが変更された場合は、`.env` ファイルで対応する環境変数を更新してください：

```
# サブグラフIDの設定例
UNISWAP_SUBGRAPH_ID=new_uniswap_subgraph_id
SUSHISWAP_SUBGRAPH_ID=new_sushiswap_subgraph_id
QUICKSWAP_SUBGRAPH_ID=new_quickswap_subgraph_id
BALANCER_SUBGRAPH_ID=new_balancer_subgraph_id
```

## 4. API設定の動作確認

設定が正しく行われているか確認するために、テストスクリプトを実行します：

```bash
python test_graph_api.py
```

すべてのDEXで正常にデータが取得できれば設定は成功です。

特定のDEXのみをテストする場合：

```bash
python test_graph_api.py --dex uniswap
```

特定の通貨ペアをテストする場合：

```bash
python test_graph_api.py --base ETH --quote USDT
```

## 5. トラブルシューティング

### APIキーの問題

エラーメッセージに "Invalid API Key" が含まれる場合：
- APIキーが正しく設定されているか確認
- APIキーがアクティブであることを確認
- APIキーの利用制限を確認

### サブグラフの問題

エラーメッセージに "Subgraph not found" が含まれる場合：
- サブグラフIDが正しいか確認
- サブグラフが存在するか確認
- 最新のサブグラフIDに更新

### クエリの問題

エラーメッセージに "Invalid query" が含まれる場合：
- GraphQLスキーマが変更された可能性があります
- 最新のドキュメントを確認し、クエリを修正

## 6. 参考リンク

- [The Graph ドキュメント](https://thegraph.com/docs/)
- [Uniswap Subgraph](https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3)
- [SushiSwap Subgraph](https://thegraph.com/hosted-service/subgraph/sushi-v3/v3-polygon)
- [QuickSwap Subgraph](https://thegraph.com/hosted-service/subgraph/quickswap/quickswap-v3)
- [Balancer Subgraph](https://thegraph.com/hosted-service/subgraph/balancer-labs/balancer-polygon-v2)