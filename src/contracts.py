# src/contracts.py
import json
import os
from web3 import Web3

# ERC20トークンのABI（必要な関数のみ）
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

# DEX Router用のABI（必要な関数のみ）
# DEX_ABI = [
#     {
#         "inputs": [
#             {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
#             {"internalType": "address[]", "name": "path", "type": "address[]"}
#         ],
#         "name": "getAmountsOut",
#         "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
#         "stateMutability": "view",
#         "type": "function"
#     },
#     {
#         "inputs": [
#             {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
#             {"internalType": "address[]", "name": "path", "type": "address[]"}
#         ],
#         "name": "getAmountsIn",
#         "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
#         "stateMutability": "view",
#         "type": "function"
#     }
# ]

DEX_ABI = [
    {
        "name": "Exchange",
        "inputs": [
            {"name": "sender", "type": "address", "indexed": "true"},
            {"name": "receiver", "type": "address", "indexed": "true"},
            {"name": "route", "type": "address[11]", "indexed": "false"},
            {"name": "swap_params", "type": "uint256[5][5]", "indexed": "false"},
            {"name": "pools", "type": "address[5]", "indexed": "false"},
            {"name": "in_amount", "type": "uint256", "indexed": "false"},
            {"name": "out_amount", "type": "uint256", "indexed": "false"},
        ],
        "anonymous": "false",
        "type": "event",
    },
    {"stateMutability": "payable", "type": "fallback"},
    {
        "stateMutability": "nonpayable",
        "type": "constructor",
        "inputs": [
            {"name": "_weth", "type": "address"},
            {"name": "_stable_calc", "type": "address"},
            {"name": "_crypto_calc", "type": "address"},
            {"name": "_tricrypto_meta_pools", "type": "address[2]"},
        ],
        "outputs": [],
    },
    {
        "stateMutability": "payable",
        "type": "function",
        "name": "exchange",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_min_dy", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "payable",
        "type": "function",
        "name": "exchange",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_min_dy", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "payable",
        "type": "function",
        "name": "exchange",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_min_dy", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
            {"name": "_receiver", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dy",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dy",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dx",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_out_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dx",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_out_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
            {"name": "_base_pools", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dx",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_out_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
            {"name": "_base_pools", "type": "address[5]"},
            {"name": "_base_tokens", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dx",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_out_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
            {"name": "_base_pools", "type": "address[5]"},
            {"name": "_base_tokens", "type": "address[5]"},
            {"name": "_second_base_pools", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_dx",
        "inputs": [
            {"name": "_route", "type": "address[11]"},
            {"name": "_swap_params", "type": "uint256[5][5]"},
            {"name": "_out_amount", "type": "uint256"},
            {"name": "_pools", "type": "address[5]"},
            {"name": "_base_pools", "type": "address[5]"},
            {"name": "_base_tokens", "type": "address[5]"},
            {"name": "_second_base_pools", "type": "address[5]"},
            {"name": "_second_base_tokens", "type": "address[5]"},
        ],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "version",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
    },
]

UNISWAP_V3_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_factory", "type": "address"},
            {"internalType": "address", "name": "_WETH9", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {
        "inputs": [],
        "name": "WETH9",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "amountOutMinimum",
                        "type": "uint256",
                    },
                ],
                "internalType": "struct ISwapRouter.ExactInputParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInput",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "amountOutMinimum",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint160",
                        "name": "sqrtPriceLimitX96",
                        "type": "uint160",
                    },
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "amountInMaximum",
                        "type": "uint256",
                    },
                ],
                "internalType": "struct ISwapRouter.ExactOutputParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactOutput",
        "outputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                    {
                        "internalType": "uint256",
                        "name": "amountInMaximum",
                        "type": "uint256",
                    },
                    {
                        "internalType": "uint160",
                        "name": "sqrtPriceLimitX96",
                        "type": "uint160",
                    },
                ],
                "internalType": "struct ISwapRouter.ExactOutputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactOutputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "factory",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "refundETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"},
        ],
        "name": "selfPermit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "nonce", "type": "uint256"},
            {"internalType": "uint256", "name": "expiry", "type": "uint256"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"},
        ],
        "name": "selfPermitAllowed",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "nonce", "type": "uint256"},
            {"internalType": "uint256", "name": "expiry", "type": "uint256"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"},
        ],
        "name": "selfPermitAllowedIfNecessary",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"},
        ],
        "name": "selfPermitIfNecessary",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
            {"internalType": "address", "name": "recipient", "type": "address"},
        ],
        "name": "sweepToken",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "feeBips", "type": "uint256"},
            {"internalType": "address", "name": "feeRecipient", "type": "address"},
        ],
        "name": "sweepTokenWithFee",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "int256", "name": "amount0Delta", "type": "int256"},
            {"internalType": "int256", "name": "amount1Delta", "type": "int256"},
            {"internalType": "bytes", "name": "_data", "type": "bytes"},
        ],
        "name": "uniswapV3SwapCallback",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
            {"internalType": "address", "name": "recipient", "type": "address"},
        ],
        "name": "unwrapWETH9",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "feeBips", "type": "uint256"},
            {"internalType": "address", "name": "feeRecipient", "type": "address"},
        ],
        "name": "unwrapWETH9WithFee",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {"stateMutability": "payable", "type": "receive"},
]


def get_w3():
    """Web3インスタンスを取得する"""
    rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
    return Web3(Web3.HTTPProvider(rpc_url))


def get_erc20_contract(token_address):
    """ERC20トークンコントラクトのインスタンスを取得する"""
    w3 = get_w3()
    return w3.eth.contract(address=w3.to_checksum_address(token_address), abi=ERC20_ABI)


def get_dex_contract(router_address):
    """DEX Routerコントラクトのインスタンスを取得する"""
    w3 = get_w3()
    return w3.eth.contract(address=w3.to_checksum_address(router_address), abi=DEX_ABI)
