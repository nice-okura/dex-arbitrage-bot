#!/usr/bin/env python3
# test_graph_api.py - The GraphのAPIを使ったテストスクリプト

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv
from tabulate import tabulate
import time
import argparse
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_graph_api")

# 環境変数の読み込み
load_dotenv()

# The Graph API Key
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")

# サブグラフID
SUBGRAPH_IDS = {
    "uniswap": os.getenv("UNISWAP_SUBGRAPH_ID", "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"),
    "sushiswap": os.getenv("SUSHISWAP_SUBGRAPH_ID", "CKaCne3uUUEqT7Ei9jjZbQqTLntEno9LnFa4JnsqqBma"),
    "quickswap": os.getenv("QUICKSWAP_SUBGRAPH_ID", "FqsRcH1XqSjqVx9GRTvEJe959aCbKrcyGgDWBrUkG24g"),
    "balancer": os.getenv("BALANCER_SUBGRAPH_ID", "H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp"),
}

# The Graph Gateway URL
GRAPH_BASE_URL = "https://gateway.thegraph.com/api"

# テスト用の通貨ペア
DEFAULT_PAIRS = [
    {"base": "ETH", "quote": "USDT"},
    {"base": "MATIC", "quote": "USDT"},
    {"base": "WBTC", "quote": "ETH"}
]

def get_graph_url(subgraph_id):
    """サブグラフIDからGraphQLエンドポイントURLを生成"""
    if not GRAPH_API_KEY:
        logger.warning("GRAPH_API_KEY環境変数が設定されていません。APIリクエストは失敗します。")
        return f"{GRAPH_BASE_URL}/[API-KEY-REQUIRED]/subgraphs/id/{subgraph_id}"
    return f"{GRAPH_BASE_URL}/{GRAPH_API_KEY}/subgraphs/id/{subgraph_id}"

async def test_uniswap_query(session, pair):
    """Uniswap V3のGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["uniswap"])
    
    # GraphQLクエリを構築
    query = """
    {
      pools(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: liquidity, orderDirection: desc, first: 5) {
        id
        token0Price
        token1Price
        liquidity
        volumeUSD
        token0 {
          symbol
          id
          decimals
        }
        token1 {
          symbol
          id
          decimals
        }
        feeTier
      }
    }
    """ % (pair["base"], pair["quote"])
    
    start_time = time.time()
    
    try:
        async with session.post(url, json={"query": query}) as response:
            duration = time.time() - start_time
            
            if response.status != 200:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": await response.text(),
                    "duration": duration
                }
            
            data = await response.json()
            
            # エラーチェック
            if "errors" in data:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": data["errors"],
                    "duration": duration
                }
            
            pools = data.get("data", {}).get("pools", [])
            
            if not pools:
                return {
                    "success": True,
                    "status_code": response.status,
                    "result": "No pools found for this pair",
                    "duration": duration
                }
            
            # 結果を整形
            result = []
            for pool in pools:
                token0_symbol = pool["token0"]["symbol"]
                token1_symbol = pool["token1"]["symbol"]
                
                # 正しい方向の価格を選択
                if token0_symbol.upper() == pair["base"].upper():
                    price = float(pool["token1Price"])
                    base_token = token0_symbol
                    quote_token = token1_symbol
                else:
                    price = float(pool["token0Price"])
                    base_token = token1_symbol
                    quote_token = token0_symbol
                
                pool_info = {
                    "pool_id": pool["id"][:10] + "...",
                    "base_token": base_token,
                    "quote_token": quote_token,
                    "price": price,
                    "liquidity": float(pool["liquidity"]),
                    "fee_tier": pool["feeTier"]
                }
                result.append(pool_info)
            
            return {
                "success": True,
                "status_code": response.status,
                "result": result,
                "duration": duration
            }
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Uniswapクエリ中にエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "duration": duration
        }

async def test_sushiswap_query(session, pair):
    """SushiSwapのGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["sushiswap"])
    
    # GraphQLクエリを構築
    query = """
    {
      pairs(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: reserveUSD, orderDirection: desc, first: 5) {
        id
        token0Price
        token1Price
        reserveUSD
        volumeUSD
        token0 {
          symbol
          id
        }
        token1 {
          symbol
          id
        }
      }
    }
    """ % (pair["base"], pair["quote"])
    
    start_time = time.time()
    
    try:
        async with session.post(url, json={"query": query}) as response:
            duration = time.time() - start_time
            
            if response.status != 200:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": await response.text(),
                    "duration": duration
                }
            
            data = await response.json()
            
            # エラーチェック
            if "errors" in data:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": data["errors"],
                    "duration": duration
                }
            
            pairs = data.get("data", {}).get("pairs", [])
            
            if not pairs:
                return {
                    "success": True,
                    "status_code": response.status,
                    "result": "No pairs found for this pair",
                    "duration": duration
                }
            
            # 結果を整形
            result = []
            for pair_data in pairs:
                token0_symbol = pair_data["token0"]["symbol"]
                token1_symbol = pair_data["token1"]["symbol"]
                
                # 正しい方向の価格を選択
                if token0_symbol.upper() == pair["base"].upper():
                    price = float(pair_data["token1Price"])
                    base_token = token0_symbol
                    quote_token = token1_symbol
                else:
                    price = float(pair_data["token0Price"])
                    base_token = token1_symbol
                    quote_token = token0_symbol
                
                pair_info = {
                    "pool_id": pair_data["id"][:10] + "...",
                    "base_token": base_token,
                    "quote_token": quote_token,
                    "price": price,
                    "liquidity": float(pair_data.get("reserveUSD", 0)),
                    "volume_usd": float(pair_data.get("volumeUSD", 0))
                }
                result.append(pair_info)
            
            return {
                "success": True,
                "status_code": response.status,
                "result": result,
                "duration": duration
            }
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"SushiSwapクエリ中にエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "duration": duration
        }

async def test_quickswap_query(session, pair):
    """QuickSwapのGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["quickswap"])
    
    # GraphQLクエリを構築
    query = """
    {
      pools(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: totalValueLockedUSD, orderDirection: desc, first: 5) {
        id
        token0Price
        token1Price
        totalValueLockedUSD
        volumeUSD
        token0 {
          symbol
          id
        }
        token1 {
          symbol
          id
        }
        feeTier
      }
    }
    """ % (pair["base"], pair["quote"])
    
    start_time = time.time()
    
    try:
        async with session.post(url, json={"query": query}) as response:
            duration = time.time() - start_time
            
            if response.status != 200:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": await response.text(),
                    "duration": duration
                }
            
            data = await response.json()
            
            # エラーチェック
            if "errors" in data:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": data["errors"],
                    "duration": duration
                }
            
            pools = data.get("data", {}).get("pools", [])
            
            if not pools:
                return {
                    "success": True,
                    "status_code": response.status,
                    "result": "No pools found for this pair",
                    "duration": duration
                }
            
            # 結果を整形
            result = []
            for pool in pools:
                token0_symbol = pool["token0"]["symbol"]
                token1_symbol = pool["token1"]["symbol"]
                
                # 正しい方向の価格を選択
                if token0_symbol.upper() == pair["base"].upper():
                    price = float(pool["token1Price"])
                    base_token = token0_symbol
                    quote_token = token1_symbol
                else:
                    price = float(pool["token0Price"])
                    base_token = token1_symbol
                    quote_token = token0_symbol
                
                pool_info = {
                    "pool_id": pool["id"][:10] + "...",
                    "base_token": base_token,
                    "quote_token": quote_token,
                    "price": price,
                    "liquidity": float(pool.get("totalValueLockedUSD", 0)),
                    "fee_tier": pool.get("feeTier", "N/A")
                }
                result.append(pool_info)
            
            return {
                "success": True,
                "status_code": response.status,
                "result": result,
                "duration": duration
            }
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"QuickSwapクエリ中にエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "duration": duration
        }

async def test_balancer_query(session, pair):
    """BalancerのGraphQLクエリをテスト"""
    url = get_graph_url(SUBGRAPH_IDS["balancer"])
    
    # GraphQLクエリを構築
    query = """
    {
      pools(where: {
        tokensList_contains_nocase: ["%s", "%s"]
      }, orderBy: totalLiquidity, orderDirection: desc, first: 5) {
        id
        totalLiquidity
        tokens {
          symbol
          address
          latestPrice {
            price
          }
        }
      }
    }
    """ % (pair["base"].lower(), pair["quote"].lower())
    
    start_time = time.time()
    
    try:
        async with session.post(url, json={"query": query}) as response:
            duration = time.time() - start_time
            
            if response.status != 200:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": await response.text(),
                    "duration": duration
                }
            
            data = await response.json()
            
            # エラーチェック
            if "errors" in data:
                return {
                    "success": False,
                    "status_code": response.status,
                    "error": data["errors"],
                    "duration": duration
                }
            
            pools = data.get("data", {}).get("pools", [])
            
            if not pools:
                return {
                    "success": True,
                    "status_code": response.status,
                    "result": "No pools found for this pair",
                    "duration": duration
                }
            
            # 結果を整形
            result = []
            for pool in pools:
                tokens = pool["tokens"]
                
                # ベーストークンとクオートトークンを探す
                base_token = None
                quote_token = None
                
                for token in tokens:
                    if token["symbol"].upper() == pair["base"].upper():
                        base_token = token
                    elif token["symbol"].upper() == pair["quote"].upper():
                        quote_token = token
                
                if base_token and quote_token and \
                   base_token.get("latestPrice") and \
                   quote_token.get("latestPrice"):
                    
                    base_price = float(base_token["latestPrice"]["price"])
                    quote_price = float(quote_token["latestPrice"]["price"])
                    
                    if quote_price > 0:
                        price = base_price / quote_price
                        
                        pool_info = {
                            "pool_id": pool["id"][:10] + "...",
                            "base_token": base_token["symbol"],
                            "quote_token": quote_token["symbol"],
                            "price": price,
                            "liquidity": float(pool.get("totalLiquidity", 0))
                        }
                        result.append(pool_info)
            
            if not result:
                return {
                    "success": True,
                    "status_code": response.status,
                    "result": "Found pools, but couldn't calculate prices",
                    "duration": duration
                }
            
            return {
                "success": True,
                "status_code": response.status,
                "result": result,
                "duration": duration
            }
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Balancerクエリ中にエラー: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "duration": duration
        }

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
    parser.add_argument("--dex", choices=["uniswap", "sushiswap", "quickswap", "balancer", "all"], default="all", help="テストするDEX")
    parser.add_argument("--base", type=str, help="ベーストークン（例: ETH）")
    parser.add_argument("--quote", type=str, help="クオートトークン（例: USDT）")
    parser.add_argument("--pairs", nargs="+", help="テストする通貨ペア（例: ETH/USDT WBTC/ETH）")
    args = parser.parse_args()
    
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
    
    # テスト実行
    async with aiohttp.ClientSession() as session:
        for dex in test_dexes:
            for pair in test_pairs:
                try:
                    # DEXに応じたテスト関数を呼び出し
                    if dex == "uniswap":
                        result = await test_uniswap_query(session, pair)
                        await print_results("Uniswap V3", pair, result)
                    elif dex == "sushiswap":
                        result = await test_sushiswap_query(session, pair)
                        await print_results("SushiSwap", pair, result)
                    elif dex == "quickswap":
                        result = await test_quickswap_query(session, pair)
                        await print_results("QuickSwap", pair, result)
                    elif dex == "balancer":
                        result = await test_balancer_query(session, pair)
                        await print_results("Balancer", pair, result)
                    
                    # API呼び出しの間隔を空ける（レート制限対策）
                    await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"{dex} - {pair['base']}/{pair['quote']}のテスト中にエラー: {e}", exc_info=True)
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