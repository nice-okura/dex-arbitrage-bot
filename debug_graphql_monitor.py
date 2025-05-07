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
from typing import Dict, Any, List, Optional

# ロギング設定
logger = logging.getLogger("dex_graphql_monitor")


def setup_logging(log_dir="./logs/graphql"):
    """モニタリング用のロギングをセットアップ"""
    os.makedirs(log_dir, exist_ok=True)

    # ファイル名に日付を含める
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = f"{log_dir}/graphql_{today}.log"

    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # 標準出力にも表示
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console)

    return logger


class GraphQLMonitor:
    def __init__(self, enabled=True, log_dir="./logs/graphql", save_responses=True):
        """
        GraphQLモニタリングの初期化

        Args:
            enabled: モニタリングを有効にするかどうか
            log_dir: ログディレクトリ
            save_responses: レスポンスボディを保存するかどうか
        """
        self.enabled = enabled
        self.log_dir = log_dir
        self.save_responses = save_responses

        if self.enabled:
            setup_logging(log_dir)
            # JSONレスポンス保存用ディレクトリ
            self.responses_dir = f"{log_dir}/responses"
            os.makedirs(self.responses_dir, exist_ok=True)

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
        logger.debug(f"GraphQL Request: {method} {url} ({duration:.4f}s)")

        # リクエストボディが存在する場合はログに出力
        if "body" in trace_config_ctx.request_info:
            body = trace_config_ctx.request_info["body"]
            if isinstance(body, dict) and "query" in body:
                query = body["query"].strip()
                # 長いクエリは短縮
                if len(query) > 500:
                    query = query[:250] + "..." + query[-250:]
                logger.debug(f"GraphQL Query: {query}")

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
        logger.error(f"GraphQL Request Error: {params.exception} ({duration:.4f}s)")

        # リクエスト情報も出力
        if hasattr(trace_config_ctx, "request_info"):
            url = trace_config_ctx.request_info["url"]
            method = trace_config_ctx.request_info["method"]
            logger.error(f"Failed Request: {method} {url}")

            if "body" in trace_config_ctx.request_info:
                body = trace_config_ctx.request_info["body"]
                if isinstance(body, dict) and "query" in body:
                    logger.error(f"Failed Query: {body['query'][:200]}...")

    async def trace_response_received(self, session, trace_config_ctx, params):
        """レスポンス受信時のトレース (on_response の代わり)"""
        if not self.enabled:
            return

        duration = time.monotonic() - trace_config_ctx.start
        status = params.response.status

        # 基本レスポンス情報をログに出力
        url = trace_config_ctx.request_info["url"]
        method = trace_config_ctx.request_info["method"]
        logger.info(
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
                                logger.error(
                                    f"GraphQL Error: {json.dumps(body_json['errors'])}"
                                )

                            # データがあるかチェック
                            if "data" in body_json:
                                # サマリー情報を出力
                                data_keys = list(body_json["data"].keys())
                                data_summary = {}

                                for key in data_keys:
                                    value = body_json["data"][key]
                                    if isinstance(value, list):
                                        data_summary[key] = f"Array[{len(value)}]"
                                    elif isinstance(value, dict):
                                        data_summary[key] = (
                                            f"Object{{{', '.join(value.keys())}}}"
                                        )
                                    else:
                                        data_summary[key] = str(value)

                                logger.info(f"GraphQL Data: {json.dumps(data_summary)}")

                            # レスポンスをファイルに保存
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            dex_name = url.split("/")[-1]  # URLからDEX名を抽出
                            filename = (
                                f"{self.responses_dir}/{timestamp}_{dex_name}.json"
                            )

                            with open(filename, "w") as f:
                                json.dump(body_json, f, indent=2)
                                logger.debug(f"レスポンスを保存: {filename}")

                        except json.JSONDecodeError:
                            logger.warning(
                                f"レスポンスはJSON形式ではありません: {body_str[:100]}..."
                            )
                    except UnicodeDecodeError:
                        logger.warning(
                            "レスポンスボディをUTF-8としてデコードできませんでした"
                        )

            except Exception as e:
                logger.error(f"レスポンス処理中にエラーが発生しました: {e}")

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
            logger.warning(
                "レスポンストレースイベントが利用できません。aiohttp のバージョンを確認してください。"
            )

        return trace_config


class TracedSession:
    """GraphQLモニタリング機能を持つHTTPセッション"""

    def __init__(self, monitor_enabled=True, save_responses=True):
        self.monitor = GraphQLMonitor(
            enabled=monitor_enabled, save_responses=save_responses
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


# 使用例
async def test_graphql_monitoring():
    """モニタリング機能のテスト"""
    print("GraphQLモニタリングテスト開始")

    # ディレクトリを作成
    os.makedirs("./logs/graphql/responses", exist_ok=True)

    # モニタリング機能を持つセッションを作成
    async with TracedSession() as session:
        # Uniswap V3のGraphQLエンドポイント
        url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-polygon"  # Polygonネットワーク用

        # テストクエリ
        query = """
        {
          pools(where: {token0_: {symbol_contains_nocase: "ETH"}, token1_: {symbol_contains_nocase: "USDT"}}, orderBy: liquidity, orderDirection: desc, first: 5) {
            id
            token0Price
            token1Price
            token0 {
              symbol
            }
            token1 {
              symbol
            }
            feeTier
          }
        }
        """

        try:
            # GraphQLリクエストを送信
            async with session.post(url, json={"query": query}) as response:
                data = await response.json()
                print(f"ステータスコード: {response.status}")
                print(f"取得したデータサンプル: {json.dumps(data, indent=2)[:200]}...")
                print(
                    f"データ取得成功！完全なレスポンスはログディレクトリに保存されています。"
                )

        except Exception as e:
            print(f"エラーが発生しました: {e}")

    print("GraphQLモニタリングテスト終了")


if __name__ == "__main__":
    asyncio.run(test_graphql_monitoring())
