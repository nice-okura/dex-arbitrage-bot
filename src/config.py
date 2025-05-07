# src/config.py（更新版）
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

class TokenPair:
    def __init__(self, base: str, quote: str):
        self.base = base    # 基準となる通貨 (例: MATIC)
        self.quote = quote  # 相手通貨 (例: USDT)
        
    def __str__(self):
        return f"{self.base}/{self.quote}"
    
    def as_tuple(self):
        return (self.base, self.quote)
    
    def for_dex(self, dex_name):
        """DEX用のペア表記を返す"""
        if dex_name == "uniswap_v3" or dex_name == "quickswap" or dex_name == "sushiswap":
            return f"{self.base}-{self.quote}"
        elif dex_name == "curve":
            return f"{self.base.lower()}{self.quote.lower()}"
        elif dex_name == "balancer":
            return f"{self.base}-{self.quote}"
        return f"{self.base}-{self.quote}"
    
    def for_cex(self, cex_name):
        """CEX用のペア表記を返す"""
        if cex_name == "bitbank":
            return f"{self.base.lower()}_{self.quote.lower()}"
        elif cex_name == "bitflyer":
            return f"{self.base}_{self.quote}"
        elif cex_name == "coincheck":
            return f"{self.base.lower()}_{self.quote.lower()}"
        elif cex_name == "zaif":
            return f"{self.base.lower()}_{self.quote.lower()}"
        elif cex_name == "bittrade":
            return f"{self.base.lower()}{self.quote.lower()}"
        return f"{self.base}{self.quote}"

class DEXConfig:
    def __init__(self, name: str, api_url: str, fee_percent: float, subgraph_id: Optional[str] = None):
        self.name = name
        self.api_url = api_url
        self.fee_percent = fee_percent
        self.subgraph_id = subgraph_id

class CEXConfig:
    def __init__(self, name: str, api_url: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.name = name
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret

class AppConfig:
    def __init__(self):
        # 基本設定
        self.price_update_interval = int(os.getenv("PRICE_UPDATE_INTERVAL", "5"))  # 秒
        self.arbitrage_threshold = float(os.getenv("ARBITRAGE_THRESHOLD", "0.5"))  # %
        self.slippage_tolerance = float(os.getenv("SLIPPAGE_TOLERANCE", "0.3"))    # %
        self.min_profit_usd = float(os.getenv("MIN_PROFIT_USD", "5.0"))           # USD
        self.notification_cooldown = int(os.getenv("NOTIFICATION_COOLDOWN", "300"))  # 秒 (5分)
        
        # The Graph API Key
        self.graph_api_key = os.getenv("GRAPH_API_KEY", "")
        
        # Redis設定
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        
        # Slack通知設定
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        
        # 監視対象の通貨ペア
        self.token_pairs = self._load_token_pairs()
        
        # 監視対象のDEX
        self.dexes = self._load_dexes()
        
        # 監視対象のCEX
        self.cexes = self._load_cexes()
    
    def _load_token_pairs(self) -> List[TokenPair]:
        # 環境変数またはデフォルト値から通貨ペアを読み込む
        pairs_env = os.getenv("TOKEN_PAIRS", "BTC/JPY,ETH/JPY,XRP/JPY,MATIC/USDT,ETH/BTC")
        pairs = []
        
        for pair_str in pairs_env.split(","):
            if "/" in pair_str:
                base, quote = pair_str.strip().split("/")
                pairs.append(TokenPair(base.strip(), quote.strip()))
        
        return pairs
    
    def _load_dexes(self) -> Dict[str, DEXConfig]:
        # The Graph Gateway URL（API Keyがある場合）
        graph_base_url = "https://gateway.thegraph.com/api"
        
        # GraphQLエンドポイントを構築
        def build_graph_url(subgraph_id):
            if self.graph_api_key:
                return f"{graph_base_url}/{self.graph_api_key}/subgraphs/id/{subgraph_id}"
            else:
                # APIキーがない場合は警告を出力
                import logging
                logging.warning("GRAPH_API_KEY環境変数が設定されていません。The Graph APIへのアクセスが制限される可能性があります。")
                return f"{graph_base_url}/[API-KEY-REQUIRED]/subgraphs/id/{subgraph_id}"
        
        # 各DEXのサブグラフID
        uniswap_subgraph_id = os.getenv("UNISWAP_SUBGRAPH_ID", "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV") 
        sushiswap_subgraph_id = os.getenv("SUSHISWAP_SUBGRAPH_ID", "CKaCne3uUUEqT7Ei9jjZbQqTLntEno9LnFa4JnsqqBma")
        quickswap_subgraph_id = os.getenv("QUICKSWAP_SUBGRAPH_ID", "FqsRcH1XqSjqVx9GRTvEJe959aCbKrcyGgDWBrUkG24g")
        balancer_subgraph_id = os.getenv("BALANCER_SUBGRAPH_ID", "H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp")
        
        # 主要なDEXの設定を返す
        return {
            "uniswap_v3": DEXConfig(
                name="Uniswap V3",
                api_url=build_graph_url(uniswap_subgraph_id),
                fee_percent=0.3,  # 基本手数料
                subgraph_id=uniswap_subgraph_id
            ),
            "quickswap": DEXConfig(
                name="QuickSwap",
                api_url=build_graph_url(quickswap_subgraph_id),
                fee_percent=0.3,
                subgraph_id=quickswap_subgraph_id
            ),
            "sushiswap": DEXConfig(
                name="SushiSwap",
                api_url=build_graph_url(sushiswap_subgraph_id),
                fee_percent=0.3,
                subgraph_id=sushiswap_subgraph_id
            ),
            "curve": DEXConfig(
                name="Curve",
                api_url="https://api.curve.fi/api/getPools/polygon/main",
                fee_percent=0.04,
                subgraph_id=None  # CurveはGraphQLを使用しない
            ),
            "balancer": DEXConfig(
                name="Balancer",
                api_url=build_graph_url(balancer_subgraph_id),
                fee_percent=0.2,
                subgraph_id=balancer_subgraph_id
            )
        }
    
    def _load_cexes(self) -> Dict[str, CEXConfig]:
        # 主要なCEXの設定を返す
        return {
            "bitbank": CEXConfig(
                name="Bitbank",
                api_url="https://public.bitbank.cc",
                api_key=os.getenv("BITBANK_API_KEY", ""),
                api_secret=os.getenv("BITBANK_API_SECRET", "")
            ),
            "bitflyer": CEXConfig(
                name="BitFlyer",
                api_url="https://api.bitflyer.com/v1",
                api_key=os.getenv("BITFLYER_API_KEY", ""),
                api_secret=os.getenv("BITFLYER_API_SECRET", "")
            ),
            "coincheck": CEXConfig(
                name="Coincheck",
                api_url="https://coincheck.com/api",
                api_key=os.getenv("COINCHECK_API_KEY", ""),
                api_secret=os.getenv("COINCHECK_API_SECRET", "")
            ),
            "zaif": CEXConfig(
                name="Zaif",
                api_url="https://api.zaif.jp/api/1",
                api_key=os.getenv("ZAIF_API_KEY", ""),
                api_secret=os.getenv("ZAIF_API_SECRET", "")
            ),
            "bittrade": CEXConfig(
                name="BitTrade",
                api_url="https://api.bittrade.co.jp/v1",
                api_key=os.getenv("BITTRADE_API_KEY", ""),
                api_secret=os.getenv("BITTRADE_API_SECRET", "")
            )
        }