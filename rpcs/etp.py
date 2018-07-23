from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import logging


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETP'

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        req_body = {
            'id': self.rpc_id,
            'jsonrpc': self.rpc_version,
            'method': method,
            "params": params}
        res = requests.post(
            self.settings['uri'], json.dumps(req_body), timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
            if isinstance(js, dict) and js.get('error') is not None:
                raise RpcException(js['error'])
            return js
        except ValueError as e:
            pass
        return res.text

    def get_balance(self, address):
        res = self.make_request('getaddressetp', [address])
        return res[result]['unspent']

    def get_block_by_height(self, height):
        res = self.make_request('getblockheader', ['-t', int(height)])
        block_hash = res['result']['hash']
        res = self.make_request('getblock', [block_hash, 'true'])
        timestamp = res['result']['timestamp']
        transactions = res['result']['transactions']
        txs = []
        for i, tx in enumerate(transactions):
            input_addresses = [input_['address'] for input_ in tx[
                'inputs'] if input_.get('address') is not None]
            for j, output in enumerate(tx['outputs']):
                output['to'] = '' if output.get(
                    'address') is None else output['address']
                output['blockNumber'] = height
                output['value'] = int(output['value'])
                output['type'] = 'ETP'
                output['hash'] = tx['hash']
                output['index'] = i
                output['output_index'] = j
                output['time'] = int(timestamp)
                output['input_addresses'] = input_addresses
                txs.append(output)
                if output['attachment']['type'] == 'asset-transfer':
                    import copy
                    o = copy.copy(output)
                    o['type'] = output['attachment']['symbol']
                    o['value'] = int(output['attachment']['quantity'])
                    txs.append(o)

        res['txs'] = txs
        return res

    def is_deposit(self, tx, addresses):
        if tx['type'] != self.name:
            return False
        if tx['value'] <= 0:
            return False

        if set(tx['input_addresses']).intersection(set(addresses)):
            return False
        if tx['script'].find('numequalverify') < 0 and tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('gettransaction', [txid])
        return res['result']

    def new_address(self, account, passphase):
        res = self.make_request('getnewaddress', [account, passphase])
        addresses = res['result']
        if addresses is not None and len(addresses) > 0:
            return addresses[0]
        return None

    def best_block_number(self):
        res = self.make_request('getheight')
        return res['result']

    def to_wei(self, ether):
        return int(decimal.Decimal(ether) * decimal.Decimal(10.0**8))
        # return long(ether * 10.0**18)

    def from_wei(self, wei):
        return wei / decimal.Decimal(10.0**8)
