from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import logging
from modles import db
from modles.deposit import Deposit
from modles.address import Address
from sqlalchemy import func
import time


class Xrb(Base):
    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'XRB'
        self.wallet = settings.get('wallet')

    def start(self):
        assert (self.wallet is not None)
        self.get_accounts()
        return True

    def stop(self):
        return False

    def get_accounts(self):
        res = self.make_request('account_list', {'wallet': self.wallet})
        return res

    def account_block_count(self, address):
        res = self.make_request('account_block_count', {'account': address})
        return res['block_count']

    def account_info(self, address):
        res = self.make_request('account_info', {'account': address})
        return res

    def make_request(self, method, params={}):
        params['action'] = method
        data = params
        res = requests.post(self.settings['uri'], json.dumps(data), headers={'Content-Type': 'application/json'},
                            timeout=25)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            raise RpcException('bad response content, failed to parse,%s' % res.text)
        if js.get('error') is not None:
            raise RpcException('%s' % js['error'])
        return js

    def get_balance(self, address):
        res = self.make_request('account_balance', {'account': address})
        return res['balance']

    def get_block_by_height(self, height):
        ids = db.session.query(func.max(Deposit.iden)).group_by(Deposit.address).filter_by(asset=self.name).all()
        ids = [i[0] for i in ids]
        if ids:
            address_besthashes = db.session.query(Deposit.address, Deposit.tx_hash).filter(
                Deposit.iden.in_(ids)).filter_by(asset=self.name).all();
        else:
            address_besthashes = {}
        address_besthashes = {ab[0]: ab[1] for ab in address_besthashes}
        addresses = [addr.display for addr in Address.query.filter_by(asset=self.name, inuse=1).all()]
        block = {}
        txs = []
        res = {}
        for addr in addresses:
            if addr in address_besthashes:
                continue
            address_besthashes[addr] = None
        for addr, besthash in address_besthashes.items():
            try:
                res = self.account_info(addr)
            except Exception as e:
                continue
            if (res['frontier'] == besthash):
                continue
            hs = self.account_history(addr, res['frontier'], besthash)['history']
            hs = hs[::-1]
            txs.extend([{'to': addr, 'amount': h['amount'], 'hash': h['hash'], 'value': h['amount'], 'blockNumber': 9999,
                         'index': 0, 'time': int(time.time())} for h in hs if h['type'] == 'receive'])
        block['txs'] = txs
        return block

    def account_history(self, address, frontier, stop=None):
        count = 1
        while True:
            if frontier == stop:
                break
            res = self.make_request('chain', {'block': frontier, 'count': 2})
            if not res['blocks']:
                break
            if frontier == res['blocks'][-1]:
                break
            frontier = res['blocks'][-1]
            if frontier == stop:
                break
            count += 1
            logging.info('count,%s,%s' % (count, frontier))
        res = self.make_request('account_history', {'account': address, 'count': count})
        return res

    def is_deposit(self, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('block', {'hash': txid})
        res['blockNumber'] = 9999999999999
        res['to'] = '' if res.get('to') is None else res['to']
        return res

    def new_address(self, account, passphase):
        res = self.make_request('account_create', {'wallet': self.wallet})
        return res['account']

    def transfer(self, passphrase, from_, to_, amount):
        return

    def best_block_number(self):
        return 9999999999999

    def is_address_valid(self, address):
        res = self.make_request('validate_account_number', {'account': address})
        return res['valid']

    def is_address_existed(self, address):
        res = self.make('wallet_contains', {'wallet': self.wallet, 'account': address})
        return res['exists']

    def to_wei(self, ether):
        return long(decimal.Decimal(str(ether)) * decimal.Decimal(str(10.0 ** 30)))

    def from_wei(self, wei):
        return decimal.Decimal(str(wei)) / decimal.Decimal(str(10.0 ** 30))
