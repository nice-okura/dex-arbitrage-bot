#!/usr/bin/env python3
# view_data.py - DEXアービトラージボットのデータ閲覧ツール

import sqlite3
import argparse
import time
import json
import os
from tabulate import tabulate
import redis
from datetime import datetime


def connect_to_db(db_path="./data/arbitrage.db"):
    """SQLiteデータベースに接続する"""
    if not os.path.exists(db_path):
        print(f"エラー: データベースファイル {db_path} が見つかりません。")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 行をディクショナリとして返す
        return conn
    except Exception as e:
        print(f"データベース接続エラー: {e}")
        return None


def connect_to_redis(host="localhost", port=6379, db=0, password=None):
    """Redisに接続する"""
    try:
        r = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        r.ping()  # 接続テスト
        return r
    except Exception as e:
        print(f"Redis接続エラー: {e}")
        print("Redisデータは表示できません。SQLiteのみ参照します。")
        return None


def format_timestamp(timestamp):
    """UNIXタイムスタンプを読みやすい形式に変換する"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def show_latest_prices(conn, redis_conn=None, pair=None, exchange=None, limit=10):
    """最新の価格データを表示する"""
    query = "SELECT * FROM prices"
    params = []
    
    # フィルタリング条件を追加
    conditions = []
    if pair:
        conditions.append("pair = ?")
        params.append(pair)
    if exchange:
        conditions.append("exchange = ?")
        params.append(exchange)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # 並び替えと制限
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        print("指定された条件に一致する価格データはありません。")
        return
    
    # データをテーブル形式で表示
    table_data = []
    for row in rows:
        table_data.append({
            "取引所": row["exchange"],
            "通貨ペア": row["pair"],
            "価格": row["price"],
            "流動性": row["liquidity"] if row["liquidity"] else "N/A",
            "タイムスタンプ": format_timestamp(row["timestamp"])
        })
    
    print("\n=== 最新の価格データ ===")
    print(tabulate(table_data, headers="keys", tablefmt="grid"))
    
    # Redisからも最新データを取得（存在する場合）
    if redis_conn:
        try:
            print("\n=== Redisからの最新価格データ（キャッシュ） ===")
            redis_data = []
            
            # フィルタリング条件に基づいてRedisキーを構築
            pattern = "price:*"
            if exchange and pair:
                pattern = f"price:{exchange}:{pair}"
            elif exchange:
                pattern = f"price:{exchange}:*"
            elif pair:
                pattern = f"price:*:{pair}"
            
            for key in redis_conn.keys(pattern):
                try:
                    data = json.loads(redis_conn.get(key))
                    parts = key.split(":")
                    if len(parts) >= 3:
                        redis_data.append({
                            "取引所": parts[1],
                            "通貨ペア": parts[2],
                            "価格": data.get("price", "N/A"),
                            "流動性": data.get("liquidity", "N/A"),
                            "タイムスタンプ": format_timestamp(data.get("timestamp", 0))
                        })
                except:
                    pass
            
            if redis_data:
                print(tabulate(redis_data, headers="keys", tablefmt="grid"))
            else:
                print("Redisに該当するデータはありません。")
        except Exception as e:
            print(f"Redisデータの取得中にエラーが発生しました: {e}")


def show_arbitrage_opportunities(conn, min_profit=0.5, start_time=None, end_time=None, limit=10):
    """裁定機会のデータを表示する"""
    query = "SELECT * FROM arbitrage_opportunities"
    params = []
    
    # フィルタリング条件を追加
    conditions = []
    
    if min_profit > 0:
        conditions.append("net_profit_percent >= ?")
        params.append(min_profit)
    
    if start_time:
        conditions.append("timestamp >= ?")
        params.append(start_time)
    
    if end_time:
        conditions.append("timestamp <= ?")
        params.append(end_time)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # 並び替えと制限
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        print("指定された条件に一致する裁定機会データはありません。")
        return
    
    # データをテーブル形式で表示
    table_data = []
    for row in rows:
        table_data.append({
            "通貨ペア": row["pair"],
            "買い取引所": row["buy_exchange"],
            "売り取引所": row["sell_exchange"],
            "買値": row["buy_price"],
            "売値": row["sell_price"],
            "価格差 (%)": row["price_diff_percent"],
            "手数料 (%)": row["fees_percent"],
            "純利益 (%)": row["net_profit_percent"],
            "検出時刻": format_timestamp(row["timestamp"])
        })
    
    print("\n=== 裁定取引機会 ===")
    print(tabulate(table_data, headers="keys", tablefmt="grid"))


def show_exchange_summary(conn):
    """取引所ごとの統計情報を表示する"""
    cursor = conn.cursor()
    
    # 取引所ごとのデータ件数
    cursor.execute("""
    SELECT exchange, COUNT(*) as count
    FROM prices
    GROUP BY exchange
    ORDER BY count DESC
    """)
    exchange_counts = cursor.fetchall()
    
    # 取引所ごとの最新データのタイムスタンプ
    cursor.execute("""
    SELECT exchange, MAX(timestamp) as latest_timestamp
    FROM prices
    GROUP BY exchange
    """)
    latest_timestamps = {row["exchange"]: row["latest_timestamp"] for row in cursor.fetchall()}
    
    # 結果表示
    table_data = []
    for row in exchange_counts:
        exchange = row["exchange"]
        latest = latest_timestamps.get(exchange, 0)
        latest_formatted = format_timestamp(latest) if latest else "N/A"
        
        table_data.append({
            "取引所": exchange,
            "データ件数": row["count"],
            "最新データ時刻": latest_formatted,
            "経過時間(分)": round((time.time() - latest) / 60, 1) if latest else "N/A"
        })
    
    print("\n=== 取引所サマリー ===")
    print(tabulate(table_data, headers="keys", tablefmt="grid"))


def show_pair_summary(conn):
    """通貨ペアごとの統計情報を表示する"""
    cursor = conn.cursor()
    
    # 通貨ペアごとのデータ件数
    cursor.execute("""
    SELECT pair, COUNT(*) as count
    FROM prices
    GROUP BY pair
    ORDER BY count DESC
    """)
    pair_counts = cursor.fetchall()
    
    # 通貨ペアごとの価格範囲
    cursor.execute("""
    SELECT pair, MIN(price) as min_price, MAX(price) as max_price, AVG(price) as avg_price
    FROM prices
    GROUP BY pair
    """)
    price_stats = {row["pair"]: (row["min_price"], row["max_price"], row["avg_price"]) for row in cursor.fetchall()}
    
    # 結果表示
    table_data = []
    for row in pair_counts:
        pair = row["pair"]
        stats = price_stats.get(pair, (0, 0, 0))
        
        table_data.append({
            "通貨ペア": pair,
            "データ件数": row["count"],
            "最小価格": round(stats[0], 8),
            "最大価格": round(stats[1], 8),
            "平均価格": round(stats[2], 8)
        })
    
    print("\n=== 通貨ペアサマリー ===")
    print(tabulate(table_data, headers="keys", tablefmt="grid"))


def main():
    parser = argparse.ArgumentParser(description="DEXアービトラージボットのデータ閲覧ツール")
    parser.add_argument("--db", default="./data/arbitrage.db", help="SQLiteデータベースのパス")
    parser.add_argument("--redis-host", default="localhost", help="Redisホスト")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redisポート")
    parser.add_argument("--redis-db", type=int, default=0, help="RedisのDB番号")
    parser.add_argument("--redis-password", help="Redisパスワード")
    
    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")
    
    # 価格データ表示コマンド
    prices_parser = subparsers.add_parser("prices", help="価格データを表示")
    prices_parser.add_argument("--pair", help="フィルタリングする通貨ペア (例: BTC/JPY)")
    prices_parser.add_argument("--exchange", help="フィルタリングする取引所 (例: bitbank)")
    prices_parser.add_argument("--limit", type=int, default=10, help="表示する行数")
    
    # 裁定機会表示コマンド
    arb_parser = subparsers.add_parser("arbitrage", help="裁定機会を表示")
    arb_parser.add_argument("--min-profit", type=float, default=0.5, help="最小利益割合 (%)")
    arb_parser.add_argument("--start-time", help="開始時間 (YYYY-MM-DD HH:MM:SS)")
    arb_parser.add_argument("--end-time", help="終了時間 (YYYY-MM-DD HH:MM:SS)")
    arb_parser.add_argument("--limit", type=int, default=10, help="表示する行数")
    
    # 取引所サマリー表示コマンド
    subparsers.add_parser("exchanges", help="取引所ごとの統計情報を表示")
    
    # 通貨ペアサマリー表示コマンド
    subparsers.add_parser("pairs", help="通貨ペアごとの統計情報を表示")
    
    args = parser.parse_args()
    
    # データベース接続
    conn = connect_to_db(args.db)
    if not conn:
        return
    
    # Redis接続（オプショナル）
    redis_conn = None
    try:
        redis_conn = connect_to_redis(
            host=args.redis_host,
            port=args.redis_port,
            db=args.redis_db,
            password=args.redis_password
        )
    except:
        pass
    
    try:
        if args.command == "prices":
            show_latest_prices(conn, redis_conn, args.pair, args.exchange, args.limit)
        
        elif args.command == "arbitrage":
            # 時間文字列をタイムスタンプに変換
            start_time = None
            end_time = None
            
            if args.start_time:
                start_time = int(datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S").timestamp())
            
            if args.end_time:
                end_time = int(datetime.strptime(args.end_time, "%Y-%m-%d %H:%M:%S").timestamp())
            
            show_arbitrage_opportunities(conn, args.min_profit, start_time, end_time, args.limit)
        
        elif args.command == "exchanges":
            show_exchange_summary(conn)
        
        elif args.command == "pairs":
            show_pair_summary(conn)
        
        else:
            # コマンドが指定されていない場合は簡易サマリーを表示
            print("DEXアービトラージボット データ閲覧ツール")
            print("コマンドを指定してください。利用可能なコマンド: prices, arbitrage, exchanges, pairs")
            print("\n簡易統計情報:")
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM prices")
            price_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM arbitrage_opportunities")
            arb_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT exchange) FROM prices")
            exchange_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT pair) FROM prices")
            pair_count = cursor.fetchone()[0]
            
            print(f" - 価格データ件数: {price_count}")
            print(f" - 裁定機会件数: {arb_count}")
            print(f" - 監視取引所数: {exchange_count}")
            print(f" - 監視通貨ペア数: {pair_count}")
            
            print("\n詳細を見るには、コマンドライン引数を指定してください。例:")
            print("  python view_data.py prices --pair BTC/JPY")
            print("  python view_data.py arbitrage --min-profit 1.0")
            print("  python view_data.py exchanges")
            print("  python view_data.py pairs")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()