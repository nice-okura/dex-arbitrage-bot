# src/graphql/client.py
"""GraphQLクライアント共通モジュール"""

import logging
import json
import aiohttp
import asyncio
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("dex_arbitrage_bot.graphql_client")

class GraphQLClient:
    """GraphQLクライアントクラス"""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None, 
                 timeout: float = 30.0, 
                 max_retries: int = 3, 
                 retry_delay: float = 2.0,
                 debug: bool = True):  # デバッグフラグを追加
        """
        GraphQLクライアントの初期化
        
        Args:
            session: 既存のaiohttp.ClientSessionがあれば指定
            timeout: リクエストタイムアウト時間（秒）
            max_retries: エラー時の最大リトライ回数
            retry_delay: リトライ間の待機時間（秒）
            debug: デバッグログ出力フラグ
        """
        self.session = session
        self._owned_session = False
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.debug = debug
    
    async def ensure_session(self):
        """セッションがなければ作成"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._owned_session = True
    
    async def close(self):
        """セッションのクローズ（自分で作成したセッションのみ）"""
        if self._owned_session and self.session:
            await self.session.close()
            self.session = None
            self._owned_session = False
    
    async def execute(self, url: str, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        GraphQLクエリを実行
        
        Args:
            url: GraphQLエンドポイントURL
            query: GraphQLクエリ
            variables: クエリ変数
            
        Returns:
            Dict[str, Any]: レスポンスデータ
        """
        await self.ensure_session()
        
        # リクエストペイロードの作成
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        # デバッグログ出力
        if self.debug:
            formatted_query = query.strip().replace('\n', ' ').replace('  ', ' ')
            truncated_query = formatted_query[:500] + "..." if len(formatted_query) > 500 else formatted_query
            logger.debug(f"GraphQL URL: {url}")
            logger.debug(f"GraphQL Query: {truncated_query}")
            if variables:
                logger.debug(f"GraphQL Variables: {json.dumps(variables)}")
        
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with self.session.post(url, json=payload, timeout=timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GraphQL request failed: {response.status} - {error_text}")
                        return {"data": None, "errors": [{"message": f"HTTP error: {response.status}"}]}
                    
                    data = await response.json()
                    
                    # デバッグログでレスポンスサマリを出力
                    if self.debug:
                        self._log_response_summary(data)
                    
                    # エラーのロギング
                    if "errors" in data:
                        logger.error(f"GraphQL errors: {json.dumps(data['errors'])}")
                    
                    return data
            
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                logger.warning(f"GraphQL request timed out (attempt {retry_count+1}/{self.max_retries+1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"GraphQL request failed (attempt {retry_count+1}/{self.max_retries+1}): {e}")
            
            # リトライの判断
            retry_count += 1
            if retry_count <= self.max_retries:
                await asyncio.sleep(self.retry_delay * retry_count)  # 指数バックオフ
        
        # 全リトライ失敗
        logger.error(f"All GraphQL request attempts failed: {last_error}")
        return {"data": None, "errors": [{"message": f"All requests failed: {last_error}"}]}
    
    def _log_response_summary(self, data: Dict[str, Any]):
        """GraphQLレスポンスのサマリをログに出力"""
        if "errors" in data:
            logger.debug(f"GraphQL Response contains errors: {len(data['errors'])} errors found")
            return
            
        if "data" in data:
            data_keys = list(data["data"].keys()) if data["data"] else []
            summary = {}
            
            for key in data_keys:
                value = data["data"][key]
                if isinstance(value, list):
                    summary[key] = f"Array[{len(value)}]"
                elif isinstance(value, dict):
                    field_names = list(value.keys())
                    summary[key] = f"Object{{{', '.join(field_names[:3])}}}" + ("..." if len(field_names) > 3 else "")
                else:
                    summary[key] = str(value)
            
            logger.debug(f"GraphQL Response Data: {json.dumps(summary)}")
        else:
            logger.debug("GraphQL Response: No data returned")
    
    async def execute_simple(self, url: str, query: str) -> Dict[str, Any]:
        """
        シンプルなGraphQLクエリ実行（変数なし）
        
        Args:
            url: GraphQLエンドポイントURL
            query: GraphQLクエリ文字列
            
        Returns:
            Dict[str, Any]: レスポンスデータ
        """
        return await self.execute(url, query)