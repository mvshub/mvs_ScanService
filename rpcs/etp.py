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
        self.tokens = settings['tokens']
        self.token_names = [x['name'] for x in self.tokens]
        logging.info("init type {}, tokens: {}".format(self.name, self.token_names))

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
        return res['result']['unspent']

    def get_block_by_height(self, height, addresses):
        res = self.make_request('getblockheader', ['-t', int(height)])
        block_hash = res['result']['hash']
        res = self.make_request('getblock', [block_hash, 'true'])
        timestamp = res['result']['timestamp']
        transactions = res['result']['transactions']
        logging.info(" > get block {}, {} txs".format(height, len(transactions)))

        txs = []
        for i, trans in enumerate(transactions):
            input_addresses = [input_['address'] for input_ in trans[
                'inputs'] if input_.get('address') is not None]

            tx = {}
            for j, output in enumerate(trans['outputs']):
                to_addr = '' if output.get('address') is None else output['address']

                if output['attachment']['type'] == 'asset-transfer':
                    if to_addr not in addresses:
                        continue

                    tx['type'] = 'ETP'
                    tx['blockNumber'] = height
                    tx['index'] = i
                    tx['hash'] = trans['hash']
                    tx['to'] = to_addr
                    tx['output_index'] = j
                    tx['time'] = int(timestamp)
                    tx['input_addresses'] = input_addresses
                    tx['script'] = output['script']
                    tx['token'] = output['attachment']['symbol']
                    tx['value'] = int(output['attachment']['quantity'])

                elif output['attachment']['type'] == 'message':
                    tx['swap_address'] = output['attachment']['content']

            if tx.get('token') is not None and tx.get('swap_address') is not None:
                txs.append(tx)
                logging.info("transfer {} - {}, height: {}, swap_address: {}".format(
                    tx['token'], tx['value'], tx['blockNumber'], tx['swap_address']))

        res['txs'] = txs
        return res

    def is_swap(self, tx, addresses):
        if tx['type'] != self.name:
            return False
        if tx['value'] <= 0:
            return False
        if tx['token'] is None:
            return False

        if tx['token'] not in self.token_names:
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

    def get_addresses(self, account, passphase):
        res = self.make_request('listaddresses', [account, passphase])
        addresses = res['result']
        return addresses

    def best_block_number(self):
        res = self.make_request('getheight')
        return res['result']

    def to_wei(self, ether):
        return int(decimal.Decimal(ether) * decimal.Decimal(10.0**8))
        # return long(ether * 10.0**18)

    def from_wei(self, wei):
        return wei / decimal.Decimal(10.0**8)
