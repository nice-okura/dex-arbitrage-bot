# src/graphql/__init__.py
"""GraphQL関連モジュール"""

from .queries import (
    get_uniswap_query,
    get_sushiswap_query, 
    get_quickswap_query,
    get_balancer_query,
    UNISWAP_POOL_QUERY,
    SUSHISWAP_PAIR_QUERY,
    QUICKSWAP_POOL_QUERY,
    BALANCER_POOL_QUERY
)

from .client import GraphQLClient
from .parsers import (
    parse_uniswap_response,
    parse_sushiswap_response,
    parse_quickswap_response,
    parse_balancer_response
)

__all__ = [
    'GraphQLClient',
    'get_uniswap_query',
    'get_sushiswap_query',
    'get_quickswap_query',
    'get_balancer_query',
    'UNISWAP_POOL_QUERY',
    'SUSHISWAP_PAIR_QUERY',
    'QUICKSWAP_POOL_QUERY',
    'BALANCER_POOL_QUERY',
    'parse_uniswap_response',
    'parse_sushiswap_response',
    'parse_quickswap_response',
    'parse_balancer_response'
]