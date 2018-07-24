from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import logging

class Eth(Base):
    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETH' if settings.get('name') is None else settings['name']

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        data = {"jsonrpc":"2.0","method":method,"params":params,"id":83}
        res = requests.post('http://%s:%s' % (self.settings['host'], self.settings['port']), json.dumps(data), headers = {'Content-Type':'application/json'}, timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            raise RpcException('bad response content, failed to parse,%s' % res.text)
        if js.get('error') is not None:
            raise RpcException('%s' % js['error']['message'])
        # if js.get('result') is None:
        #     raise RpcException('bad response content, no result found,%s' % js)
        return js['result']

    def get_balance(self, address):
        res = self.make_request('eth_getBalance', [address])
        return int(res, 16)

    def get_block_by_height(self, height):
        logging.info(">>>>>>>>>> ETH : get_block_by_height")
        block = self.make_request('eth_getBlockByNumber', [hex(int(height)), True])
        block['txs'] = block['transactions']
        for i, tx in enumerate(block['txs']):
            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            tx['value'] = int(tx['value'], 16)
            tx['amount'] = tx['value']
            tx['to'] = 'create contract' if tx['to'] is None else tx['to']
        return block

    def is_deposit(self, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res
        res['blockNumber'] = int(res['blockNumber'], 16) if res['blockNumber'] else 0
        res['to'] = '' if res.get('to') is None else res['to']
        return res

    def unlock_account(self, address, passphrase, unlock_time=10):
        res = self.make_request('personal_unlockAccount', [address, passphrase, unlock_time])
        return res

    def new_address(self, account, passphase):
        res = self.make_request('personal_newAccount', [passphase])
        return res

    def get_addresses(self, account, passphase):
        # TODO
        res = self.make_request('', [passphase])
        return res

    def estimate_gas(self, options):
        res = self.make_request('eth_estimateGas', [options])
        return int(res, 16)

    def transfer(self, passphrase, from_, to_, amount):
        options = {'from':from_, 'to':to_, 'value':hex(int(amount))}
        gas = self.estimate_gas(options)
        options['gas'] = gas

        # self.unlock_account(from_, passphrase)

        res = self.make_request('eth_sendTransaction', [options])
        return res, gas*self.settings['gasPrice']

    def best_block_number(self):
        res = self.make_request('eth_blockNumber')
        return int(res, 16)

    def new_filter(self, block_height, address):
        res = self.make_request('eth_newFilter', [{'fromBlock':hex(block_height),
                                              'toBlock':hex(block_height), 'address':address, 'topics':[]}])
        return res

    def get_filter_logs(self, f):
        res = self.make_request('eth_getFilterLogs', [f])
        return res

    def is_address_valid(self, address):
        if len(address) != 42:
            return False
        try:
            int(address, 16)
        except Exception as e:
            return False
        return True

    def to_wei(self, ether):
        return long(ether * decimal.Decimal(10.0**18))

    def from_wei(self, wei):
        return decimal.Decimal(wei) / decimal.Decimal(10.0**18)
