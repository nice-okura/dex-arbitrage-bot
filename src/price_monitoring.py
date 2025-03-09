# src/price_monitoring.py
import asyncio
import logging
import time
from typing import Dict, Any, List, Tuple
import json
import aiohttp
from web3 import Web3
import os

from src.config import AppConfig, TokenPair
from src.data_management import DataManager
from src.contracts import get_erc20_contract, get_dex_contract, DEX_ABI

logger = logging.getLogger("dex_arbitrage_bot.price_monitoring")

class PriceMonitor:
    def __init__(self, config: AppConfig, data_manager: DataManager):
        self.config = config
        self.data_manager = data_manager
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")))
        
        # The Graph API用のエンドポイント
        self.quickswap_subgraph_url = "https://api.thegraph.com/subgraphs/name/sameepsi/quickswap-v3"
        self.sushiswap_subgraph_url = "https://api.thegraph.com/subgraphs/name/sushiswap/exchange-polygon"
        
        # 接続テスト
        try:
            connected = self.w3.is_connected()
            chain_id = self.w3.eth.chain_id
            logger.info(f"Polygonチェーンに接続しました: connected={connected}, chain_id={chain_id}")
        except Exception as e:
            logger.error(f"Polygonチェーンへの接続に失敗しました: {e}", exc_info=True)
            
        # 価格データのキャッシュ
        self.price_cache = {}
        self.last_notification_time = {}  # 通知のクールダウン管理用
    
    async def start_monitoring(self):
        """価格モニタリングを開始する"""
        logger.info("価格モニタリングを開始しました")
        
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
                
                # ログ出力
                logger.debug(f"価格データを更新しました: {json.dumps(all_prices, indent=2)}")
                
                # 設定された間隔で待機
                await asyncio.sleep(self.config.price_update_interval)
                
            except Exception as e:
                logger.error(f"価格モニタリング中にエラーが発生しました: {e}", exc_info=True)
                await asyncio.sleep(5)  # エラー発生時は短い間隔で再試行
    
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
        
        if dex_id == "quickswap":
            # QuickSwapからの価格取得（The Graph API + オンチェーン）
            prices = await self._fetch_quickswap_prices()
        elif dex_id == "sushiswap":
            # SushiSwapからの価格取得（The Graph API + オンチェーン）
            prices = await self._fetch_sushiswap_prices()
        else:
            # その他のDEXはオンチェーンデータから直接取得
            for pair in self.config.token_pairs:
                price_data = await self._fetch_onchain_price(dex_config, pair)
                if price_data:
                    prices[str(pair)] = price_data
        
        return prices
    
    async def _fetch_quickswap_prices(self) -> Dict[str, Any]:
        """QuickSwapから価格データを取得する（The Graph API使用）"""
        prices = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                for pair in self.config.token_pairs:
                    # The Graphからプール情報を取得
                    query = """
                    {
                      pools(where: {token0_: {symbol: "%s"}, token1_: {symbol: "%s"}}, orderBy: liquidity, orderDirection: desc, first: 1) {
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
                    
                    async with session.post(self.quickswap_subgraph_url, json={"query": query}) as response:
                        if response.status == 200:
                            data = await response.json()
                            pools = data.get("data", {}).get("pools", [])
                            
                            if pools:
                                pool = pools[0]
                                token0_symbol = pool["token0"]["symbol"]
                                token1_symbol = pool["token1"]["symbol"]
                                
                                # 正しい方向の価格を選択
                                if token0_symbol == pair.base:
                                    price = float(pool["token1Price"])
                                else:
                                    price = float(pool["token0Price"])
                                
                                # オンチェーンから流動性情報を取得して価格を補完
                                pool_address = pool["id"]
                                reserves = await self._get_pool_reserves(pool_address)
                                
                                prices[str(pair)] = {
                                    "price": price,
                                    "liquidity": float(pool["liquidity"]),
                                    "reserves": reserves
                                }
        
        except Exception as e:
            logger.error(f"QuickSwapからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices
    
    async def _fetch_sushiswap_prices(self) -> Dict[str, Any]:
        """SushiSwapから価格データを取得する（The Graph API使用）"""
        prices = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                for pair in self.config.token_pairs:
                    # The Graphからペア情報を取得
                    query = """
                    {
                      pairs(where: {token0_: {symbol: "%s"}, token1_: {symbol: "%s"}}, orderBy: reserveUSD, orderDirection: desc, first: 1) {
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
                    
                    async with session.post(self.sushiswap_subgraph_url, json={"query": query}) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get("data", {}).get("pairs", [])
                            
                            if pairs:
                                pair_data = pairs[0]
                                token0_symbol = pair_data["token0"]["symbol"]
                                token1_symbol = pair_data["token1"]["symbol"]
                                
                                # 正しい方向の価格を選択
                                if token0_symbol == pair.base:
                                    price = float(pair_data["token1Price"])
                                else:
                                    price = float(pair_data["token0Price"])
                                
                                # オンチェーンから流動性情報を取得して価格を補完
                                pair_address = pair_data["id"]
                                reserves = await self._get_pool_reserves(pair_address)
                                
                                prices[str(pair)] = {
                                    "price": price,
                                    "liquidity": float(pair_data["reserveUSD"]),
                                    "reserves": reserves
                                }
        
        except Exception as e:
            logger.error(f"SushiSwapからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices
    
    async def _get_pool_reserves(self, pool_address: str) -> Dict[str, float]:
        """プールの流動性情報を取得する"""
        try:
            # プールコントラクトのABI（簡略化）
            pool_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "reserve0", "type": "uint112"},
                        {"name": "reserve1", "type": "uint112"},
                        {"name": "blockTimestampLast", "type": "uint32"}
                    ],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # プールコントラクトのインスタンス化
            pool_contract = self.w3.eth.contract(address=self.w3.to_checksum_address(pool_address), abi=pool_abi)
            
            # reserves関数の呼び出し
            reserves = pool_contract.functions.getReserves().call()
            
            return {
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "timestamp": reserves[2]
            }
        
        except Exception as e:
            logger.error(f"プールの流動性情報取得中にエラーが発生しました: {e}", exc_info=True)
            return {"reserve0": 0, "reserve1": 0, "timestamp": 0}
    
    async def _fetch_onchain_price(self, dex_config, pair: TokenPair) -> Dict[str, Any]:
        """オンチェーンデータから直接価格を取得する"""
        try:
            # DEXルーターコントラクトのインスタンス化
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(dex_config.address),
                abi=DEX_ABI
            )
            
            # トークンアドレスの取得
            base_token_address = self.w3.to_checksum_address(self.config.token_addresses.get(pair.base, ""))
            quote_token_address = self.w3.to_checksum_address(self.config.token_addresses.get(pair.quote, ""))
            
            if not base_token_address or not quote_token_address:
                logger.warning(f"トークンアドレスが見つかりません: {pair}")
                return None
            
            # 価格取得（1単位のbaseトークンに対するquoteトークンの量）
            amount_in = 10**18  # 1 token with 18 decimals
            
            # getAmountsOut関数を呼び出して価格を取得
            try:
                amounts = router_contract.functions.getAmountsOut(
                    amount_in,
                    [base_token_address, quote_token_address]
                ).call()
                
                price = amounts[1] / amount_in
                
                return {
                    "price": price,
                    "liquidity": 0,  # オンチェーンからの簡易取得では流動性情報は取得しない
                    "timestamp": int(time.time())
                }
            
            except Exception as e:
                logger.error(f"価格取得中にエラーが発生しました: {pair}, {e}", exc_info=True)
                return None
        
        except Exception as e:
            logger.error(f"オンチェーン価格取得中にエラーが発生しました: {e}", exc_info=True)
            return None
    
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
        
        if cex_id == "binance":
            # Binanceからの価格取得
            prices = await self._fetch_binance_prices()
        elif cex_id == "coinbase":
            # Coinbaseからの価格取得
            prices = await self._fetch_coinbase_prices()
        
        return prices
    
    async def _fetch_binance_prices(self) -> Dict[str, Any]:
        """Binanceから価格データを取得する"""
        prices = {}
        binance_api_url = "https://api.binance.com/api/v3/ticker/price"
        
        try:
            async with aiohttp.ClientSession() as session:
                # すべての通貨ペアの価格を一度に取得
                async with session.get(binance_api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 監視対象の通貨ペアのみフィルタリング
                        for pair in self.config.token_pairs:
                            # Binanceの形式に変換（スペースなし）
                            binance_symbol = f"{pair.base}{pair.quote}"
                            
                            # 価格データを検索
                            for item in data:
                                if item["symbol"] == binance_symbol:
                                    prices[str(pair)] = {
                                        "price": float(item["price"]),
                                        "timestamp": int(time.time())
                                    }
                                    break
        
        except Exception as e:
            logger.error(f"Binanceからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices
    
    async def _fetch_coinbase_prices(self) -> Dict[str, Any]:
        """Coinbaseから価格データを取得する"""
        prices = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                for pair in self.config.token_pairs:
                    # Coinbaseの形式に変換（ハイフン区切り）
                    coinbase_symbol = f"{pair.base}-{pair.quote}"
                    coinbase_api_url = f"https://api.coinbase.com/v2/prices/{coinbase_symbol}/spot"
                    
                    async with session.get(coinbase_api_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if "data" in data and "amount" in data["data"]:
                                prices[str(pair)] = {
                                    "price": float(data["data"]["amount"]),
                                    "timestamp": int(time.time())
                                }
        
        except Exception as e:
            logger.error(f"Coinbaseからの価格取得中にエラーが発生しました: {e}", exc_info=True)
        
        return prices