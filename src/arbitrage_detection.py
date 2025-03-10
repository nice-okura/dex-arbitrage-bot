# src/arbitrage_detection.py
import asyncio
import logging
import time
from typing import Dict, List, Tuple, Any
import json

from src.config import AppConfig
from src.data_management import DataManager
from src.notification import SlackNotifier

logger = logging.getLogger("dex_arbitrage_bot.arbitrage_detection")

class ArbitrageDetector:
    def __init__(self, config: AppConfig, data_manager: DataManager, notifier: SlackNotifier):
        self.config = config
        self.data_manager = data_manager
        self.notifier = notifier
        
        # 通知履歴（クールダウン管理用）
        self.notification_history = {}
    
    async def start_detection(self):
        """裁定機会検出を開始する"""
        logger.info("裁定機会検出を開始しました")
        
        while True:
            try:
                # すべての通貨ペアに対して裁定機会を検出
                for pair in self.config.token_pairs:
                    pair_str = str(pair)
                    
                    # 最新の価格データを取得
                    prices = await self.data_manager.get_latest_prices(pair_str)
                    
                    if not prices or len(prices) < 2:
                        logger.debug(f"{pair_str}の価格データが不足しています")
                        continue
                    
                    # 裁定機会の検出
                    arbitrage_opportunities = self._detect_arbitrage(pair_str, prices)
                    
                    # 裁定機会が見つかった場合の処理
                    for opportunity in arbitrage_opportunities:
                        # 同じ裁定機会に対する通知のクールダウンチェック
                        opportunity_key = f"{opportunity['buy_exchange']}_{opportunity['sell_exchange']}_{pair_str}"
                        current_time = time.time()
                        
                        if opportunity_key in self.notification_history:
                            last_notified = self.notification_history[opportunity_key]
                            if current_time - last_notified < self.config.notification_cooldown:
                                logger.debug(f"通知クールダウン中: {opportunity_key}")
                                continue
                        
                        # 通知を送信
                        await self._notify_arbitrage(opportunity)
                        
                        # 通知履歴を更新
                        self.notification_history[opportunity_key] = current_time
                
                # 設定された間隔で待機
                await asyncio.sleep(self.config.price_update_interval)
                
            except Exception as e:
                logger.error(f"裁定機会検出中にエラーが発生しました: {e}", exc_info=True)
                await asyncio.sleep(5)  # エラー発生時は短い間隔で再試行
    
    def _detect_arbitrage(self, pair_str: str, prices: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """裁定機会を検出する"""
        opportunities = []
        
        # すべての取引所の組み合わせをチェック
        exchanges = list(prices.keys())
        
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1 = exchanges[i]
                exchange2 = exchanges[j]
                
                # 価格が取得できているか確認
                if not prices[exchange1] or not prices[exchange2]:
                    continue
                
                price1 = prices[exchange1].get("price", 0)
                price2 = prices[exchange2].get("price", 0)
                
                if price1 <= 0 or price2 <= 0:
                    continue
                
                # 価格差を計算
                price_diff_percent1 = (price2 - price1) / price1 * 100
                price_diff_percent2 = (price1 - price2) / price2 * 100
                
                # 手数料を考慮
                fee1 = self._get_exchange_fee(exchange1)
                fee2 = self._get_exchange_fee(exchange2)
                
                # スリッページを考慮
                slippage = self.config.slippage_tolerance
                
                # 総コスト（手数料 + スリッページ）
                total_cost1 = fee1 + fee2 + slippage
                total_cost2 = fee1 + fee2 + slippage
                
                # 裁定機会の判定
                if price_diff_percent1 > total_cost1 + self.config.arbitrage_threshold:
                    # exchange1で買い、exchange2で売る裁定取引
                    net_profit_percent = price_diff_percent1 - total_cost1
                    
                    opportunities.append({
                        "pair": pair_str,
                        "buy_exchange": exchange1,
                        "sell_exchange": exchange2,
                        "buy_price": price1,
                        "sell_price": price2,
                        "price_diff_percent": price_diff_percent1,
                        "fees_percent": fee1 + fee2,
                        "slippage_percent": slippage,
                        "net_profit_percent": net_profit_percent,
                        "timestamp": int(time.time())
                    })
                
                if price_diff_percent2 > total_cost2 + self.config.arbitrage_threshold:
                    # exchange2で買い、exchange1で売る裁定取引
                    net_profit_percent = price_diff_percent2 - total_cost2
                    
                    opportunities.append({
                        "pair": pair_str,
                        "buy_exchange": exchange2,
                        "sell_exchange": exchange1,
                        "buy_price": price2,
                        "sell_price": price1,
                        "price_diff_percent": price_diff_percent2,
                        "fees_percent": fee1 + fee2,
                        "slippage_percent": slippage,
                        "net_profit_percent": net_profit_percent,
                        "timestamp": int(time.time())
                    })
        
        return opportunities
    
    def _get_exchange_fee(self, exchange: str) -> float:
        """取引所の手数料を取得する"""
        # DEXの場合
        if exchange in self.config.dexes:
            return self.config.dexes[exchange].fee_percent
        
        # CEXの場合（一般的な取引手数料）
        cex_fees = {
            "bitbank": 0.12,
            "bitflyer": 0.15,
            "coincheck": 0.2,
            "zaif": 0.2,
            "bittrade": 0.15
        }
        
        return cex_fees.get(exchange, 0.2)  # デフォルトは0.2%
    
    async def _notify_arbitrage(self, opportunity: Dict[str, Any]):
        """裁定機会を通知する"""
        try:
            # 通知メッセージの作成
            message = self._create_notification_message(opportunity)
            
            # Slack通知の送信
            if self.notifier and self.notifier.is_enabled():
                await self.notifier.send_notification(message)
            
            # ログ出力
            logger.info(f"裁定機会を検出しました: {json.dumps(opportunity, indent=2)}")
            
            # データベースに記録
            await self.data_manager.save_arbitrage_opportunity(opportunity)
            
        except Exception as e:
            logger.error(f"裁定機会の通知中にエラーが発生しました: {e}", exc_info=True)
    
    def _create_notification_message(self, opportunity: Dict[str, Any]) -> str:
        """通知メッセージを作成する"""
        return (
            f"*裁定機会検出* :rocket:\n"
            f"*通貨ペア:* {opportunity['pair']}\n"
            f"*取引方法:* {opportunity['buy_exchange']}で買い、{opportunity['sell_exchange']}で売る\n"
            f"*価格差:* {opportunity['price_diff_percent']:.2f}%\n"
            f"*手数料:* {opportunity['fees_percent']:.2f}%\n"
            f"*スリッページ:* {opportunity['slippage_percent']:.2f}%\n"
            f"*純利益:* {opportunity['net_profit_percent']:.2f}%\n"
            f"*買値:* {opportunity['buy_price']:.8f}\n"
            f"*売値:* {opportunity['sell_price']:.8f}\n"
            f"*検出時刻:* <!date^{opportunity['timestamp']}^{{date_num}} {{time_secs}}|{opportunity['timestamp']}>"
        )