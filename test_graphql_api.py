#!/usr/bin/env python3
# test_graphql_api.py - The GraphのAPIを使ったテストスクリプト

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv
from tabulate import tabulate
import time
import argparse
import logging

# 共通GraphQLモジュールをインポート
from src.graphql import (
    GraphQLClient,
    get_uniswap_query,
    get_sushiswap_query,
    get_quickswap_query,
    get_balancer_query,
    parse_uniswap_response,
    parse_sushiswap_response,
    parse_quickswap_response,
    parse_balancer_response,
)

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_graph_api")

# 環境変数の読み込み
load_dotenv()

# The Graph API Key
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")

# サブグラフID
SUBGRAPH_IDS = {
    "uniswap": os.getenv(
        "UNISWAP_SUBGRAPH_ID", "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    ),
    "sushiswap": os.getenv(
        "SUSHISWAP_SUBGRAPH_ID", "CKaCne3uUUEqT7Ei9jjZbQqTLntEno9LnFa4JnsqqBma"
    ),
    "quickswap": os.getenv(
        "QUICKSWAP_SUBGRAPH_ID", "FqsRcH1XqSjqVx9GRTvEJe959aCbKrcyGgDWBrUkG24g"
    ),
    "balancer": os.getenv(
        "BALANCER_SUBGRAPH_ID", "H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp"
    ),
}

# The Graph Gateway URL
GRAPH_BASE_URL = "https://gateway.thegraph.com/api"

# テスト用の通貨ペア
DEFAULT_PAIRS = [
    {"base": "ETH", "quote": "USDT"},
    {"base": "MATIC", "quote": "USDT"},
    {"base": "WBTC", "quote": "ETH"},
]


def get_graph_url(subgraph_id):
    """サブグラフIDからGraphQLエンドポイントURLを生成"""
    if not GRAPH_API_KEY:
        logger.warning(
            "GRAPH_API_KEY環境変数が設定されていません。APIリクエストは失敗します。"
        )
        return f"{GRAPH_BASE_URL}/[API-KEY-REQUIRED]/subgraphs/id/{subgraph_id}"
    return f"{GRAPH_BASE_URL}/{GRAPH_API_KEY}/subgraphs/id/{subgraph_id}"


async def test_uniswap_query(graphql_client, pair):
    """Uniswap V3のGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["uniswap"])

    # 共通モジュールからクエリを取得
    query = get_uniswap_query(pair["base"], pair["quote"], 5)

    # クエリをログ出力 (フルバージョン)
    logger.debug(f"Uniswap V3 Query for {pair['base']}/{pair['quote']}:\n{query}")

    start_time = time.time()

    try:
        # GraphQLクライアントを使用してクエリ実行
        response = await graphql_client.execute_simple(url, query)
        duration = time.time() - start_time

        # エラーチェック
        if "errors" in response:
            return {
                "success": False,
                "status_code": 200,
                "error": response["errors"],
                "duration": duration,
            }

        # レスポンスをパース
        parsed_pools = parse_uniswap_response(response, pair["base"], pair["quote"])

        if not parsed_pools:
            return {
                "success": True,
                "status_code": 200,
                "result": "No pools found for this pair",
                "duration": duration,
            }

        # テーブル表示用にデータを整形
        result = []
        for pool in parsed_pools:
            pool_info = {
                "pool_id": pool["pool_id"][:10] + "...",
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "price": pool["price"],
                "liquidity": pool["liquidity"],
            }
            result.append(pool_info)

        return {
            "success": True,
            "status_code": 200,
            "result": result,
            "duration": duration,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Uniswapクエリ中にエラー: {e}", exc_info=True)
        return {"success": False, "error": str(e), "duration": duration}


async def test_sushiswap_query(graphql_client, pair):
    """SushiSwapのGraphQLクエリをテスト (where句なし版)"""
    url = get_graph_url(SUBGRAPH_IDS["sushiswap"])

    # 共通モジュールからクエリを取得 (where句なし)
    query = get_sushiswap_query(
        pair["base"], pair["quote"], 100
    )  # より多くのペアを取得

    # クエリをログ出力 (フルバージョン)
    logger.debug(
        f"SushiSwap Query for {pair['base']}/{pair['quote']} (client-side filtering):\n{query}"
    )

    start_time = time.time()

    try:
        # GraphQLクライアントを使用してクエリ実行（タイムアウト対策）
        response = await graphql_client.execute_simple(url, query)
        duration = time.time() - start_time

        # エラーチェック
        if "errors" in response:
            return {
                "success": False,
                "status_code": 200,
                "error": response["errors"],
                "duration": duration,
            }

        # レスポンス全体のペア数を記録
        total_pairs = len(response.get("data", {}).get("pairs", []))
        logger.debug(f"SushiSwap: 合計 {total_pairs} ペアを取得しました")

        # クライアントサイドでフィルタリングを行うパーサーを使用
        parsed_pairs = parse_sushiswap_response(response, pair["base"], pair["quote"])

        if not parsed_pairs:
            return {
                "success": True,
                "status_code": 200,
                "result": f"No matching pairs found (searched through {total_pairs} pairs)",
                "duration": duration,
            }

        # テーブル表示用にデータを整形
        result = []
        for pair_data in parsed_pairs:
            pair_info = {
                "pool_id": pair_data["pool_id"][:10] + "...",
                "base_token": pair_data["base_token"],
                "quote_token": pair_data["quote_token"],
                "price": pair_data["price"],
                "liquidity": pair_data["liquidity"],
            }
            result.append(pair_info)

        return {
            "success": True,
            "status_code": 200,
            "result": result,
            "duration": duration,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"SushiSwapクエリ中にエラー: {e}", exc_info=True)
        return {"success": False, "error": str(e), "duration": duration}


async def test_quickswap_query(graphql_client, pair):
    """QuickSwapのGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["quickswap"])

    # 共通モジュールからクエリを取得
    query = get_quickswap_query(pair["base"], pair["quote"], 5)

    # クエリをログ出力 (フルバージョン)
    logger.debug(f"Uniswap V3 Query for {pair['base']}/{pair['quote']}:\n{query}")

    start_time = time.time()

    try:
        # GraphQLクライアントを使用してクエリ実行
        response = await graphql_client.execute_simple(url, query)
        duration = time.time() - start_time

        # エラーチェック
        if "errors" in response:
            return {
                "success": False,
                "status_code": 200,
                "error": response["errors"],
                "duration": duration,
            }

        # レスポンスをパース
        parsed_pools = parse_quickswap_response(response, pair["base"], pair["quote"])

        if not parsed_pools:
            return {
                "success": True,
                "status_code": 200,
                "result": "No pools found for this pair",
                "duration": duration,
            }

        # テーブル表示用にデータを整形
        result = []
        for pool in parsed_pools:
            pool_info = {
                "pool_id": pool["pool_id"][:10] + "...",
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "price": pool["price"],
                "liquidity": pool["liquidity"],
            }
            result.append(pool_info)

        return {
            "success": True,
            "status_code": 200,
            "result": result,
            "duration": duration,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"QuickSwapクエリ中にエラー: {e}", exc_info=True)
        return {"success": False, "error": str(e), "duration": duration}


async def test_balancer_query(graphql_client, pair):
    """BalancerのGraphQLクエリをテスト (where句なし版)"""
    url = get_graph_url(SUBGRAPH_IDS["balancer"])

    # 修正版: Balancerのwhere句なしクエリ
    query = get_balancer_query(
        pair["base"], pair["quote"], 100
    )  # より多くのプールを取得

    # クエリをログ出力 (フルバージョン)
    logger.debug(
        f"Balancer Query for {pair['base']}/{pair['quote']} (client-side filtering):\n{query}"
    )

    start_time = time.time()

    try:
        # GraphQLクライアントを使用してクエリ実行
        response = await graphql_client.execute_simple(url, query)
        duration = time.time() - start_time

        # エラーチェック
        if "errors" in response:
            return {
                "success": False,
                "status_code": 200,
                "error": response["errors"],
                "duration": duration,
            }

        # レスポンス全体のプール数を記録
        total_pools = len(response.get("data", {}).get("pools", []))
        logger.debug(f"Balancer: 合計 {total_pools} プールを取得しました")

        # クライアントサイドでフィルタリングを行うパーサーを使用
        parsed_pools = parse_balancer_response(response, pair["base"], pair["quote"])

        if not parsed_pools:
            return {
                "success": True,
                "status_code": 200,
                "result": f"No matching pools found (searched through {total_pools} pools)",
                "duration": duration,
            }

        # テーブル表示用にデータを整形
        result = []
        for pool in parsed_pools:
            pool_info = {
                "pool_id": pool["pool_id"][:10] + "...",
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "price": pool["price"],
                "liquidity": pool["liquidity"],
            }
            result.append(pool_info)

        return {
            "success": True,
            "status_code": 200,
            "result": result,
            "duration": duration,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Balancerクエリ中にエラー: {e}", exc_info=True)
        return {"success": False, "error": str(e), "duration": duration}


async def print_results(dex_name, pair, result):
    """テスト結果を表示"""
    print(f"\n=== {dex_name} - {pair['base']}/{pair['quote']} ===")
    print(f"応答時間: {result['duration']:.4f}秒")

    if not result["success"]:
        print(f"エラー: {result.get('error', '不明なエラー')}")
        return

    if isinstance(result["result"], str):
        print(result["result"])
        return

    # テーブル形式で結果を表示
    table_data = []
    for item in result["result"]:
        table_data.append(item)

    if table_data:
        print(tabulate(table_data, headers="keys", tablefmt="grid"))
    else:
        print("データが取得できませんでした。")


async def run_tests():
    """テストを実行する"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="The Graph APIテストツール")
    parser.add_argument(
        "--dex",
        choices=["uniswap", "sushiswap", "quickswap", "balancer", "all"],
        default="all",
        help="テストするDEX",
    )
    parser.add_argument("--base", type=str, help="ベーストークン（例: ETH）")
    parser.add_argument("--quote", type=str, help="クオートトークン（例: USDT）")
    parser.add_argument(
        "--pairs", nargs="+", help="テストする通貨ペア（例: ETH/USDT WBTC/ETH）"
    )
    parser.add_argument(
        "--debug", action="store_true", help="デバッグモードを有効にする"
    )

    args = parser.parse_args()

    # デバッグモードが指定された場合のロギングレベル設定
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("dex_arbitrage_bot").setLevel(logging.DEBUG)
        logger.info("デバッグモードが有効です")
    else:
        logging.getLogger().setLevel(logging.INFO)

    # APIキーチェック
    if not GRAPH_API_KEY:
        print("警告: GRAPH_API_KEY環境変数が設定されていません。")
        print("The Graph APIはAPIキーがないとアクセスできません。")
        print(".envファイルにGRAPH_API_KEYを設定してください。")
        return

    # テスト対象のDEXを決定
    test_dexes = []
    if args.dex == "all":
        test_dexes = ["uniswap", "sushiswap", "quickswap", "balancer"]
    else:
        test_dexes = [args.dex]

    # テスト対象の通貨ペアを決定
    test_pairs = []
    if args.base and args.quote:
        test_pairs = [{"base": args.base, "quote": args.quote}]
    elif args.pairs:
        for pair_str in args.pairs:
            if "/" in pair_str:
                base, quote = pair_str.split("/")
                test_pairs.append({"base": base, "quote": quote})
    else:
        test_pairs = DEFAULT_PAIRS

    logger.info(f"テスト対象DEX: {test_dexes}")
    logger.info(f"テスト対象通貨ペア: {test_pairs}")

    # GraphQLクライアントを初期化
    async with aiohttp.ClientSession() as session:
        graphql_client = GraphQLClient(
            session=session, debug=args.debug  # デバッグフラグを追加
        )

        # テスト実行
        for dex in test_dexes:
            for pair in test_pairs:
                try:
                    # DEXに応じたテスト関数を呼び出し
                    if dex == "uniswap":
                        result = await test_uniswap_query(graphql_client, pair)
                        await print_results("Uniswap V3", pair, result)
                    elif dex == "sushiswap":
                        result = await test_sushiswap_query(graphql_client, pair)
                        await print_results("SushiSwap", pair, result)
                    elif dex == "quickswap":
                        result = await test_quickswap_query(graphql_client, pair)
                        await print_results("QuickSwap", pair, result)
                    elif dex == "balancer":
                        result = await test_balancer_query(graphql_client, pair)
                        await print_results("Balancer", pair, result)

                    # API呼び出しの間隔を空ける（レート制限対策）
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(
                        f"{dex} - {pair['base']}/{pair['quote']}のテスト中にエラー: {e}",
                        exc_info=True,
                    )
                    print(f"\n=== {dex} - {pair['base']}/{pair['quote']} ===")
                    print(f"エラー: {e}")


if __name__ == "__main__":
    print("The Graph API テストツール")
    print("------------------------")

    # 環境変数のチェック
    if not GRAPH_API_KEY:
        print("警告: GRAPH_API_KEY環境変数が設定されていません。")
        print(".envファイルに以下の行を追加してください:")
        print("GRAPH_API_KEY=your_api_key_here")
    else:
        print(f"APIキー: {GRAPH_API_KEY[:4]}...{GRAPH_API_KEY[-4:]}")

    print("サブグラフID:")
    for dex, subgraph_id in SUBGRAPH_IDS.items():
        print(f"- {dex}: {subgraph_id[:8]}...{subgraph_id[-8:]}")

    print("\nテストを開始します...")
    asyncio.run(run_tests())
