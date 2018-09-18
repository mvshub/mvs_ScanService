from rpcs.base import Base
import requests
from utils.log.logger import Logger
from utils.exception import RpcException, CriticalException
import json
import decimal
from models import db
from models.coin import Coin
from models.constants import Status
from models import constants
import time
import re


class Etp(Base):
    rpc_version = "2.0"
    rpc_id = 0

    tx_unknown = 0
    tx_mst_transfer = 1
    tx_mit_transfer = 2

    def __init__(self, settings, tokens):
        Base.__init__(self, settings)

        self.token_mapping = json.loads(
            open('config/token_mapping.json').read())

        self.name = 'ETP'
        self.tokens = {}
        for token in tokens:
            name = token['name']
            token['mvs_symbol'] = self.get_mvs_symbol(name)
            self.tokens[name] = token
        self.token_names = [v['mvs_symbol'] for k, v in self.tokens.items()]

        Logger.get().info("init type {}, tokens: {}".format(
            self.name, self.token_names))
        self.developers = ("MAwLwVGwJyFsTBfNj2j5nCUrQXGVRvHzPh",
                           "tJNo92g6DavpaCZbYjrH45iQ8eAKnLqmms")
        self.minfee = constants.MIN_FEE_FOR_ETP_DEVELOPER_COMMUNITY

        self.tx_verify_uri = settings['tx_verify_uri']

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
            self.settings['uri'], json.dumps(req_body), timeout=constants.DEFAULT_REQUEST_TIMEOUT)
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

    def get_coins(self):
        coins = []
        for k, v in self.tokens.items():
            symbol = v['mvs_symbol']
            supply = self.get_total_supply(symbol)
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = symbol
                coin.total_supply = supply
                coin.decimal = self.get_decimal(symbol)
                coin.status = int(Status.Token_Normal)
                coins.append(coin)
        return coins

    def get_total_supply(self, token=None):
        res = self.make_request('getasset', [token])
        assets = res['result']
        if len(assets) > 0:
            supply = int(assets[0]['maximum_supply'])
            if token in self.token_names:
                supply = self.from_wei(token, supply)
                return supply
        return 0

    def is_mst_transfer(self, output):
        return output['attachment']['type'] == 'asset-transfer'

    def is_mit_transfer(self, output):
        return (output['attachment']['type'] == 'mit' and
                output['attachment']['status'] == 'transfered')

    def parse_tx_type(self, trans):
        for j, output in enumerate(trans['outputs']):
            if self.is_mst_transfer(output):
                return tx_mst_transfer
            elif self.is_mit_transfer(output):
                return tx_mit_transfer

        return tx_unknown

    def parse_target_address(self, output):
        assert(output['attachment']['type'] == 'message')
        content = output['attachment']['content']
        if content and len(content) > 0:
            try:
                rst = json.loads(content)
                if rst == None or 'type' not in rst or 'address' not in rst:
                    return None

                if rst['type'] == 'ETH':
                    address = rst['address']
                    if not address.startswith('0x'):
                        address = "0x{}".format(address)
                    return address.lower()
            except Exception as e:
                Logger.get().info("height: {}, failed to load json: {}".format(height, content))

        return None

    def process_mst_transfer(self, scan_address, trans, input_addresses, from_addr):
        tx = {}

        nonce = 0
        for j, output in enumerate(trans['outputs']):

            # get swap info of token
            if self.is_mst_transfer(output):
                to_addr = '' if output.get(
                    'address') is None else output['address']

                # check it is scan address
                if to_addr != scan_address:
                    continue

                # check it is not from scan address
                if to_addr in input_addresses:
                    continue

                tx['nonce'] = nonce
                tx['blockhash'] = block
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

            # get json content of swap target address
            elif output['attachment']['type'] == 'message':
                target_address = self.parse_target_address(output)
                if target_address:
                    tx['to'] = target_address

            # get fee for developer-community
            elif output['attachment']['type'] == 'etp':
                to_addr = '' if output.get(
                    'address') is None else output['address']

                if to_addr in input_addresses:
                    continue

                if to_addr not in self.developers:
                    continue

                tx['fee'] = output["value"]

        if tx.get('token') is not None and tx.get('to') is not None:
            token = tx['token']
            if token not in self.token_names:
                continue
            tx['value'] = self.from_wei(token, tx['value'])
            address = tx.get('to')
            fee = 0 if not tx.get('fee') else tx['fee']

            # check it is a valid eth address
            if not self.is_eth_address_valid(address):
                Logger.get().error("transfer mst {} - {}, height: {}, hash: {}, invalid to: {}".format(
                    token, tx['value'], tx['hash'], tx['blockNumber'], address))
                tx['message'] = 'invalid to address:' + address
                tx['ban'] = True

            # check fee
            elif fee < self.minfee:
                Logger.get().error("transfer mst {} - {}, height: {}, hash: {}, invalid fee: {}".format(
                    token, tx['value'], tx['hash'], tx['blockNumber'], fee))
                tx['message'] = 'invalid fee: {}'.format(fee)
                tx['ban'] = True

            tx['fee'] = fee
            Logger.get().info("transfer mst {} - {}, height: {}, hash: {}, from:{}, to: {}".format(
                token, tx['value'], tx['blockNumber'], tx['hash'], from_addr, address))
        else:
            tx = None

        return tx

    def process_mit_transfer(self, scan_address, trans, input_addresses, from_addr):
        tx = {}

        nonce = 0
        for j, output in enumerate(trans['outputs']):
            if self.is_mit_transfer(output):
                to_addr = '' if output.get(
                    'address') is None else output['address']

                # check it is scan address
                if to_addr != scan_address:
                    continue

                # check it is not from scan address
                if to_addr in input_addresses:
                    continue

                tx['nonce'] = nonce
                tx['blockhash'] = block
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
                tx['value'] = 1
                tx['from'] = from_addr

            # get json content of swap target address
            elif output['attachment']['type'] == 'message':
                target_address = self.parse_target_address(output)
                if target_address:
                    tx['to'] = target_address

            # get fee for developer-community
            elif output['attachment']['type'] == 'etp':
                to_addr = '' if output.get(
                    'address') is None else output['address']

                if to_addr in input_addresses:
                    continue

                if to_addr not in self.developers:
                    continue

                tx['fee'] = output["value"]

        if tx.get('token') is not None and tx.get('to') is not None:
            token = tx['token']

            # TODO check database
            Logger.get().info("====== TODO check mit token from database.")
            if token not in self.token_names:
                continue

            address = tx.get('to')
            fee = 0 if not tx.get('fee') else tx['fee']

            # check it is a valid eth address
            if not self.is_eth_address_valid(address):
                Logger.get().error("transfer mit {} - {}, height: {}, hash: {}, invalid to: {}".format(
                    token, tx['value'], tx['hash'], tx['blockNumber'], address))
                tx['message'] = 'invalid to address:' + address
                tx['ban'] = True

            # check fee
            elif fee < self.minfee:
                Logger.get().error("transfer mit {} - {}, height: {}, hash: {}, invalid fee: {}".format(
                    token, tx['value'], tx['hash'], tx['blockNumber'], fee))
                tx['message'] = 'invalid fee: {}'.format(fee)
                tx['ban'] = True

            tx['fee'] = fee
            Logger.get().info("transfer mit {} - {}, height: {}, hash: {}, from:{}, to: {}".format(
                token, tx['value'], tx['blockNumber'], tx['hash'], from_addr, address))
        else:
            tx = None

        return tx

    def get_block_by_height(self, height, scan_address):
        res = self.make_request('getblock', [height])
        timestamp = res['result']['timestamp']
        transactions = res['result']['transactions']
        block = res['result']['hash']

        txs = []
        for i, trans in enumerate(transactions):
            tx_type = self.parse_tx_type(trans)
            if tx_type == tx_unknown:
                continue

            input_addresses = [input_['address'] for input_ in trans[
                'inputs'] if input_.get('address') is not None]
            input_addresses = list(set(input_addresses))
            from_addr = input_addresses[0] if len(input_addresses) > 0 else ''

            if tx_type == tx_mst_transfer:
                tx = self.process_mst_transfer(
                    scan_address, trans, input_addresses, from_addr)
                if tx:
                    txs.append(tx)

            elif tx_type == tx_mit_transfer:
                tx = self.process_mit_transfer(
                    scan_address, trans, input_addresses, from_addr)
                if tx:
                    txs.append(tx)

        res['txs'] = txs
        return res

    def verify_tx(self, tx):
        res = requests.get(
            self.tx_verify_uri + str(tx['hash']), timeout=constants.DEFAULT_REQUEST_TIMEOUT)
        if res.status_code != 200:
            raise RpcException('bad request code: {}'.format(res.status_code))

        try:
            js = json.loads(res.text)['result']
            if (js['hash'] == tx['hash'] and js['height'] == tx['blockNumber'] and
                    js['block'] == tx['blockhash']):
                return Status.Tx_Checked
            else:
                tx['ban'] = True
                tx['message'] = ('Check Tx failed, defalut tx, cur = [%s], verify_tx = [%s]' %
                                 (tx, js))
                return Status.Tx_Ban

        except Exception as e:
            Logger.get().error(
                'bad response content, failed to parse,%s' % res.text)

        return Status.Tx_Unchecked

    def is_eth_address_valid(self, address):
        return address is not None and re.fullmatch(r"^0x[0-9a-f]{40}$", address) is not None

    def is_address_valid(self, address):
        if address is None or address == '':
            return False

        res = self.make_request('validateaddress', [address])
        return res['result']['is_valid']

    def is_swap(self, tx, scan_address):
        if 'type' not in tx or tx['type'] != self.name:
            return False

        if tx['value'] <= 0:
            return False

        if tx['token'] not in self.token_names:
            return False

        if scan_address in tx['input_addresses']:
            return False

        if tx['swap_address'] != scan_address:
            return False

        # prevent locking tx
        if 'numequalverify' in tx['script']:
            return False

        return True

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

    def get_decimal(self, symbol):
        for k, v in self.tokens.items():
            if v['mvs_symbol'] == symbol:
                return min(i['decimal'], constants.MAX_SWAP_ASSET_DECIMAL)
        raise CriticalException(
            'decimal config missing: coin={}, token={}'.format(self.name, symbol))

    def get_mvs_symbol(self, token):
        if token in self.token_mapping:
            return self.token_mapping[token]
        return constants.SWAP_TOKEN_PREFIX + token
