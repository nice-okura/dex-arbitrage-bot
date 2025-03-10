import os
from web3 import Web3
from contracts import DEX_ABI  # Uniswap用ABIに更新する必要がある場合はこちらも変更

# Web3の初期化
w3 = Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")))

# Uniswapルーターのアドレス（例: Uniswap V3 Routerのアドレス）
contract_address = "0x7a250d5630B4cf539739dF2C5dAcb4c659F2488D"  # uniswap

# スマートコントラクトのインスタンス化
contract = w3.eth.contract(
    address=w3.to_checksum_address(contract_address), abi=DEX_ABI
)

# テスト関数の呼び出し
try:
    version = contract.functions.version().call()
    print(f"version: {version}")
except Exception as e:
    print(f"Error calling version: {e}")

# トークンスワップのシミュレーション（Uniswap用）
token1 = "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270"  # WMATIC
token2 = "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619"  # WETH
try:
    amount_in = 10**18  # 1 token with 18 decimals
    route = [w3.to_checksum_address(token1), w3.to_checksum_address(token2)]
    # Uniswap V2のシミュレーション用関数 getAmountsOut を使用
    amounts = contract.functions.getAmountsOut(amount_in, route).call()
    print(f"Simulated swap result (output amount): {amounts[-1]}")
except Exception as e:
    print(f"Error simulating token swap: {e}")
