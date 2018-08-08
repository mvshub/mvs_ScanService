#!/usr/bin/env python
#! encoding=utf-8

from enum import IntEnum


FETCH_MAX_ROW = 1000

MAX_ERC_2_ETP_DECIMAL = 9

SWAP_TOKEN_PREFIX = 'ERCT1.'

class Status(IntEnum):
    Swap_New = 1
    Swap_Issue = 2
    Swap_Send = 3
    Swap_Finish = 4

    Tx_Unconfirm = 0
    Tx_Confirm = 1

    Token_Normal = 0
    Token_Issue = 1


class Error(IntEnum):
    Success = 0
