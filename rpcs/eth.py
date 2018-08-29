from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException
import json
import decimal
import binascii
from models.coin import Coin
from models.constants import Status


class Eth(Base):

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETH' if settings.get('name') is None else settings['name']
        self.contract_mapaddress = settings['contract_mapaddress'].lower()

        self.tx_verify_uri = settings['tx_verify_uri']

    def start(self):
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[]):
        data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 83}
        res = requests.post(
            self.settings['uri'], json.dumps(data),
            headers={'Content-Type': 'application/json'}, timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            raise RpcException(
                'bad response content, failed to parse,%s' % res.text)
        if js.get('error') is not None:
            raise RpcException('%s' % js['error']['message'])
        return js['result']

    def get_coins(self):
        coins = []
        supply = self.get_total_supply()
        if supply != 0:
            coin = Coin()
            coin.name = self.name
            coin.token = self.name
            coin.total_supply = self.from_wei(token=None, wei=supply)
            coin.decimal = 18
            coin.status = int(Status.Token_Normal)

            coins.append(coin)
        return coins

    def get_total_supply(self, token_name=None):
        res = requests.get('https://www.etherchain.org/api/supply', timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)
        except Exception as e:
            Logger.get().error(
                'bad response content, failed to parse,%s' % res.text)
            return 0

        return js['value']

    def get_block_by_height(self, height, addresses):
        # Logger.get().info(">>>>>>>>>> ETH : get_block_by_height")
        block = self.make_request('eth_getBlockByNumber', [
                                  hex(int(height)), True])
        block['txs'] = []
        for i, tx in enumerate(block['transactions']):
            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['blockhash'] = tx['blockHash']
            tx['time'] = int(block['timestamp'], 16)
            tx['isBinder'] = False
            tx['type'] = self.name
            if tx['to'] is None:
                continue
            elif tx['to'] == self.contract_mapaddress:
                input_ = tx['input']
                strLen = int('0x' + input_[134:138], 16)
                tx['to'] = str(binascii.unhexlify(
                    input_[138:])[:strLen], "utf-8")

                tx['isBinder'] = True
                Logger.get().info('new binder found, from:%s, to:%s' %
                                  (tx['from'], tx['to']))
            else:
                if tx['to'] not in addresses:
                    continue

                tx['swap_address'] = tx['to']
                tx['to'] = None
                tx['token'] = 'ETH'

            value = int(tx['value'], 16)
            value = self.from_wei(None, value)
            tx['value'] = value
            tx['amount'] = value
            tx['fee'] = 0

            block['txs'].append(tx)

        return block

    def verify_tx(self, tx):
        res = requests.get( self.tx_verify_uri + str(tx['hash']), timeout=5)
        if res.status_code != 200:
            raise RpcException('bad request code,%s' % res.status_code)
        try:
            js = json.loads(res.text)[0]
            def LSTRIP( x, prefix):
                if x.startswith(prefix): 
                    return x[len(prefix):]
                return x
            if ( LSTRIP(js['hash'], '0x') == LSTRIP( tx['hash'], '0x') and int(js['blocknumber']) == int(tx['blockNumber']) and
            LSTRIP( js['blockhash'], '0x') == LSTRIP( tx['blockHash'], '0x') and int(js['nonce']) == int(tx['nonce'],16) ):
                return Status.Tx_Checked
            else:
                tx['ban'] = True
                tx['message'] = ('Check Tx failed, defalut tx, cur = [%s], verify_tx = [%s]' %
                (tx, js) )
                return Status.Tx_Ban

        except Exception as e:
            Logger.get().error(
                'bad response content, failed to parse,%s' % res.text)

        return Status.Tx_Unchecked

    def is_swap(self, tx, addresses):
        if 'type' not in tx or tx['type'] != self.name:
            return False

        if tx['value'] <= 0:
            return False
        if tx['token'] is None or tx['token'] != self.name:
            return False

        return True

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res
        res['blockNumber'] = int(res['blockNumber'], 16) if res[
            'blockNumber'] else 0
        res['to'] = '' if res.get('to') is None else res['to']
        return res

    def estimate_gas(self, options):
        res = self.make_request('eth_estimateGas', [options])
        return int(res, 16)

    def best_block_number(self):
        res = self.make_request('eth_blockNumber')
        return int(res, 16)

    def new_filter(self, block_height, address):
        res = self.make_request('eth_newFilter',
                                [{'fromBlock': hex(block_height),
                                  'toBlock': hex(block_height),
                                  'address': address,
                                  'topics': []}])
        return res

    def get_filter_logs(self, f):
        res = self.make_request('eth_getFilterLogs', [f])
        return res

    def is_address_valid(self, address):
        if len(address) != 42:
            return False
        if address[:2] != '0x':
            return False
        try:
            int(address, 16)
        except Exception as e:
            return False
        return True

    def get_decimal(self, token):
        return 18
