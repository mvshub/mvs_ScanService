#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum

DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_REQUEST_TIMEOUT_MAX = 60

FETCH_MAX_ROW = 1000

SWAP_TOKEN_PREFIX = 'ERC20.'

MAX_SWAP_ASSET_DECIMAL = 8

MIN_FEE_FOR_ETP_DEVELOPER_COMMUNITY = 10**8  # 1 ETP


class TokenType(IntEnum):
    Unknown = -1
    Erc20 = 0
    Erc721 = 1
    Eth = 2

class Status(IntEnum):
    Swap_New = 1
    Swap_Issue = 2
    Swap_Send = 3
    Swap_Finish = 4

    Tx_Unconfirm = 0
    Tx_Confirm = 1

    Token_Normal = 0
    Token_Issue = 1

    Tx_Unchecked = 0
    Tx_Checked = 1
    Tx_Ban = 2

    Connect_Mit_Register = 0
    Connect_MIT_Transfer = 1
    Connect_MIT_Burn = 2

class Error(IntEnum):
    Success = 0
