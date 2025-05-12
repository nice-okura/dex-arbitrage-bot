# src/graphql/parsers.py
"""GraphQLレスポンスのパーサモジュール"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("dex_arbitrage_bot.graphql_parsers")

def parse_uniswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    Uniswap V3のレスポンスをパースし、最も流動性の高いプールのみを返す
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル
        quote_token: クオートトークンのシンボル
        
    Returns:
        List[Dict[str, Any]]: 最も推奨されるプールのみを含むリスト (空のリストの場合もある)
    """
    results = []
    
    try:
        # エラーチェック
        if "errors" in response:
            logger.error(f"Uniswapクエリにエラーがあります: {response['errors']}")
            return results
            
        pools = response.get("data", {}).get("pools", [])
        
        # 適切なプールをフィルタリング
        valid_pools = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pool in pools:
            token0_symbol = pool["token0"]["symbol"].upper()
            token1_symbol = pool["token1"]["symbol"].upper()
            
            # 両方のトークンが正確に一致するか確認（部分一致ではなく完全一致）
            if (token0_symbol == base_upper and token1_symbol == quote_upper) or \
               (token0_symbol == quote_upper and token1_symbol == base_upper):
                
                # 流動性を数値として取得
                liquidity = float(pool["liquidity"]) if "liquidity" in pool else 0
                
                # 流動性が0でないプールのみを考慮
                if liquidity > 0:
                    valid_pools.append(pool)
        
        # 流動性でソート（降順）
        valid_pools.sort(key=lambda p: float(p["liquidity"]) if "liquidity" in p else 0, reverse=True)
        
        # 最も流動性の高いプールのみを処理（存在する場合）
        if valid_pools:
            top_pool = valid_pools[0]
            token0_symbol = top_pool["token0"]["symbol"]
            token1_symbol = top_pool["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_upper:
                price = float(top_pool["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(top_pool["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            results.append({
                "pool_id": top_pool["id"],
                "price": price,
                "liquidity": float(top_pool["liquidity"]) if "liquidity" in top_pool else 0,
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time()),
                "selected_from": len(pools),
                "valid_pools": len(valid_pools)
            })
            
            logger.debug(f"Uniswap: {len(pools)}プール中、{len(valid_pools)}個の有効なプールから最適なプール（流動性: {results[0]['liquidity']}）を選択しました")
        else:
            logger.debug(f"Uniswap: {base_token}/{quote_token}に対して適切なプールが見つかりませんでした（全{len(pools)}プール）")
    
    except Exception as e:
        logger.error(f"Uniswapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_sushiswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    SushiSwapのレスポンスをパースし、最も適切なペアのみを返す
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル (フィルタリングに使用)
        quote_token: クオートトークンのシンボル (フィルタリングに使用)
        
    Returns:
        List[Dict[str, Any]]: 最も推奨されるペアのみを含むリスト
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
        valid_pairs = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pair in pairs:
            token0_symbol = pair["token0"]["symbol"].upper()
            token1_symbol = pair["token1"]["symbol"].upper()
            
            # 指定したトークンペアに完全一致するかチェック (両方向)
            if (token0_symbol == base_upper and token1_symbol == quote_upper) or \
               (token0_symbol == quote_upper and token1_symbol == base_upper):
                
                # 価格が正常かチェック
                price0 = float(pair.get("token0Price", 0))
                price1 = float(pair.get("token1Price", 0))
                
                if price0 > 0 and price1 > 0:
                    valid_pairs.append(pair)
        
        # 一般的には流動性（reserveUSD）でソートするが、SushiSwapでは利用できない場合がある
        # 有効なペアがあれば、最初のペアを使用（通常、APIから返される順序は流動性順）
        if valid_pairs:
            top_pair = valid_pairs[0]
            token0_symbol = top_pair["token0"]["symbol"]
            token1_symbol = top_pair["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_upper:
                price = float(top_pair["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(top_pair["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            # reserveUSDがない場合は0を設定
            liquidity = 0  
            try:
                liquidity = float(top_pair.get("reserveUSD", 0))
            except (ValueError, TypeError):
                pass
            
            results.append({
                "pool_id": top_pair["id"],
                "price": price,
                "liquidity": liquidity,
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time()),
                "selected_from": len(pairs),
                "valid_pairs": len(valid_pairs)
            })
            
            logger.debug(f"SushiSwap: {len(pairs)}ペア中、{len(valid_pairs)}個の有効なペアから最適なペアを選択しました")
        else:
            logger.debug(f"SushiSwap: {base_token}/{quote_token}に対して適切なペアが見つかりませんでした（全{len(pairs)}ペア）")
    
    except Exception as e:
        logger.error(f"SushiSwapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_quickswap_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    QuickSwapのレスポンスをパースし、最も流動性の高いプールのみを返す
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル
        quote_token: クオートトークンのシンボル
        
    Returns:
        List[Dict[str, Any]]: 最も推奨されるプールのみを含むリスト
    """
    results = []
    
    try:
        # エラーチェック
        if "errors" in response:
            logger.error(f"QuickSwapクエリにエラーがあります: {response['errors']}")
            return results
            
        pools = response.get("data", {}).get("pools", [])
        
        # 適切なプールをフィルタリング
        valid_pools = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pool in pools:
            token0_symbol = pool["token0"]["symbol"].upper()
            token1_symbol = pool["token1"]["symbol"].upper()
            
            # 両方のトークンが正確に一致するか確認
            if (token0_symbol == base_upper and token1_symbol == quote_upper) or \
               (token0_symbol == quote_upper and token1_symbol == base_upper):
                
                # totalValueLockedUSDを取得
                liquidity = 0
                try:
                    liquidity = float(pool.get("totalValueLockedUSD", 0))
                except (ValueError, TypeError):
                    pass
                
                # 価格が正常かチェック
                price0 = float(pool.get("token0Price", 0))
                price1 = float(pool.get("token1Price", 0))
                
                if price0 > 0 and price1 > 0:
                    valid_pools.append(pool)
        
        # 流動性でソート（降順）
        valid_pools.sort(key=lambda p: float(p.get("totalValueLockedUSD", 0)), reverse=True)
        
        # 最も流動性の高いプールのみを処理（存在する場合）
        if valid_pools:
            top_pool = valid_pools[0]
            token0_symbol = top_pool["token0"]["symbol"]
            token1_symbol = top_pool["token1"]["symbol"]
            
            # 正しい方向の価格を選択
            if token0_symbol.upper() == base_upper:
                price = float(top_pool["token1Price"])
                base = token0_symbol
                quote = token1_symbol
            else:
                price = float(top_pool["token0Price"])
                base = token1_symbol
                quote = token0_symbol
            
            # 流動性を取得
            liquidity = 0
            try:
                liquidity = float(top_pool.get("totalValueLockedUSD", 0))
            except (ValueError, TypeError):
                pass
            
            results.append({
                "pool_id": top_pool["id"],
                "price": price,
                "liquidity": liquidity,
                "base_token": base,
                "quote_token": quote,
                "timestamp": int(time.time()),
                "selected_from": len(pools),
                "valid_pools": len(valid_pools)
            })
            
            logger.debug(f"QuickSwap: {len(pools)}プール中、{len(valid_pools)}個の有効なプールから最適なプール（流動性: {liquidity}）を選択しました")
        else:
            logger.debug(f"QuickSwap: {base_token}/{quote_token}に対して適切なプールが見つかりませんでした（全{len(pools)}プール）")
    
    except Exception as e:
        logger.error(f"QuickSwapレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results

def parse_balancer_response(response: Dict[str, Any], base_token: str, quote_token: str) -> List[Dict[str, Any]]:
    """
    Balancerのレスポンスをパースし、最も流動性の高いプールのみを返す
    
    Args:
        response: GraphQLレスポンスデータ
        base_token: ベーストークンのシンボル
        quote_token: クオートトークンのシンボル
        
    Returns:
        List[Dict[str, Any]]: 最も推奨されるプールのみを含むリスト
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
        valid_pools = []
        base_upper = base_token.upper()
        quote_upper = quote_token.upper()
        
        for pool in pools:
            tokens = pool.get("tokens", [])
            token_symbols = [token.get("symbol", "").upper() for token in tokens]
            
            # 指定したベーストークンとクオートトークンの両方を含むプールのみを選択
            if base_upper in token_symbols and quote_upper in token_symbols:
                # 流動性を取得
                liquidity = 0
                try:
                    liquidity = float(pool.get("totalLiquidity", 0))
                except (ValueError, TypeError):
                    pass
                
                # 流動性が0より大きいプールのみを追加
                if liquidity > 0:
                    valid_pools.append(pool)
        
        # 流動性でソート（降順）
        valid_pools.sort(key=lambda p: float(p.get("totalLiquidity", 0)), reverse=True)
        
        # 最も流動性の高いプールのみを処理（存在する場合）
        if valid_pools:
            top_pool = valid_pools[0]
            tokens = top_pool.get("tokens", [])
            
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
                    
                    # 流動性を取得
                    liquidity = 0
                    try:
                        liquidity = float(top_pool.get("totalLiquidity", 0))
                    except (ValueError, TypeError):
                        pass
                    
                    # 価格が正常な場合のみ追加
                    if price > 0:
                        results.append({
                            "pool_id": top_pool["id"],
                            "price": price,
                            "liquidity": liquidity,
                            "base_token": base_token_data["symbol"],
                            "quote_token": quote_token_data["symbol"],
                            "timestamp": int(time.time()),
                            "selected_from": len(pools),
                            "valid_pools": len(valid_pools)
                        })
                        
                        logger.debug(f"Balancer: {len(pools)}プール中、{len(valid_pools)}個の有効なプールから最適なプール（流動性: {liquidity}）を選択しました")
                    else:
                        logger.debug(f"Balancer: 計算された価格が無効です: {price}")
                
                except (ValueError, ZeroDivisionError) as e:
                    logger.error(f"Balancer価格計算エラー: {e}", exc_info=True)
            else:
                logger.debug(f"Balancer: トークンデータが取得できませんでした")
        else:
            logger.debug(f"Balancer: {base_token}/{quote_token}に対して適切なプールが見つかりませんでした（全{len(pools)}プール）")
    
    except Exception as e:
        logger.error(f"Balancerレスポンスのパース中にエラー: {e}", exc_info=True)
    
    return results