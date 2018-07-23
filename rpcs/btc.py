from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import base64


class Btc(Base):
    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = settings['name']

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        data = {'method':method, 'params':params}
        auth = 'Basic %s' % base64.b64encode('%s:%s' % (self.settings['rpcuser'], self.settings['rpcpassword']) )
        res = requests.post(self.settings['uri'], json.dumps(data), headers = {'Authorization':auth}, timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
            #raise RpcException('bad request code,%s' % res)
        try:
            js = json.loads(res.text)
            if isinstance(js, dict) and js.get('error') is not None:
                raise RpcException(js['error'])
            return js['result']
        except ValueError as e:
            pass
        return res.text

    def get_balance(self, address):
        res = self.make_request('fetch-balance', [address])
        return res

    def get_block_by_height(self, height):
        block_hash = self.make_request('getblockhash', [int(height)])
        block = self.make_request('getblock', [block_hash])
        txs = []
        for i, tx in enumerate(block['tx']):
            res = self.make_request('getrawtransaction', [tx, 1])
            for output in res['vout']:
                if output['scriptPubKey']['type'] == 'nulldata':
                    continue
                if output['scriptPubKey'].get('addresses') is None:
                    continue
                output['to'] = output['scriptPubKey']['addresses'][0]
                output['blockNumber'] = height
                output['value'] = output['value']
                output['hash'] = res['hash']
                output['index'] = i
                output['output_index'] = output['n']
                output['time'] = block['time']
                txs.append(output)
        block['txs'] = txs
        return block

    def is_deposit(self, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('getrawtransaction', [txid, 1])
        return res

    def new_address(self, account, passphase):
        res = self.make_request('getnewaddress', [account])
        return res

    def best_block_number(self):
        res = self.make_request('getinfo')
        return int(res['blocks'])

    def to_wei(self, ether):
        return ether
        # return long(ether * 10.0**18)

    def from_wei(self, wei):
        return wei
