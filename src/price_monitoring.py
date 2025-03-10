# src/price_monitoring.py
import asyncio
import logging
import time
import os
import json
from typing import Dict, Any, List, Tuple
import aiohttp

from src.config import AppConfig, TokenPair
from src.data_management import DataManager

logger = logging.getLogger("dex_arbitrage_bot.price_monitoring")

class PriceMonitor:
    def __init__(self, config: AppConfig, data_manager: DataManager):
        self.config = config
        self.data_manager = data_manager
        
        # 価格データのキャッシュ
        self.price_cache = {}
        self.session = None
    
    async def start_monitoring(self):
        """価格モニタリングを開始する"""
        logger.info("価格モニタリングを開始しました")
        
        # HTTPセッションの作成
        self.session = aiohttp.ClientSession()
        
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
                
                async with self.session.post(dex_config.api_url, json={"query": query}) as response:
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
                            
                            prices[str(pair)] = {
                                "price": price,
                                "liquidity": float(pool["liquidity"]) if "liquidity" in pool else 0,
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"Uniswap V3からの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_quickswap_prices(self, dex_config) -> Dict[str, Any]:
        """QuickSwapから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
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
                
                async with self.session.post(dex_config.api_url, json={"query": query}) as response:
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
                            
                            prices[str(pair)] = {
                                "price": price,
                                "liquidity": float(pool.get("totalValueLockedUSD", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"QuickSwapからの価格取得中にエラーが発生しました({pair}): {e}")
        
        return prices
    
    async def _fetch_sushiswap_prices(self, dex_config) -> Dict[str, Any]:
        """SushiSwapから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
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
                
                async with self.session.post(dex_config.api_url, json={"query": query}) as response:
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
                            
                            prices[str(pair)] = {
                                "price": price,
                                "liquidity": float(pair_data.get("reserveUSD", 0)),
                                "timestamp": int(time.time())
                            }
            except Exception as e:
                logger.error(f"SushiSwapからの価格取得中にエラーが発生しました({pair}): {e}")
        
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
        """Balancerから価格データを取得する"""
        prices = {}
        
        for pair in self.config.token_pairs:
            try:
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
                
                async with self.session.post(dex_config.api_url, json={"query": query}) as response:
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
                                    
                                    prices[str(pair)] = {
                                        "price": price,
                                        "liquidity": float(pool.get("totalLiquidity", 0)),
                                        "timestamp": int(time.time())
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