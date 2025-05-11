# src/price_monitoring.py
import asyncio
import logging
import time
import os
from typing import Dict, Any, List, Tuple
import aiohttp

from src.config import AppConfig, TokenPair
from src.data_management import DataManager
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

logger = logging.getLogger("dex_arbitrage_bot.price_monitoring")

class PriceMonitor:
    def __init__(self, config: AppConfig, data_manager: DataManager):
        self.config = config
        self.data_manager = data_manager
        
        # 価格データのキャッシュ
        self.price_cache = {}
        self.session = None
        self.graphql_client = None
    
    async def start_monitoring(self):
        """価格モニタリングを開始する"""
        logger.info("価格モニタリングを開始しました")
        
        # HTTPセッションの作成
        self.session = aiohttp.ClientSession()
        self.graphql_client = GraphQLClient(self.session)
        
        try:
            while True:
                try:
                    # DEXからの価格データ取得
                    dex_prices = await self._fetch_dex_prices()
                    
                    # CEXからの価格データ取得
                    cex_prices = await self._fetch_cex_prices()
                    
                    # 価格データの結合
                    all_prices = {**dex_prices, **cex_prices}
                    
                    # データの保存
                    timestamp = int(time.time())
                    for exchange, prices in all_prices.items():
                        for pair_str, price_data in prices.items():
                            await self.data_manager.save_price(exchange, pair_str, price_data, timestamp)
                    
                    # ログ出力（開発時のみ詳細ログを出力）
                    if os.getenv("DEBUG", "false").lower() == "true":
                        import json
                        logger.debug(f"価格データを更新しました: {json.dumps(all_prices, indent=2)}")
                    else:
                        # 実運用時は簡易ログ
                        logger.info(f"価格データを更新しました: {len(all_prices)}取引所、{sum([len(p) for p in all_prices.values()])}ペア")
                    
                    # 設定された間隔で待機
                    await asyncio.sleep(self.config.price_update_interval)
                    
                except Exception as e:
                    logger.error(f"価格モニタリング中にエラーが発生しました: {e}", exc_info=True)
                    await asyncio.sleep(5)  # エラー発生時は短い間隔で再試行
        finally:
            # セッションのクローズ
            if self.graphql_client:
                await self.graphql_client.close()
            if self.session:
                await self.session.close()
    
    async def _fetch_dex_prices(self) -> Dict[str, Dict[str, Any]]:
        """DEXからの価格データを取得する"""
        results = {}
        
        # 各DEXに対して並行して処理
        tasks = []
        for dex_id, dex_config in self.config.dexes.items():
            tasks.append(self._fetch_dex_price(dex_id, dex_config))
        
        # すべてのタスクが完了するまで待機
        dex_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を集約
        for i, (dex_id, _) in enumerate(self.config.dexes.items()):
            if isinstance(dex_results[i], Exception):
                logger.error(f"{dex_id}からの価格取得中にエラーが発生しました: {dex_results[i]}")
                continue
            
            results[dex_id] = dex_results[i]
        
        return results
    
    async def _fetch_dex_price(self, dex_id: str, dex_config) -> Dict[str, Any]:
        """特定のDEXから価格データを取得する"""
        prices = {}
        
        try:
            if dex_id == "uniswap_v3":
                prices = await self._fetch_uniswap_prices(dex_config)
            elif dex_id == "quickswap":
                prices = await self._fetch_quickswap_prices(dex_config)
            elif dex_id == "sushiswap":
                prices = await self._fetch_sushiswap_prices(dex_config)
            elif dex_id == "curve":
                prices = await self._fetch_curve_prices(dex_config)
            elif dex_id == "balancer":
                prices = await self._fetch_balancer_prices(dex_config)
            
            return prices
        except Exception as e:
            logger.error(f"{dex_id}からの価格取得中にエラーが発生しました: {e}", exc_info=True)
            return {}
    
    async def _fetch_uniswap_prices(self, dex_config) -> Dict[str, Any]:
        """Uniswap V3から価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 共通モジュールからクエリを取得
                query = get_uniswap_query(pair.base, pair.quote)
                
                # GraphQLクライアントを使用してクエリ実行
                response = await self.graphql_client.execute_simple(dex_config.api_url, query)
                
                # レスポンスをパース
                parsed_pools = parse_uniswap_response(response, pair.base, pair.quote)
                
                if parsed_pools:
                    # 最も流動性の高いプールを使用
                    pool = parsed_pools[0]
                    prices[str(pair)] = {
                        "price": pool["price"],
                        "liquidity": pool["liquidity"],
                        "timestamp": pool["timestamp"]
                    }
            except Exception as e:
                logger.error(f"Uniswap V3からの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_quickswap_prices(self, dex_config) -> Dict[str, Any]:
        """QuickSwapから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 共通モジュールからクエリを取得
                query = get_quickswap_query(pair.base, pair.quote)
                
                # GraphQLクライアントを使用してクエリ実行
                response = await self.graphql_client.execute_simple(dex_config.api_url, query)
                
                # レスポンスをパース
                parsed_pools = parse_quickswap_response(response, pair.base, pair.quote)
                
                if parsed_pools:
                    # 最も流動性の高いプールを使用
                    pool = parsed_pools[0]
                    prices[str(pair)] = {
                        "price": pool["price"],
                        "liquidity": pool["liquidity"],
                        "timestamp": pool["timestamp"]
                    }
            except Exception as e:
                logger.error(f"QuickSwapからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_sushiswap_prices(self, dex_config) -> Dict[str, Any]:
        """SushiSwapから価格データを取得する (クライアントサイドフィルタリング版)"""
        prices = {}
        
        try:
            # すべてのペアを一度に取得（1回のAPI呼び出しで済ますため）
            query = get_sushiswap_query("", "", 500)  # パラメータは使用しないが、関数シグネチャに合わせて空文字を渡す
            
            # デバッグ: クエリをログ出力
            logger.debug(f"SushiSwap query (client-side filtering): {query.strip()}")
            
            # GraphQLクライアントを使用してクエリ実行
            response = await self.graphql_client.execute_simple(dex_config.api_url, query)
            
            # APIから取得したペアの総数をログ出力
            total_pairs = len(response.get("data", {}).get("pairs", []))
            logger.debug(f"SushiSwap: 合計 {total_pairs} ペアを取得しました")
            
            # 各通貨ペアについて、取得したデータから該当するものをフィルタリング
            for pair in self.config.token_pairs:
                try:
                    # 特定のペアに絞ったパース処理を行う
                    parsed_pairs = parse_sushiswap_response(response, pair.base, pair.quote)
                    
                    if parsed_pairs:
                        # 最も適切なペアを使用（複数ある場合は先頭を使用）
                        pair_data = parsed_pairs[0]
                        prices[str(pair)] = {
                            "price": pair_data["price"],
                            "liquidity": pair_data["liquidity"],
                            "timestamp": pair_data["timestamp"]
                        }
                        logger.debug(f"SushiSwap: {pair} の価格を見つけました: {pair_data['price']}")
                    else:
                        logger.debug(f"SushiSwap: {pair} に一致するペアが見つかりませんでした")
                except Exception as e:
                    logger.error(f"SushiSwap: {pair} の処理中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"SushiSwapからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices

    async def _fetch_curve_prices(self, dex_config) -> Dict[str, Any]:
        """Curveから価格データを取得する"""
        prices = {}
        
        try:
            # Curve APIから全プールデータを取得
            async with self.session.get(dex_config.api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    pools_data = data.get("data", {}).get("poolData", [])
                    
                    for pair in self.config.token_pairs:
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
                                        
                                        prices[str(pair)] = {
                                            "price": price,
                                            "liquidity": float(pool.get("usdTotal", 0)),
                                            "timestamp": int(time.time())
                                        }
                                        break
        except Exception as e:
            logger.error(f"Curveからの価格取得中にエラーが発生しました: {e}")
        
        return prices
    
    async def _fetch_balancer_prices(self, dex_config) -> Dict[str, Any]:
        """Balancerから価格データを取得する (クライアントサイドフィルタリング版)"""
        prices = {}
        
        try:
            # すべてのプールを一度に取得（1回のAPI呼び出しで済ますため）
            query = get_balancer_query("", "", 200)  # パラメータは使用しないが、関数シグネチャに合わせて空文字を渡す
            
            # デバッグ: クエリをログ出力
            logger.debug(f"Balancer query (client-side filtering): {query.strip()}")
            
            # GraphQLクライアントを使用してクエリ実行
            response = await self.graphql_client.execute_simple(dex_config.api_url, query)
            logger.debug(f"Balancer response: {response}")
            
            # APIから取得したプールの総数をログ出力
            total_pools = len(response.get("data", {}).get("pools", []))
            logger.debug(f"Balancer: 合計 {total_pools} プールを取得しました")
            
            # 各通貨ペアについて、取得したデータから該当するものをフィルタリング
            for pair in self.config.token_pairs:
                try:
                    # 特定のペアに絞ったパース処理を行う
                    parsed_pools = parse_balancer_response(response, pair.base, pair.quote)
                    
                    if parsed_pools:
                        # 最も流動性の高いプールを使用（複数ある場合は先頭を使用）
                        pool = parsed_pools[0]
                        prices[str(pair)] = {
                            "price": pool["price"],
                            "liquidity": pool["liquidity"],
                            "timestamp": pool["timestamp"]
                        }
                        logger.debug(f"Balancer: {pair} の価格を見つけました: {pool['price']}")
                    else:
                        logger.debug(f"Balancer: {pair} に一致するプールが見つかりませんでした")
                except Exception as e:
                    logger.error(f"Balancer: {pair} の処理中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"Balancerからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices

        """Balancerから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 共通モジュールからクエリを取得
                query = get_balancer_query(pair.base, pair.quote)
                
                # GraphQLクライアントを使用してクエリ実行
                response = await self.graphql_client.execute_simple(dex_config.api_url, query)
                logger.debug(f"Balancer response: {response}")
                
                # レスポンスをパース
                parsed_pools = parse_balancer_response(response, pair.base, pair.quote)
                
                if parsed_pools:
                    # 最も流動性の高いプールを使用
                    pool = parsed_pools[0]
                    prices[str(pair)] = {
                        "price": pool["price"],
                        "liquidity": pool["liquidity"],
                        "timestamp": pool["timestamp"]
                    }
            except Exception as e:
                logger.error(f"Balancerからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_cex_prices(self) -> Dict[str, Dict[str, Any]]:
        """CEXからの価格データを取得する"""
        results = {}
        
        # 各CEXに対して並行して処理
        tasks = []
        for cex_id, cex_config in self.config.cexes.items():
            tasks.append(self._fetch_cex_price(cex_id, cex_config))
        
        # すべてのタスクが完了するまで待機
        cex_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を集約
        for i, (cex_id, _) in enumerate(self.config.cexes.items()):
            if isinstance(cex_results[i], Exception):
                logger.error(f"{cex_id}からの価格取得中にエラーが発生しました: {cex_results[i]}")
                continue
            
            results[cex_id] = cex_results[i]
        
        return results
    
    async def _fetch_cex_price(self, cex_id: str, cex_config) -> Dict[str, Any]:
        """特定のCEXから価格データを取得する"""
        prices = {}
        
        try:
            if cex_id == "bitbank":
                prices = await self._fetch_bitbank_prices(cex_config)
            elif cex_id == "bitflyer":
                prices = await self._fetch_bitflyer_prices(cex_config)
            elif cex_id == "coincheck":
                prices = await self._fetch_coincheck_prices(cex_config)
            elif cex_id == "zaif":
                prices = await self._fetch_zaif_prices(cex_config)
            elif cex_id == "bittrade":
                prices = await self._fetch_bittrade_prices(cex_config)
            
            return prices
        except Exception as e:
            logger.error(f"{cex_id}からの価格取得中にエラーが発生しました: {e}", exc_info=True)
            return {}
    
    async def _fetch_bitbank_prices(self, cex_config) -> Dict[str, Any]:
        """Bitbankから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 通貨ペアをBitbank形式に変換
                symbol = pair.for_cex("bitbank")
                url = f"{cex_config.api_url}/{symbol}/ticker"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("success") == 1:
                            ticker = data.get("data", {})
                            
                            if "last" in ticker:
                                price = float(ticker["last"])
                                
                                prices[str(pair)] = {
                                    "price": price,
                                    "volume": float(ticker.get("vol", 0)),
                                    "timestamp": int(time.time())
                                }
            except Exception as e:
                logger.error(f"Bitbankからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_bitflyer_prices(self, cex_config) -> Dict[str, Any]:
        """BitFlyerから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 通貨ペアをBitFlyer形式に変換
                symbol = pair.for_cex("bitflyer")
                url = f"{cex_config.api_url}/ticker"
                params = {"product_code": symbol}
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        ticker = await response.json()
                        
                        if "ltp" in ticker:
                            price = float(ticker["ltp"])
                            
                            prices[str(pair)] = {
                                "price": price,
                                "volume": float(ticker.get("volume", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"BitFlyerからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_coincheck_prices(self, cex_config) -> Dict[str, Any]:
        """Coincheckから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 通貨ペアをCoincheck形式に変換
                symbol = pair.for_cex("coincheck")
                url = f"{cex_config.api_url}/ticker"
                params = {"pair": symbol}
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        ticker = await response.json()
                        
                        if "last" in ticker:
                            price = float(ticker["last"])
                            
                            prices[str(pair)] = {
                                "price": price,
                                "volume": float(ticker.get("volume", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"Coincheckからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_zaif_prices(self, cex_config) -> Dict[str, Any]:
        """Zaifから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 通貨ペアをZaif形式に変換
                symbol = pair.for_cex("zaif")
                url = f"{cex_config.api_url}/ticker/{symbol}"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        ticker = await response.json()
                        
                        if "last" in ticker:
                            price = float(ticker["last"])
                            
                            prices[str(pair)] = {
                                "price": price,
                                "volume": float(ticker.get("volume", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"Zaifからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_bittrade_prices(self, cex_config) -> Dict[str, Any]:
        """BitTradeから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
                # 通貨ペアをBitTrade形式に変換
                symbol = pair.for_cex("bittrade")
                url = f"{cex_config.api_url}/public/ticker/{symbol}"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        ticker = await response.json()
                        
                        if ticker.get("status") == "success" and "last" in ticker.get("data", {}):
                            price = float(ticker["data"]["last"])
                            
                            prices[str(pair)] = {
                                "price": price,
                                "volume": float(ticker["data"].get("volume", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"BitTradeからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices