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
            # 各DEXに対してテスト実行
            for dex_id, dex_config in self.config.dexes.items():
                logger.info(f"テスト: {dex_config.name}")
                
                # 各通貨ペアに対してテスト
                for pair in self.config.token_pairs:
                    logger.info(f"  通貨ペア: {pair}")
                    
                    try:
                        if dex_id == "uniswap_v3":
                            result = await self._test_uniswap_prices(session, dex_config, pair)
                        elif dex_id == "quickswap":
                            result = await self._test_quickswap_prices(session, dex_config, pair)
                        elif dex_id == "sushiswap":
                            result = await self._test_sushiswap_prices(session, dex_config, pair)
                        elif dex_id == "curve":
                            result = await self._test_curve_prices(session, dex_config, pair)
                        elif dex_id == "balancer":
                            result = await self._test_balancer_prices(session, dex_config, pair)
                        
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
    
    async def _test_uniswap_prices(self, session, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """Uniswap V3のGraphQLクエリをテスト"""
        # GraphQLクエリを構築
        query = """
        {
          pools(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: liquidity, orderDirection: desc, first: 1) {
            id
            token0Price
            token1Price
            liquidity
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
        """ % (pair.base, pair.quote)
        
        # クエリを実行
        async with session.post(dex_config.api_url, json={"query": query}) as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get("data", {}).get("pools", [])
                
                if pools:
                    pool = pools[0]
                    token0_symbol = pool["token0"]["symbol"]
                    token1_symbol = pool["token1"]["symbol"]
                    
                    # 正しい方向の価格を選択
                    if token0_symbol.upper() == pair.base:
                        price = float(pool["token1Price"])
                    else:
                        price = float(pool["token0Price"])
                    
                    return {
                        "price": price,
                        "liquidity": float(pool["liquidity"]) if "liquidity" in pool else 0,
                        "pool_id": pool["id"],
                        "token0": token0_symbol,
                        "token1": token1_symbol,
                        "timestamp": int(time.time())
                    }
        
        return None
    
    async def _test_quickswap_prices(self, session, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """QuickSwapのGraphQLクエリをテスト"""
        # GraphQLクエリを構築
        query = """
        {
          pools(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: totalValueLockedUSD, orderDirection: desc, first: 1) {
            id
            token0Price
            token1Price
            totalValueLockedUSD
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
        """ % (pair.base, pair.quote)
        
        # クエリを実行
        async with session.post(dex_config.api_url, json={"query": query}) as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get("data", {}).get("pools", [])
                
                if pools:
                    pool = pools[0]
                    token0_symbol = pool["token0"]["symbol"]
                    token1_symbol = pool["token1"]["symbol"]
                    
                    # 正しい方向の価格を選択
                    if token0_symbol.upper() == pair.base:
                        price = float(pool["token1Price"])
                    else:
                        price = float(pool["token0Price"])
                    
                    return {
                        "price": price,
                        "liquidity": float(pool.get("totalValueLockedUSD", 0)),
                        "pool_id": pool["id"],
                        "token0": token0_symbol,
                        "token1": token1_symbol,
                        "timestamp": int(time.time())
                    }
        
        return None
    
    async def _test_sushiswap_prices(self, session, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """SushiSwapのGraphQLクエリをテスト"""
        # GraphQLクエリを構築
        query = """
        {
          pairs(where: {token0_: {symbol_contains_nocase: "%s"}, token1_: {symbol_contains_nocase: "%s"}}, orderBy: reserveUSD, orderDirection: desc, first: 1) {
            id
            token0Price
            token1Price
            reserveUSD
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
        """ % (pair.base, pair.quote)
        
        # クエリを実行
        async with session.post(dex_config.api_url, json={"query": query}) as response:
            if response.status == 200:
                data = await response.json()
                pairs_data = data.get("data", {}).get("pairs", [])
                
                if pairs_data:
                    pair_data = pairs_data[0]
                    token0_symbol = pair_data["token0"]["symbol"]
                    token1_symbol = pair_data["token1"]["symbol"]
                    
                    # 正しい方向の価格を選択
                    if token0_symbol.upper() == pair.base:
                        price = float(pair_data["token1Price"])
                    else:
                        price = float(pair_data["token0Price"])
                    
                    return {
                        "price": price,
                        "liquidity": float(pair_data.get("reserveUSD", 0)),
                        "pool_id": pair_data["id"],
                        "token0": token0_symbol,
                        "token1": token1_symbol,
                        "timestamp": int(time.time())
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
                    
                    if pair.base in tokens and pair.quote in tokens:
                        # インデックスを取得
                        base_idx = tokens.index(pair.base)
                        quote_idx = tokens.index(pair.quote)
                        
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
    
    async def _test_balancer_prices(self, session, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """Balancerの価格取得をテスト"""
        # GraphQLクエリを構築
        query = """
        {
          pools(where: {
            tokensList_contains_nocase: ["%s", "%s"]
          }, orderBy: totalLiquidity, orderDirection: desc, first: 1) {
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
        """ % (pair.base, pair.quote)
        
        # クエリを実行
        async with session.post(dex_config.api_url, json={"query": query}) as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get("data", {}).get("pools", [])
                
                if pools and pools[0]["tokens"]:
                    pool = pools[0]
                    tokens = pool["tokens"]
                    
                    # ベーストークンとクオートトークンを探す
                    base_token = None
                    quote_token = None
                    
                    for token in tokens:
                        if token["symbol"].upper() == pair.base:
                            base_token = token
                        elif token["symbol"].upper() == pair.quote:
                            quote_token = token
                    
                    if base_token and quote_token and \
                       base_token.get("latestPrice") and \
                       quote_token.get("latestPrice"):
                        
                        base_price = float(base_token["latestPrice"]["price"])
                        quote_price = float(quote_token["latestPrice"]["price"])
                        
                        if quote_price > 0:
                            price = base_price / quote_price
                            
                            return {
                                "price": price,
                                "liquidity": float(pool.get("totalLiquidity", 0)),
                                "pool_id": pool["id"],
                                "base_token_price": base_price,
                                "quote_token_price": quote_price,
                                "token_count": len(tokens),
                                "timestamp": int(time.time())
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
    # 設定を読み込み
    from src.config import AppConfig
    config = AppConfig()
    
    # デバッグツールを初期化
    debug_monitor = DebugPriceMonitor(config)
    
    # すべてのDEXクエリをテスト
    await debug_monitor.test_all_dex_queries()

if __name__ == "__main__":
    # テスト実行
    asyncio.run(main())
