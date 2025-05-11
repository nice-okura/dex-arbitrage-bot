# src/graphql/parsers.py
"""GraphQLレスポンスのパーサモジュール"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("dex_arbitrage_bot.graphql_parsers")

def parse_uniswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    Uniswap V3のレスポンスをパース
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル
        quote_token: クオートトークンのシンボル
        
    Returns:
        List[Dict[str, Any]]: パース済みプールデータのリスト
    """
    results = []
    
    try:
        pools = response.get("data", {}).get("pools", [])
        
        for pool in pools:
            token0_symbol = pool["token0"]["symbol"]
            token1_symbol = pool["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_token.upper():
                price = float(pool["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(pool["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            results.append({
                "pool_id": pool["id"],
                "price": price,
                "liquidity": float(pool["liquidity"]) if "liquidity" in pool else 0,
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time())
            })
    
    except Exception as e:
        logger.error(f"Uniswapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_sushiswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    SushiSwapのレスポンスをパース (クライアント側フィルタリング版)
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル (フィルタリングに使用)
        quote_token: クオートトークンのシンボル (フィルタリングに使用)
        
    Returns:
        List[Dict[str, Any]]: パース済みプールデータのリスト
    """
    results = []
    
    try:
        # エラーチェック
        if "errors" in response:
            logger.error(f"SushiSwapクエリにエラーがあります: {response['errors']}")
            return results
            
        pairs = response.get("data", {}).get("pairs", [])
        logger.debug(f"SushiSwap: 合計 {len(pairs)} ペアを取得しました")
        
        # クライアントサイドでのフィルタリング
        filtered_pairs = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pair in pairs:
            token0_symbol = pair["token0"]["symbol"].upper()
            token1_symbol = pair["token1"]["symbol"].upper()
            
            # 指定したトークンペアに一致するかチェック (両方向)
            if (token0_symbol == base_upper and token1_symbol == quote_upper) or \
               (token0_symbol == quote_upper and token1_symbol == base_upper):
                filtered_pairs.append(pair)
        
        logger.debug(f"SushiSwap: {base_token}/{quote_token} に一致するペアは {len(filtered_pairs)} 件でした")
        
        # フィルタリングしたペアを処理
        for pair in filtered_pairs:
            token0_symbol = pair["token0"]["symbol"]
            token1_symbol = pair["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_upper:
                price = float(pair["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(pair["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            results.append({
                "pool_id": pair["id"],
                "price": price,
                "liquidity": 0,  # SushiSwapではreserveUSDが利用できないため
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time())
            })
    
    except Exception as e:
        logger.error(f"SushiSwapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_quickswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """QuickSwapのレスポンスをパース"""
    results = []
    
    try:
        pools = response.get("data", {}).get("pools", [])
        
        for pool in pools:
            token0_symbol = pool["token0"]["symbol"]
            token1_symbol = pool["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_token.upper():
                price = float(pool["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(pool["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            results.append({
                "pool_id": pool["id"],
                "price": price,
                "liquidity": float(pool.get("totalValueLockedUSD", 0)),
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time())
            })
    
    except Exception as e:
        logger.error(f"QuickSwapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_balancer_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    Balancerのレスポンスをパース (クライアント側フィルタリング版)
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル (フィルタリングに使用)
        quote_token: クオートトークンのシンボル (フィルタリングに使用)
        
    Returns:
        List[Dict[str, Any]]: パース済みプールデータのリスト
    """
    results = []
    
    try:
        # エラーチェック
        if "errors" in response:
            logger.error(f"Balancerクエリにエラーがあります: {response['errors']}")
            return results
            
        pools = response.get("data", {}).get("pools", [])
        logger.debug(f"Balancer: 合計 {len(pools)} プールを取得しました")
        
        # 指定したトークンペアを含むプールをフィルタリング
        filtered_pools = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pool in pools:
            tokens = pool.get("tokens", [])
            token_symbols = [token.get("symbol", "").upper() for token in tokens]
            
            # 指定したベーストークンとクオートトークンの両方を含むプールのみを選択
            if base_upper in token_symbols and quote_upper in token_symbols:
                filtered_pools.append(pool)
        
        logger.debug(f"Balancer: {base_token}/{quote_token} を含むプールは {len(filtered_pools)} 件でした")
        
        # フィルタリングしたプールを処理
        for pool in filtered_pools:
            tokens = pool.get("tokens", [])
            
            # ベーストークンとクオートトークンを探す
            base_token_data = None
            quote_token_data = None
            
            for token in tokens:
                if token["symbol"].upper() == base_upper:
                    base_token_data = token
                elif token["symbol"].upper() == quote_upper:
                    quote_token_data = token
            
            if base_token_data and quote_token_data:
                # weightを使用した価格計算
                try:
                    # 重みがある場合はそれを使用
                    if "weight" in base_token_data and "weight" in quote_token_data:
                        base_weight = float(base_token_data["weight"])
                        quote_weight = float(quote_token_data["weight"])
                        price = quote_weight / base_weight if base_weight > 0 else 0
                    else:
                        # 重みが無い場合は1:1と仮定
                        price = 1.0
                    
                    results.append({
                        "pool_id": pool["id"],
                        "price": price,
                        "liquidity": float(pool.get("totalLiquidity", 0)),
                        "base_token": base_token_data["symbol"],
                        "quote_token": quote_token_data["symbol"],
                        "timestamp": int(time.time())
                    })
                except (ValueError, ZeroDivisionError) as e:
                    logger.error(f"Balancer価格計算エラー: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Balancerレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results
    """Balancerのレスポンスをパース"""
    results = []
    
    try:
        pools = response.get("data", {}).get("pools", [])
        
        for pool in pools:
            tokens = pool.get("tokens", [])
            
            # ベーストークンとクオートトークンを探す
            base_token_data = None
            quote_token_data = None
            
            for token in tokens:
                if token["symbol"].upper() == base_token.upper():
                    base_token_data = token
                elif token["symbol"].upper() == quote_token.upper():
                    quote_token_data = token
            
            if base_token_data and quote_token_data:
                # priceRateとweightを使用した価格計算（新しいスキーマに合わせて）
                try:
                    base_price_rate = float(base_token_data.get("priceRate", 1))
                    quote_price_rate = float(quote_token_data.get("priceRate", 1))
                    
                    # 重みがある場合はそれも考慮
                    if "weight" in base_token_data and "weight" in quote_token_data:
                        base_weight = float(base_token_data["weight"])
                        quote_weight = float(quote_token_data["weight"])
                        price = (base_price_rate * quote_weight) / (quote_price_rate * base_weight)
                    else:
                        price = base_price_rate / quote_price_rate
                    
                    results.append({
                        "pool_id": pool["id"],
                        "price": price,
                        "liquidity": float(pool.get("totalLiquidity", 0)),
                        "base_token": base_token_data["symbol"],
                        "quote_token": quote_token_data["symbol"],
                        "timestamp": int(time.time())
                    })
                except (ValueError, ZeroDivisionError) as e:
                    logger.error(f"Balancer価格計算エラー: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Balancerレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results