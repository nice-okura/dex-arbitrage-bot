#!/usr/bin/env python3
# debug_graphql_monitor.py - GraphQLリクエスト/レスポンスモニタリングモジュール

import logging
import json
import os
import time
from datetime import datetime
import asyncio
import aiohttp
from aiohttp import TraceConfig
from typing import Dict, Any, List, Optional, Union, Callable
from dotenv import load_dotenv

# GraphQLクエリの共通モジュールをインポート
from src.graphql import (
    get_uniswap_query,
    get_sushiswap_query,
    get_quickswap_query,
    get_balancer_query
)

# 環境変数の読み込み
load_dotenv()

# The Graph API Key
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")

# The Graph Gateway URL
GRAPH_BASE_URL = "https://gateway.thegraph.com/api"

# サブグラフID
SUBGRAPH_IDS = {
    "uniswap": os.getenv("UNISWAP_SUBGRAPH_ID", "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"),
    "sushiswap": os.getenv("SUSHISWAP_SUBGRAPH_ID", "CKaCne3uUUEqT7Ei9jjZbQqTLntEno9LnFa4JnsqqBma"),
    "quickswap": os.getenv("QUICKSWAP_SUBGRAPH_ID", "FqsRcH1XqSjqVx9GRTvEJe959aCbKrcyGgDWBrUkG24g"),
    "balancer": os.getenv("BALANCER_SUBGRAPH_ID", "H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp"),
}

# ロギング設定
logger = logging.getLogger("dex_graphql_monitor")

def setup_logging(log_dir="./logs/graphql", log_level=logging.DEBUG):
    """モニタリング用のロギングをセットアップ"""
    os.makedirs(log_dir, exist_ok=True)

    # ファイル名に日付を含める
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"{log_dir}/graphql_{today}.log"

    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # ファイルハンドラーの設定
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    file_handler.setLevel(log_level)

    # 標準出力ハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    console_handler.setLevel(log_level)

    # 既存のハンドラーを削除してから追加（二重ログを防止）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # GraphQLモニター専用ロガーの設定
    monitor_logger = logging.getLogger("dex_graphql_monitor")
    monitor_logger.setLevel(log_level)

    return monitor_logger

def get_graph_url(subgraph_id):
    """サブグラフIDからGraphQLエンドポイントURLを生成"""
    if not GRAPH_API_KEY:
        logger.warning("GRAPH_API_KEY環境変数が設定されていません。APIリクエストは失敗します。")
        return f"{GRAPH_BASE_URL}/[API-KEY-REQUIRED]/subgraphs/id/{subgraph_id}"
    return f"{GRAPH_BASE_URL}/{GRAPH_API_KEY}/subgraphs/id/{subgraph_id}"

class GraphQLMonitor:
    """GraphQLモニタリングクラス"""
    
    def __init__(self, 
                 enabled: bool = True, 
                 log_dir: str = "./logs/graphql", 
                 save_responses: bool = True,
                 log_level: int = logging.DEBUG):
        """
        GraphQLモニタリングの初期化

        Args:
            enabled: モニタリングを有効にするかどうか
            log_dir: ログディレクトリ
            save_responses: レスポンスボディを保存するかどうか
            log_level: ログレベル
        """
        self.enabled = enabled
        self.log_dir = log_dir
        self.save_responses = save_responses
        self.log_level = log_level

        if self.enabled:
            self.logger = setup_logging(log_dir, log_level)
            # JSONレスポンス保存用ディレクトリ
            self.responses_dir = f"{log_dir}/responses"
            os.makedirs(self.responses_dir, exist_ok=True)
            self.logger.info("GraphQLモニターを初期化しました")

    async def trace_request_start(self, session, trace_config_ctx, params):
        """リクエスト開始時のトレース"""
        if not self.enabled:
            return

        trace_config_ctx.start = time.monotonic()
        trace_config_ctx.request_info = {
            "method": params.method,
            "url": str(params.url),
            "headers": dict(params.headers),
        }

        # リクエストボディをキャプチャ
        if hasattr(params, "data") and params.data:
            try:
                if isinstance(params.data, bytes):
                    body = params.data.decode("utf-8")
                    try:
                        body_json = json.loads(body)
                        trace_config_ctx.request_info["body"] = body_json
                        
                        # GraphQLクエリをログに出力
                        if isinstance(body_json, dict) and "query" in body_json:
                            query = body_json["query"].strip()
                            # 長いクエリは短縮
                            if len(query) > 500:
                                query = query[:250] + "..." + query[-250:]
                            self.logger.debug(f"GraphQL Query: {query}")
                            
                            # 変数もログに出力
                            if "variables" in body_json and body_json["variables"]:
                                self.logger.debug(f"GraphQL Variables: {json.dumps(body_json['variables'])}")
                    except:
                        trace_config_ctx.request_info["body"] = body
                else:
                    trace_config_ctx.request_info["body"] = params.data
            except:
                trace_config_ctx.request_info["body"] = "Failed to decode request body"

    async def trace_request_end(self, session, trace_config_ctx, params):
        """リクエスト終了時のトレース"""
        if not self.enabled:
            return

        duration = time.monotonic() - trace_config_ctx.start
        trace_config_ctx.request_info["duration"] = duration

        # リクエスト情報をログに出力
        url = trace_config_ctx.request_info["url"]
        method = trace_config_ctx.request_info["method"]
        self.logger.debug(f"GraphQL Request: {method} {url} ({duration:.4f}s)")

    async def trace_response_chunk_received(self, session, trace_config_ctx, params):
        """レスポンスチャンク受信時のトレース"""
        if not self.enabled or not self.save_responses:
            return

        # レスポンスチャンクを保存
        if not hasattr(trace_config_ctx, "response_chunks"):
            trace_config_ctx.response_chunks = []

        if params.chunk:
            trace_config_ctx.response_chunks.append(params.chunk)

    async def trace_request_exception(self, session, trace_config_ctx, params):
        """リクエスト例外時のトレース"""
        if not self.enabled:
            return

        duration = time.monotonic() - trace_config_ctx.start
        self.logger.error(f"GraphQL Request Error: {params.exception} ({duration:.4f}s)")

        # リクエスト情報も出力
        if hasattr(trace_config_ctx, "request_info"):
            url = trace_config_ctx.request_info["url"]
            method = trace_config_ctx.request_info["method"]
            self.logger.error(f"Failed Request: {method} {url}")

            if "body" in trace_config_ctx.request_info:
                body = trace_config_ctx.request_info["body"]
                if isinstance(body, dict) and "query" in body:
                    self.logger.error(f"Failed Query: {body['query'][:200]}...")

    async def trace_response_received(self, session, trace_config_ctx, params):
        """レスポンス受信時のトレース (on_response の代わり)"""
        if not self.enabled:
            return

        duration = time.monotonic() - trace_config_ctx.start
        status = params.response.status

        # 基本レスポンス情報をログに出力
        url = trace_config_ctx.request_info["url"]
        method = trace_config_ctx.request_info["method"]
        self.logger.info(
            f"GraphQL Response: {method} {url} - Status: {status} ({duration:.4f}s)"
        )

        if self.save_responses:
            try:
                # レスポンスボディを結合
                if (
                    hasattr(trace_config_ctx, "response_chunks")
                    and trace_config_ctx.response_chunks
                ):
                    body_bytes = b"".join(trace_config_ctx.response_chunks)
                    try:
                        body_str = body_bytes.decode("utf-8")

                        try:
                            # JSONとしてパース
                            body_json = json.loads(body_str)

                            # エラーをチェック
                            if "errors" in body_json:
                                self.logger.error(
                                    f"GraphQL Error: {json.dumps(body_json['errors'])}"
                                )

                            # データがあるかチェック
                            if "data" in body_json:
                                # サマリー情報を出力
                                data_keys = list(body_json["data"].keys()) if body_json["data"] else []
                                data_summary = {}

                                for key in data_keys:
                                    value = body_json["data"][key]
                                    if isinstance(value, list):
                                        data_summary[key] = f"Array[{len(value)}]"
                                    elif isinstance(value, dict):
                                        data_summary[key] = (
                                            f"Object{{{', '.join(list(value.keys())[:5])}}}" +
                                            ("..." if len(value.keys()) > 5 else "")
                                        )
                                    else:
                                        data_summary[key] = str(value)

                                self.logger.info(f"GraphQL Data: {json.dumps(data_summary)}")

                            # レスポンスをファイルに保存
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            dex_name = self._extract_dex_name(url)
                            filename = f"{self.responses_dir}/{timestamp}_{dex_name}.json"

                            with open(filename, "w") as f:
                                json.dump(body_json, f, indent=2)
                                self.logger.debug(f"レスポンスを保存: {filename}")

                        except json.JSONDecodeError:
                            self.logger.warning(
                                f"レスポンスはJSON形式ではありません: {body_str[:100]}..."
                            )
                    except UnicodeDecodeError:
                        self.logger.warning(
                            "レスポンスボディをUTF-8としてデコードできませんでした"
                        )

            except Exception as e:
                self.logger.error(f"レスポンス処理中にエラーが発生しました: {e}")

    def _extract_dex_name(self, url: str) -> str:
        """URLからDEX名を抽出する"""
        if "uniswap" in url.lower():
            return "uniswap"
        elif "sushiswap" in url.lower():
            return "sushiswap"
        elif "quickswap" in url.lower():
            return "quickswap"
        elif "balancer" in url.lower():
            return "balancer"
        elif "curve" in url.lower():
            return "curve"
        else:
            # サブグラフIDから取得
            for dex, subgraph_id in SUBGRAPH_IDS.items():
                if subgraph_id in url:
                    return dex
            
            # URLの最後の部分を使用
            parts = url.split("/")
            return parts[-1] if parts else "unknown"

    def create_trace_config(self):
        """aiohttp用のトレース設定を作成"""
        if not self.enabled:
            return None

        trace_config = TraceConfig()
        trace_config.on_request_start.append(self.trace_request_start)
        trace_config.on_request_end.append(self.trace_request_end)
        trace_config.on_response_chunk_received.append(
            self.trace_response_chunk_received
        )
        trace_config.on_request_exception.append(self.trace_request_exception)

        # on_response は aiohttp の一部のバージョンでは利用できないため、代わりに on_response_received を使用
        # TraceConfig に利用可能なイベントは aiohttp のバージョンによって異なる
        if hasattr(trace_config, "on_response"):
            trace_config.on_response.append(self.trace_response_received)
        elif hasattr(trace_config, "on_response_received"):
            trace_config.on_response_received.append(self.trace_response_received)
        else:
            # 両方とも利用できない場合は警告を出す
            self.logger.warning(
                "レスポンストレースイベントが利用できません。aiohttp のバージョンを確認してください。"
            )

        return trace_config


class TracedSession:
    """GraphQLモニタリング機能を持つHTTPセッション"""

    def __init__(self, 
                 monitor_enabled: bool = True, 
                 save_responses: bool = True,
                 log_level: int = logging.DEBUG,
                 log_dir: str = "./logs/graphql"):
        """
        GraphQLモニタリング機能を持つHTTPセッションの初期化
        
        Args:
            monitor_enabled: モニタリングを有効にするかどうか
            save_responses: レスポンスボディを保存するかどうか
            log_level: ログレベル
            log_dir: ログディレクトリ
        """
        self.monitor = GraphQLMonitor(
            enabled=monitor_enabled, 
            save_responses=save_responses,
            log_level=log_level,
            log_dir=log_dir
        )
        self.session = None

    async def __aenter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        trace_config = self.monitor.create_trace_config()

        if trace_config:
            self.session = aiohttp.ClientSession(trace_configs=[trace_config])
        else:
            self.session = aiohttp.ClientSession()

        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        if self.session:
            await self.session.close()


# DEXテスト用クラス
class DEXTester:
    """各DEXのGraphQLクエリをテストするクラス"""
    
    def __init__(self, log_dir: str = "./logs/graphql"):
        """
        DEXテスターの初期化
        
        Args:
            log_dir: ログディレクトリ
        """
        self.log_dir = log_dir
        self.logger = logging.getLogger("dex_graphql_monitor.tester")

    async def test_dexes(self, dexes: List[str] = None, pairs: List[Dict[str, str]] = None):
        """
        指定したDEXとトークンペアに対するGraphQLクエリをテスト実行
        
        Args:
            dexes: テスト対象のDEXリスト。Noneの場合はすべて。
            pairs: テスト対象のトークンペア。Noneの場合はデフォルト。
        """
        # デフォルトのDEX
        if dexes is None:
            dexes = ["uniswap", "sushiswap", "quickswap", "balancer"]
        
        # デフォルトのトークンペア
        if pairs is None:
            pairs = [
                {"base": "ETH", "quote": "USDT"},
                {"base": "MATIC", "quote": "USDT"},
                {"base": "WBTC", "quote": "ETH"}
            ]
        
        self.logger.info(f"テスト対象DEX: {dexes}")
        self.logger.info(f"テスト対象通貨ペア: {pairs}")
        
        # APIキーが設定されているか確認
        if not GRAPH_API_KEY:
            self.logger.error("GRAPH_API_KEY環境変数が設定されていません。The Graph APIはAPIキーがないとアクセスできません。")
            self.logger.error(".envファイルにGRAPH_API_KEYを設定してください。")
            return
        
        # トレースセッションを使用
        async with TracedSession(monitor_enabled=True, save_responses=True) as session:
            # 各DEXに対してテスト
            for dex in dexes:
                if dex not in SUBGRAPH_IDS:
                    self.logger.warning(f"未知のDEX: {dex}、スキップします。")
                    continue
                
                subgraph_id = SUBGRAPH_IDS[dex]
                url = get_graph_url(subgraph_id)
                query_func = None
                
                # クエリ関数を決定
                if dex == "uniswap":
                    query_func = get_uniswap_query
                elif dex == "sushiswap":
                    query_func = get_sushiswap_query
                elif dex == "quickswap":
                    query_func = get_quickswap_query
                elif dex == "balancer":
                    query_func = get_balancer_query
                
                if not query_func:
                    self.logger.warning(f"{dex}のクエリ関数が見つかりません。スキップします。")
                    continue
                
                self.logger.info(f"{dex.upper()}のテストを開始します...")
                
                # 各ペアに対してテスト
                for pair in pairs:
                    base = pair["base"]
                    quote = pair["quote"]
                    self.logger.info(f"  ペア: {base}/{quote}")
                    
                    # クエリの生成
                    if dex == "sushiswap" or dex == "balancer":
                        # where句なしクエリを使用（クライアントサイドフィルタリング）
                        query = query_func("", "", 100)
                        self.logger.debug(f"  {dex} クエリ（クライアントサイドフィルタリング）: {query[:100]}...")
                    else:
                        # 通常のクエリを使用
                        query = query_func(base, quote, 5)
                        self.logger.debug(f"  {dex} クエリ: {query[:100]}...")
                    
                    # クエリの実行
                    try:
                        start_time = time.time()
                        async with session.post(url, json={"query": query}) as response:
                            duration = time.time() - start_time
                            
                            if response.status == 200:
                                data = await response.json()
                                
                                # エラーチェック
                                if "errors" in data:
                                    self.logger.error(f"  エラー: {json.dumps(data['errors'])}")
                                    continue
                                
                                # データチェック
                                if "data" not in data or not data["data"]:
                                    self.logger.warning(f"  データがありません。")
                                    continue
                                
                                # データの存在をログに出力
                                data_keys = list(data["data"].keys())
                                for key in data_keys:
                                    value = data["data"][key]
                                    if isinstance(value, list):
                                        self.logger.info(f"  {key}: {len(value)}件の結果")
                                    else:
                                        self.logger.info(f"  {key}: {type(value).__name__}")
                                
                                self.logger.info(f"  クエリ実行: {duration:.4f}秒")
                            else:
                                self.logger.error(f"  HTTPエラー: {response.status}")
                    
                    except Exception as e:
                        self.logger.error(f"  クエリ実行中にエラーが発生しました: {e}")
                
                # DEX間の待機
                await asyncio.sleep(1)


# 使用例
async def test_graphql_monitoring():
    """モニタリング機能のテスト"""
    print("GraphQLモニタリングテスト開始")

    # コマンドライン引数のパース
    import argparse
    parser = argparse.ArgumentParser(description="GraphQLモニタリングテスト")
    parser.add_argument("--dex", choices=["all", "uniswap", "sushiswap", "quickswap", "balancer"],
                        default="all", help="テスト対象のDEX")
    parser.add_argument("--pair", help="テスト対象の通貨ペア（例: ETH/USDT）")
    parser.add_argument("--debug", action="store_true", help="詳細なデバッグ情報を出力します")
    parser.add_argument("--save", action="store_true", help="レスポンスを保存します")
    args = parser.parse_args()

    # ロギングレベルの設定
    log_level = logging.DEBUG if args.debug else logging.INFO

    # ディレクトリを作成
    log_dir = "./logs/graphql"
    os.makedirs(f"{log_dir}/responses", exist_ok=True)

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

    # DEXテスターの初期化
    tester = DEXTester(log_dir=log_dir)

    # テスト対象のDEX
    dexes = None
    if args.dex != "all":
        dexes = [args.dex]

    # テスト対象のペア
    pairs = None
    if args.pair:
        base, quote = args.pair.split("/")
        pairs = [{"base": base, "quote": quote}]

    # テスト実行
    await tester.test_dexes(dexes=dexes, pairs=pairs)

    print("GraphQLモニタリングテスト終了")


if __name__ == "__main__":
    # ロギングの基本設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    asyncio.run(test_graphql_monitoring())