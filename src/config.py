# src/config.py
import os
from typing import Dict, List, Optional

class TokenPair:
    def __init__(self, base: str, quote: str):
        self.base = base    # 基準となる通貨 (例: MATIC)
        self.quote = quote  # 相手通貨 (例: USDT)
        
    def __str__(self):
        return f"{self.base}/{self.quote}"
    
    def as_tuple(self):
        return (self.base, self.quote)

class DEXConfig:
    def __init__(self, name: str, address: str, fee_percent: float):
        self.name = name
        self.address = address
        self.fee_percent = fee_percent

class CEXConfig:
    def __init__(self, name: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.name = name
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
        
        # Redis設定
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        
        # Slack通知設定
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        
        # PolygonScan API設定
        self.polygonscan_api_key = os.getenv("POLYGONSCAN_API_KEY", "")
        
        # The Graph API設定
        self.graph_api_key = os.getenv("GRAPH_API_KEY", "")
        
        # 監視対象の通貨ペア
        self.token_pairs = self._load_token_pairs()
        
        # 監視対象のDEX
        self.dexes = self._load_dexes()
        
        # 監視対象のCEX
        self.cexes = self._load_cexes()
        
        # トークンアドレス (Polygon)
        self.token_addresses = {
            "MATIC": "0x0000000000000000000000000000000000001010",
            "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
            "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
            "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6"
        }
    
    def _load_token_pairs(self) -> List[TokenPair]:
        # 環境変数またはデフォルト値から通貨ペアを読み込む
        pairs_env = os.getenv("TOKEN_PAIRS", "MATIC/USDT,USDC/DAI,WETH/USDT,WBTC/USDT")
        pairs = []
        
        for pair_str in pairs_env.split(","):
            if "/" in pair_str:
                base, quote = pair_str.strip().split("/")
                pairs.append(TokenPair(base.strip(), quote.strip()))
        
        return pairs
    
    def _load_dexes(self) -> Dict[str, DEXConfig]:
        # 主要なDEXの設定を返す
        return {
            "quickswap": DEXConfig(
                name="Quickswap",
                address="0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",  # QuickSwap Router
                fee_percent=0.3
            ),
            "sushiswap": DEXConfig(
                name="SushiSwap",
                address="0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",  # SushiSwap Router
                fee_percent=0.3
            ),
            "uniswap_v3": DEXConfig(
                name="Uniswap V3",
                address="0xE592427A0AEce92De3Edee1F18E0157C05861564",  # Uniswap V3 Router
                fee_percent=0.3  # 実際にはプールによって異なる
            ),
            "curve": DEXConfig(
                name="Curve",
                address="0x8474DdbE98F5aA3179B3B3F5942D724aFcdec9f6",  # Curve Router
                fee_percent=0.04  # 実際にはプールによって異なる
            )
        }
    
    def _load_cexes(self) -> Dict[str, CEXConfig]:
        # 主要なCEXの設定を返す
        return {
            "binance": CEXConfig(
                name="Binance",
                api_key=os.getenv("BINANCE_API_KEY", ""),
                api_secret=os.getenv("BINANCE_API_SECRET", "")
            ),
            "coinbase": CEXConfig(
                name="Coinbase",
                api_key=os.getenv("COINBASE_API_KEY", ""),
                api_secret=os.getenv("COINBASE_API_SECRET", "")
            )
        }