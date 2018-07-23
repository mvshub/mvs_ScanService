from rpcs.btc import Btc
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import base64

class NonWalletTransaction(Exception):
    pass

class Nxs(Btc):
    def __init__(self, settings):
        Btc.__init__(self, settings)
        self.name = 'NXS'

    def make_request(self, method, params=[]):
        data = {'method':method, 'params':params}
        info = '%s:%s' % (self.settings['rpcuser'], self.settings['rpcpassword'])
        auth = 'Basic %s' % base64.b64encode(bytes(info, 'utf-8'))
        res = requests.post(self.settings['uri'], json.dumps(data), headers = {'Authorization':auth}, timeout=5)
        if res.status_code == 500 and res.text == '{"result":null,"error":{"code":-5,"message":"Invalid or non-wallet transaction id"},"id":null}\n':
            raise NonWalletTransaction(res.text)

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

    def get_block_by_height(self, height):
        block_hash = self.make_request('getblockhash', [int(height)])
        block = self.make_request('getblock', [block_hash])
        txs = []
        for i, tx in enumerate(block['tx']):
            try:
                res = self.make_request('gettransaction', [tx])
            except NonWalletTransaction as e:
                continue
            for j, output in enumerate(res['details']):
                if output['category'] != 'receive':
                    continue
                output['to'] = output['address']
                output['blockNumber'] = height
                output['value'] = output['amount']
                output['hash'] = tx
                output['index'] = i
                output['output_index'] = j
                output['time'] = res['time']
                txs.append(output)
        block['txs'] = txs
        return block

    def is_deposit(self, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('gettransaction', [txid])
        return res
