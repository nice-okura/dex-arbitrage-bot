# src/graphql/queries.py
"""DEX GraphQLクエリを一元管理するモジュール"""

# Uniswap V3のクエリ
UNISWAP_POOL_QUERY = """
query GetUniswapPools($base: String!, $quote: String!, $limit: Int!) {
  pools(
    where: {token0_: {symbol_contains_nocase: $base}, token1_: {symbol_contains_nocase: $quote}}
    orderBy: liquidity
    orderDirection: desc
    first: $limit
  ) {
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
"""

# SushiSwapのクエリ (スキーマ変更後の修正版)
SUSHISWAP_PAIR_QUERY = """
query GetSushiSwapPairs($limit: Int!) {
  pairs(
    orderDirection: desc
    first: $limit
  ) {
    id
    token0Price
    token1Price
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
"""

# QuickSwapのクエリ (スキーマ変更後の修正版)
QUICKSWAP_POOL_QUERY = """
query GetQuickSwapPools($base: String!, $quote: String!, $limit: Int!) {
  pools(
    where: {token0_: {symbol_contains_nocase: $base}, token1_: {symbol_contains_nocase: $quote}}
    orderBy: totalValueLockedUSD
    orderDirection: desc
    first: $limit
  ) {
    id
    token0Price
    token1Price
    totalValueLockedUSD
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
"""

# Balancerのクエリ (スキーマ変更後の修正版)
BALANCER_POOL_QUERY = """
query GetBalancerPools($limit: Int!) {
  pools(
    orderBy: totalLiquidity
    orderDirection: desc
    first: $limit
  ) {
    id
    totalLiquidity
    tokens {
      symbol
      address
      weight
    }
  }
}
"""

# 下記では変数を使わない簡易バージョンを用意
def get_uniswap_query(base: str, quote: str, limit: int = 1) -> str:
    """Uniswap V3のクエリを生成"""
    return f"""
    {{
      pools(where: {{token0_: {{symbol_contains_nocase: "{base}"}}, token1_: {{symbol_contains_nocase: "{quote}"}}}}, orderBy: liquidity, orderDirection: desc, first: {limit}) {{
        id
        token0Price
        token1Price
        liquidity
        token0 {{
          symbol
          id
        }}
        token1 {{
          symbol
          id
        }}
      }}
    }}
    """

def get_sushiswap_query(base: str, quote: str, limit: int = 100) -> str:
    """SushiSwapのクエリを生成 (where句なし、より多くのペアを取得)"""
    # base, quoteはクライアント側でフィルタリングに使用されるため渡されるが、
    # クエリ内では使用しない
    return f"""
    {{
      pairs(orderDirection: desc, first: {limit}) {{
        id
        token0Price
        token1Price
        token0 {{
          symbol
          id
        }}
        token1 {{
          symbol
          id
        }}
      }}
    }}
    """
    
def get_quickswap_query(base: str, quote: str, limit: int = 1) -> str:
    """QuickSwapのクエリを生成"""
    return f"""
    {{
      pools(where: {{token0_: {{symbol_contains_nocase: "{base}"}}, token1_: {{symbol_contains_nocase: "{quote}"}}}}, orderBy: totalValueLockedUSD, orderDirection: desc, first: {limit}) {{
        id
        token0Price
        token1Price
        totalValueLockedUSD
        token0 {{
          symbol
          id
        }}
        token1 {{
          symbol
          id
        }}
      }}
    }}
    """

def get_balancer_query(base: str, quote: str, limit: int = 100) -> str:
    """Balancerのクエリを生成 (where句なし、より多くのプールを取得)"""
    # base, quoteはクライアント側でフィルタリングに使用されるため渡されるが、
    # クエリ内では使用しない
    return f"""
    {{
      pools(orderBy: totalLiquidity, orderDirection: desc, first: {limit}) {{
        id
        totalLiquidity
        tokens {{
          symbol
          address
          weight
        }}
      }}
    }}
    """