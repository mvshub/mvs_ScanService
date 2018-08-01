from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException
import json
import decimal
from models.coin import Coin
from models.constants import Status


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0

    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = 'ETP'
        self.tokens = settings['tokens']
        self.token_names = [x['name'] for x in self.tokens]
        Logger.get().info("init type {}, tokens: {}".format(
            self.name, self.token_names))

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

    def get_balance(self, name, address):
        res = self.make_request('getaddressetp', [address])
        return res['result']['unspent']

    def get_coins(self):
        coins = []
        for x in self.tokens:
            supply = self.get_total_supply(x['name'])
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = x['name']
                coin.total_supply = supply
                coin.decimal = self.decimals(coin.token)
                coin.status = int(Status.Token_Normal)
                coins.append(coin)
        return coins

    def get_total_supply(self, token_name=None):
        res = self.make_request('getasset', [token_name])
        assets = res['result']
        if len(assets) > 0:
            supply = int(assets[0]['maximum_supply'])
            if token_name in self.token_names:
                supply = self.from_wei(token_name, supply)
                return supply
        return 0

    def get_block_by_height(self, height, addresses):
        res = self.make_request('getblock', [height])
        timestamp = res['result']['timestamp']
        transactions = res['result']['transactions']

        txs = []
        for i, trans in enumerate(transactions):
            input_addresses = [input_['address'] for input_ in trans[
                'inputs'] if input_.get('address') is not None]
            input_addresses = list(set(input_addresses))
            from_addr = input_addresses[0] if len(
                input_addresses) == 1 else None

            tx = {}
            for j, output in enumerate(trans['outputs']):

                if output['attachment']['type'] == 'asset-transfer':
                    to_addr = '' if output.get(
                        'address') is None else output['address']
                    if to_addr not in addresses:
                        continue

                    if from_addr == to_addr:
                        continue

                    tx['type'] = 'ETP'
                    tx['blockNumber'] = height
                    tx['index'] = i
                    tx['hash'] = trans['hash']
                    tx['swap_address'] = to_addr
                    tx['output_index'] = j
                    tx['time'] = int(timestamp)
                    tx['input_addresses'] = input_addresses
                    tx['script'] = output['script']
                    tx['token'] = output['attachment']['symbol']
                    tx['value'] = int(output['attachment']['quantity'])
                    tx['from'] = from_addr

                elif output['attachment']['type'] == 'message':
                    address = output['attachment']['content'].lower()
                    if not address.startswith('0x'):
                        address = "0x{}".format(address)
                    tx['to'] = address

            if tx.get('token') is not None and tx.get('to') is not None:
                address = tx.get('to')
                if self.is_to_address_valid(address):
                    Logger.get().error("transfer {} - {}, height: {}, hash: {}, invalid to: {}".format(
                        tx['token'], tx['value'], tx['hash'], tx['blockNumber'], address))
                    continue

                txs.append(tx)
                Logger.get().info("transfer {} - {}, height: {}, hash: {}, from:{}, to: {}".format(
                    tx['token'], tx['value'], tx['blockNumber'], tx['hash'], from_addr, address))

        res['txs'] = txs
        return res

    def is_to_address_valid(self, address):
        return address is None or len(address) < 42 or not self.is_hex(address[2:])

    def is_address_valid(self, address):
        if address is None or address == '':
            return False

        res = self.make_request('validateaddress', [address])
        return res['result']['is_valid']

    def is_hex(self, s):
        if s is None or s == '':
            return False
        import re
        return re.fullmatch(r"^[0-9a-f]+", s) is not None

    def is_swap(self, tx, addresses):
        if tx['type'] != self.name:
            return False
        if tx['value'] <= 0:
            return False
        if tx['token'] is None:
            return False

        if tx['token'] not in self.token_names:
            return False

        if self.is_to_address_valid(tx['to']):
            return False

        if set(tx['input_addresses']).intersection(set(addresses)):
            return False

        if tx['script'].find('numequalverify') < 0 and tx['swap_address'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        result = None
        try:
            res = self.make_request('gettransaction', [txid])
            result = res['result']
            if result:
                result['blockNumber'] = result['height']
        except RpcException as e:
            Logger.get().error("failed to get transaction: {}".format(str(e)))
            raise
        return result

    def best_block_number(self):
        res = self.make_request('getheight')
        return res['result']

    def decimals(self, token):
        for i in self.tokens:
            if i['name'] == token:
                return i['decimal']
        return 0
