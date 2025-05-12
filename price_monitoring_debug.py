#!/usr/bin/env python3
# price_monitoring_debug.py - 価格モニタリングモジュールの拡張バージョン

import asyncio
import logging
import time
import os
import json
from typing import Dict, Any, List, Tuple
import aiohttp
from datetime import datetime

from src.config import AppConfig, TokenPair
from src.data_management import DataManager
from debug_graphql_monitor import TracedSession

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
    parse_balancer_response
)

# ロギングの設定
logger = logging.getLogger("dex_arbitrage_bot.price_monitoring_debug")

class DebugPriceMonitor:
    """価格モニタリングのデバッグ機能を持つクラス"""
    
    def __init__(self, config: AppConfig, data_manager: DataManager = None):
        self.config = config
        self.data_manager = data_manager
        
        # デバッグ用設定
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        self.save_responses = os.getenv("SAVE_RESPONSES", "true").lower() == "true"
        
        # デバッグ用ディレクトリを作成
        if self.debug_mode:
            self.debug_dir = "./logs/price_monitoring"
            os.makedirs(self.debug_dir, exist_ok=True)
            
            # デバッグログファイルをセットアップ
            log_formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
            
            file_handler = logging.FileHandler(f"{self.debug_dir}/price_debug.log")
            file_handler.setFormatter(log_formatter)
            file_handler.setLevel(logging.DEBUG)
            
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
            
            logger.debug("デバッグモードで初期化しました")
    
    async def test_all_dex_queries(self):
        """すべてのDEXクエリをテスト実行する"""
        logger.info("すべてのDEXクエリのテストを開始します")
        
        # トレースセッションを作成
        async with TracedSession(monitor_enabled=self.debug_mode, save_responses=self.save_responses) as session:
            # GraphQLクライアントの初期化
            graphql_client = GraphQLClient(session=session, debug=self.debug_mode)
            
            # 各DEXに対してテスト実行
            for dex_id, dex_config in self.config.dexes.items():
                logger.info(f"テスト: {dex_config.name}")
                
                # 各通貨ペアに対してテスト
                for pair in self.config.token_pairs:
                    logger.info(f"  通貨ペア: {pair}")
                    
                    try:
                        if dex_id == "uniswap_v3":
                            result = await self._test_uniswap_prices(graphql_client, dex_config, pair)
                        elif dex_id == "quickswap":
                            result = await self._test_quickswap_prices(graphql_client, dex_config, pair)
                        elif dex_id == "sushiswap":
                            result = await self._test_sushiswap_prices(graphql_client, dex_config, pair)
                        elif dex_id == "curve":
                            result = await self._test_curve_prices(session, dex_config, pair)
                        elif dex_id == "balancer":
                            result = await self._test_balancer_prices(graphql_client, dex_config, pair)
                        
                        # 結果をログに出力
                        if result:
                            for key, value in result.items():
                                if key == "price":
                                    logger.info(f"    価格: {value}")
                                elif key == "liquidity":
                                    logger.info(f"    流動性: {value}")
                                elif key == "timestamp":
                                    continue
                                else:
                                    logger.info(f"    {key}: {value}")
                        else:
                            logger.warning(f"    結果: データが取得できませんでした")
                        
                        # 結果をJSONファイルに保存
                        if self.debug_mode and result:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{self.debug_dir}/{timestamp}_{dex_id}_{pair}.json"
                            
                            with open(filename, 'w') as f:
                                json.dump({
                                    "dex": dex_id,
                                    "pair": str(pair),
                                    "result": result,
                                    "timestamp": time.time()
                                }, f, indent=2)
                    
                    except Exception as e:
                        logger.error(f"    エラー: {e}")
        
        logger.info("すべてのDEXクエリのテストが完了しました")
    
    async def _test_uniswap_prices(self, graphql_client, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """Uniswap V3のGraphQLクエリをテスト"""
        # GraphQLクエリを構築
        query = get_uniswap_query(pair.base, pair.quote, 5)
        
        logger.debug(f"Uniswap V3クエリ: {query}")
        
        # クエリを実行
        response = await graphql_client.execute_simple(dex_config.api_url, query)
        
        # レスポンスをパース
        parsed_pools = parse_uniswap_response(response, pair.base, pair.quote)
        
        if parsed_pools:
            # 最も流動性の高いプールを使用
            pool = parsed_pools[0]
            return {
                "price": pool["price"],
                "liquidity": pool["liquidity"],
                "pool_id": pool["pool_id"],
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "timestamp": int(time.time())
            }
        
        return None
    
    async def _test_quickswap_prices(self, graphql_client, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """QuickSwapのGraphQLクエリをテスト"""
        # GraphQLクエリを構築
        query = get_quickswap_query(pair.base, pair.quote, 5)
        
        logger.debug(f"QuickSwapクエリ: {query}")
        
        # クエリを実行
        response = await graphql_client.execute_simple(dex_config.api_url, query)
        
        # レスポンスをパース
        parsed_pools = parse_quickswap_response(response, pair.base, pair.quote)
        
        if parsed_pools:
            # 最も流動性の高いプールを使用
            pool = parsed_pools[0]
            return {
                "price": pool["price"],
                "liquidity": pool["liquidity"],
                "pool_id": pool["pool_id"],
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "timestamp": int(time.time())
            }
        
        return None
    
    async def _test_sushiswap_prices(self, graphql_client, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """SushiSwapのGraphQLクエリをテスト（where句なし、クライアントサイドフィルタリング）"""
        # GraphQLクエリを構築（where句なし）
        query = get_sushiswap_query(pair.base, pair.quote, 100)
        
        logger.debug(f"SushiSwapクエリ（クライアントサイドフィルタリング）: {query}")
        
        # クエリを実行
        response = await graphql_client.execute_simple(dex_config.api_url, query)
        
        # 全ペア数をログ出力
        total_pairs = len(response.get("data", {}).get("pairs", []))
        logger.debug(f"SushiSwap: 合計 {total_pairs} ペアを取得しました")
        
        # レスポンスをパース（クライアントサイドでフィルタリング）
        parsed_pairs = parse_sushiswap_response(response, pair.base, pair.quote)
        
        if parsed_pairs:
            # 最も適切なペアを使用
            pair_data = parsed_pairs[0]
            return {
                "price": pair_data["price"],
                "liquidity": pair_data["liquidity"],
                "pool_id": pair_data["pool_id"],
                "base_token": pair_data["base_token"],
                "quote_token": pair_data["quote_token"],
                "timestamp": int(time.time()),
                "filtered_from": total_pairs
            }
        
        return None
    
    async def _test_curve_prices(self, session, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """Curveの価格取得をテスト"""
        # Curve APIから全プールデータを取得
        async with session.get(dex_config.api_url) as response:
            if response.status == 200:
                data = await response.json()
                pools_data = data.get("data", {}).get("poolData", [])
                
                pair_id = pair.for_dex("curve")
                
                # プールを検索
                for pool in pools_data:
                    tokens = [t.get("symbol", "").upper() for t in pool.get("coins", [])]
                    
                    if pair.base.upper() in tokens and pair.quote.upper() in tokens:
                        # インデックスを取得
                        base_idx = tokens.index(pair.base.upper())
                        quote_idx = tokens.index(pair.quote.upper())
                        
                        # 価格データが利用可能な場合
                        if "usdPrices" in pool:
                            base_price_usd = float(pool["usdPrices"][base_idx])
                            quote_price_usd = float(pool["usdPrices"][quote_idx])
                            
                            if quote_price_usd > 0:
                                price = base_price_usd / quote_price_usd
                                
                                return {
                                    "price": price,
                                    "liquidity": float(pool.get("usdTotal", 0)),
                                    "pool_id": pool.get("id", "unknown"),
                                    "pool_name": pool.get("name", "unknown"),
                                    "base_usd": base_price_usd,
                                    "quote_usd": quote_price_usd,
                                    "tokens": tokens,
                                    "timestamp": int(time.time())
                                }
        
        return None
    
    async def _test_balancer_prices(self, graphql_client, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """Balancerの価格取得をテスト（where句なし、クライアントサイドフィルタリング）"""
        # GraphQLクエリを構築（where句なし）
        query = get_balancer_query(pair.base, pair.quote, 100)
        
        logger.debug(f"Balancerクエリ（クライアントサイドフィルタリング）: {query}")
        
        # クエリを実行
        response = await graphql_client.execute_simple(dex_config.api_url, query)
        
        # 全プール数をログ出力
        total_pools = len(response.get("data", {}).get("pools", []))
        logger.debug(f"Balancer: 合計 {total_pools} プールを取得しました")
        
        # レスポンスをパース（クライアントサイドでフィルタリング）
        parsed_pools = parse_balancer_response(response, pair.base, pair.quote)
        
        if parsed_pools:
            # 最も流動性の高いプールを使用
            pool = parsed_pools[0]
            return {
                "price": pool["price"],
                "liquidity": pool["liquidity"],
                "pool_id": pool["pool_id"],
                "base_token": pool["base_token"],
                "quote_token": pool["quote_token"],
                "timestamp": int(time.time()),
                "filtered_from": total_pools
            }
        
        return None
    
    def save_current_prices_to_file(self, prices: Dict[str, Dict[str, Dict[str, Any]]]):
        """現在の価格データをファイルに保存（デバッグ用）"""
        if not self.debug_mode:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.debug_dir}/{timestamp}_all_prices.json"
            
            with open(filename, 'w') as f:
                json.dump(prices, f, indent=2)
            
            logger.debug(f"現在の価格データをファイルに保存しました: {filename}")
        
        except Exception as e:
            logger.error(f"価格データの保存中にエラーが発生しました: {e}")

async def main():
    """テスト実行用のメイン関数"""
    # コマンドライン引数のパース
    import argparse
    parser = argparse.ArgumentParser(description="DEX価格モニタリングのデバッグツール")
    parser.add_argument("--debug", action="store_true", help="詳細なデバッグ情報を出力します")
    parser.add_argument("--save", action="store_true", help="GraphQLレスポンスを保存します")
    parser.add_argument("--dex", choices=["all", "uniswap", "quickswap", "sushiswap", "curve", "balancer"], 
                        default="all", help="テスト対象のDEX（デフォルト: すべて）")
    parser.add_argument("--pair", help="テスト対象の通貨ペア（例: ETH/USDT）")
    args = parser.parse_args()
    
    # デバッグモード設定
    if args.debug:
        os.environ["DEBUG"] = "true"
        logging.getLogger().setLevel(logging.DEBUG)
    
    # レスポンス保存設定
    if args.save:
        os.environ["SAVE_RESPONSES"] = "true"
    
    # 設定を読み込み
    from src.config import AppConfig
    config = AppConfig()
    
    # 通貨ペアフィルタ設定
    if args.pair:
        base, quote = args.pair.split("/")
        filtered_pairs = []
        for pair in config.token_pairs:
            if pair.base.upper() == base.upper() and pair.quote.upper() == quote.upper():
                filtered_pairs.append(pair)
        if filtered_pairs:
            config.token_pairs = filtered_pairs
        else:
            logger.warning(f"指定された通貨ペア {args.pair} は設定に存在しません。すべての通貨ペアをテストします。")
    
    # DEXフィルタ設定
    if args.dex != "all":
        filtered_dexes = {}
        for dex_id, dex_config in config.dexes.items():
            if dex_id == args.dex:
                filtered_dexes[dex_id] = dex_config
        if filtered_dexes:
            config.dexes = filtered_dexes
        else:
            logger.warning(f"指定されたDEX {args.dex} は設定に存在しません。すべてのDEXをテストします。")
    
    # デバッグツールを初期化
    debug_monitor = DebugPriceMonitor(config)
    
    # すべてのDEXクエリをテスト
    await debug_monitor.test_all_dex_queries()

if __name__ == "__main__":
    # ロギングの基本設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # テスト実行
    asyncio.run(main())