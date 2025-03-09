# src/data_management.py
import os
import json
import logging
import aioredis
import asyncio
import time
from typing import Dict, List, Any, Optional
import sqlite3

from src.config import AppConfig

logger = logging.getLogger("dex_arbitrage_bot.data_management")

class DataManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.redis = None
        self.db_path = "./data/arbitrage.db"
        
        # ディレクトリの作成
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    async def initialize(self):
        """データ管理モジュールを初期化する"""
        # RedisとSQLiteの初期化を分離し、片方が失敗しても他方は実行されるようにする
        
        # SQLiteデータベースの初期化（Redisの成否に関わらず実行）
        try:
            await self._init_sqlite_db()
            logger.info("SQLiteデータベースを初期化しました")
        except Exception as e:
            logger.error(f"SQLiteデータベースの初期化中にエラーが発生しました: {e}", exc_info=True)
            # SQLiteは必須なのでエラーを再スロー
            raise
        
        # Redisの接続設定（失敗してもプログラムは継続）
        try:
            self.redis = await aioredis.create_redis_pool(
                f"redis://{self.config.redis_host}:{self.config.redis_port}",
                password=self.config.redis_password or None,
                db=self.config.redis_db
            )
            logger.info("Redisに接続しました")
        except Exception as e:
            logger.warning(f"Redisに接続できませんでした: {e}")
            logger.info("Redisなしでインメモリキャッシュを使用して続行します")
            self.redis = None
            self.in_memory_cache = {}
    
    async def _init_sqlite_db(self):
        """SQLiteデータベースを初期化する"""
        # SQLiteデータベースは非同期操作に対応していないため、
        # run_in_executor を使用して別スレッドで実行する
        await asyncio.get_event_loop().run_in_executor(
            None, self._create_tables
        )
    
    def _create_tables(self):
        """データベーステーブルを作成する"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 価格データテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            pair TEXT NOT NULL,
            price REAL NOT NULL,
            liquidity REAL,
            timestamp INTEGER NOT NULL,
            UNIQUE(exchange, pair, timestamp)
        )
        ''')
        
        # 裁定機会テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            buy_exchange TEXT NOT NULL,
            sell_exchange TEXT NOT NULL,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            price_diff_percent REAL NOT NULL,
            fees_percent REAL NOT NULL,
            slippage_percent REAL NOT NULL,
            net_profit_percent REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    async def save_price(self, exchange: str, pair: str, price_data: Dict[str, Any], timestamp: int):
        """価格データを保存する"""
        try:
            # Redisに最新の価格データを保存
            if self.redis:
                # キー形式: price:{exchange}:{pair}
                key = f"price:{exchange}:{pair}"
                
                # 価格データをJSONに変換
                json_data = json.dumps({
                    "price": price_data.get("price", 0),
                    "liquidity": price_data.get("liquidity", 0),
                    "timestamp": timestamp
                })
                
                # Redisに保存（TTL: 1時間）
                await self.redis.setex(key, 3600, json_data)
                
                # 履歴データも保存（ソート済みセット）
                history_key = f"price_history:{exchange}:{pair}"
                await self.redis.zadd(history_key, timestamp, json_data)
                
                # 古いデータを削除（1時間より前のデータ）
                old_timestamp = timestamp - 3600
                await self.redis.zremrangebyscore(history_key, 0, old_timestamp)
            
            else:
                # インメモリキャッシュに保存
                key = f"price:{exchange}:{pair}"
                self.in_memory_cache[key] = {
                    "price": price_data.get("price", 0),
                    "liquidity": price_data.get("liquidity", 0),
                    "timestamp": timestamp
                }
            
            # SQLiteにも保存（長期保存用）
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self._save_price_to_sqlite, 
                exchange, 
                pair, 
                price_data.get("price", 0),
                price_data.get("liquidity", 0),
                timestamp
            )
            
        except Exception as e:
            logger.error(f"価格データの保存中にエラーが発生しました: {e}", exc_info=True)
    
    def _save_price_to_sqlite(self, exchange: str, pair: str, price: float, liquidity: float, timestamp: int):
        """SQLiteに価格データを保存する（同期処理）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR REPLACE INTO prices (exchange, pair, price, liquidity, timestamp) VALUES (?, ?, ?, ?, ?)",
                (exchange, pair, price, liquidity, timestamp)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"SQLiteへの価格データ保存中にエラーが発生しました: {e}", exc_info=True)
    
    async def get_latest_prices(self, pair: str) -> Dict[str, Dict[str, Any]]:
        """指定した通貨ペアの最新価格データを取得する"""
        result = {}
        
        try:
            if self.redis:
                # すべての取引所からの価格データを取得
                for exchange in list(self.config.dexes.keys()) + list(self.config.cexes.keys()):
                    key = f"price:{exchange}:{pair}"
                    data = await self.redis.get(key)
                    
                    if data:
                        price_data = json.loads(data)
                        result[exchange] = price_data
            
            else:
                # インメモリキャッシュから取得
                for exchange in list(self.config.dexes.keys()) + list(self.config.cexes.keys()):
                    key = f"price:{exchange}:{pair}"
                    if key in self.in_memory_cache:
                        result[exchange] = self.in_memory_cache[key]
            
        except Exception as e:
            logger.error(f"最新価格データの取得中にエラーが発生しました: {e}", exc_info=True)
        
        return result
    
    async def get_price_history(self, exchange: str, pair: str, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """指定した取引所と通貨ペアの価格履歴を取得する"""
        result = []
        
        try:
            if self.redis:
                # Redisから履歴データを取得
                history_key = f"price_history:{exchange}:{pair}"
                data = await self.redis.zrangebyscore(history_key, start_time, end_time, withscores=True)
                
                for item, score in data:
                    price_data = json.loads(item)
                    result.append(price_data)
            
            else:
                # SQLiteから履歴データを取得
                history_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._get_price_history_from_sqlite,
                    exchange,
                    pair,
                    start_time,
                    end_time
                )
                
                result = history_data
            
        except Exception as e:
            logger.error(f"価格履歴の取得中にエラーが発生しました: {e}", exc_info=True)
        
        return result
    
    def _get_price_history_from_sqlite(self, exchange: str, pair: str, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """SQLiteから価格履歴を取得する（同期処理）"""
        result = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM prices WHERE exchange = ? AND pair = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
                (exchange, pair, start_time, end_time)
            )
            
            rows = cursor.fetchall()
            
            for row in rows:
                result.append({
                    "price": row["price"],
                    "liquidity": row["liquidity"],
                    "timestamp": row["timestamp"]
                })
            
            conn.close()
            
        except Exception as e:
            logger.error(f"SQLiteからの価格履歴取得中にエラーが発生しました: {e}", exc_info=True)
        
        return result
    
    async def save_arbitrage_opportunity(self, opportunity: Dict[str, Any]):
        """裁定機会を保存する"""
        try:
            # SQLiteに保存
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._save_arbitrage_to_sqlite,
                opportunity
            )
            
        except Exception as e:
            logger.error(f"裁定機会の保存中にエラーが発生しました: {e}", exc_info=True)
    
    def _save_arbitrage_to_sqlite(self, opportunity: Dict[str, Any]):
        """SQLiteに裁定機会を保存する（同期処理）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO arbitrage_opportunities 
                (pair, buy_exchange, sell_exchange, buy_price, sell_price, price_diff_percent, 
                fees_percent, slippage_percent, net_profit_percent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity["pair"],
                    opportunity["buy_exchange"],
                    opportunity["sell_exchange"],
                    opportunity["buy_price"],
                    opportunity["sell_price"],
                    opportunity["price_diff_percent"],
                    opportunity["fees_percent"],
                    opportunity["slippage_percent"],
                    opportunity["net_profit_percent"],
                    opportunity["timestamp"]
                )
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"SQLiteへの裁定機会保存中にエラーが発生しました: {e}", exc_info=True)
    
    async def cleanup(self):
        """リソースをクリーンアップする"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            logger.info("Redisとの接続を終了しました")