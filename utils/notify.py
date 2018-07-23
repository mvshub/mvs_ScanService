import requests
import json
import logging
from utils.decimal_encoder import DecimalEncoder
from utils.exception import DepositNotifyException, WithdrawNotifyException


def notify_withdraw(w, feedback):
    data = {
        'withdraw_id':w.withdraw_id,
        'asset':w.asset,
        'status':0
    }
    res = requests.post(feedback, data=json.dumps(data, cls = DecimalEncoder), headers={'Content-Type':'application/json'}, timeout=5)
    if res.status_code != 200:
        raise WithdrawNotifyException('withdraw deposit failed,%s' % res.status_code)


def notify_deposit(d, best_block_height, feedback):
    data = {
        'deposit_id':d.iden,
        'asset':d.asset,
        'to_address':d.address,
        'txid':d.tx_hash,
        'height':d.block_height,
        'amount':d.amount,
        'chain_height':best_block_height
    }
    logging.info('notify deposit,%s' % data)
    from utils.crypto import sign_data, encrypt
    import os
    data = json.dumps(data, cls = DecimalEncoder)
    sign=""
    # sign = sign_data(os.environ['privkey'], data)
    # data = encrypt(os.environ['pubkey'], data)
    res = requests.post(feedback, data=data, headers={'Content-Type':'text/plain', 'signature':sign}, timeout=5)
    if res.status_code != 200:
        raise DepositNotifyException('notify deposit exception,%s,%s' % (res.status_code, res.text))