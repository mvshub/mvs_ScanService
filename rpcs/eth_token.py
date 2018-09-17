from rpcs.eth import Eth
import decimal
from utils.log.logger import Logger
from utils.exception import TransactionNotfoundException
import binascii
from models.coin import Coin
from models.constants import Status


class EthToken(Eth):

    def __init__(self, settings, tokens):
        Eth.__init__(self, settings, tokens)
        self.name = settings['name']

        self.token_names = [v['name'] for k, v in self.tokens.items()]

        self.contracts = {}
        for k, v in self.tokens.items():
            address = v['contract_address'].lower()
            self.contracts[address] = v

        Logger.get().info("EthToken: tokens: {}, contract_mapaddress".format(
            self.tokens, self.contract_mapaddress))

    def start(self):
        Eth.start(self)
        return True

    def stop(self):
        return False

    def get_contractaddress(self, name):
        if name in self.tokens:
            token_setting = self.tokens[name]
            return token_setting['contract_address'].lower()
        return None

    def get_coins(self):
        coins = []
        for k, v in self.tokens.items():
            if v.get('token_type') != 'erc20':
                continue

            name = v['name']
            supply = self.get_total_supply(name)
            if supply != 0:
                coin = Coin()
                coin.name = self.name
                coin.token = name
                coin.total_supply = self.from_wei(name, supply)
                coin.decimal = self.get_decimal(coin.token)
                coin.status = int(Status.Token_Normal)
                coins.append(coin)
        return coins

    def get_total_supply(self, name=None):
        contract = self.get_contractaddress(name)
        if contract is None:
            return 0
        data = '0x18160ddd'
        balance = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])
        return int(balance, 16)

    def symbol(self, name=None, contract=None):
        if contract is None:
            contract = self.get_contractaddress(name)

        if contract is None:
            return ""

        data = '0x95d89b41'
        symbol = self.make_request(
            'eth_call', [{'to': contract, 'data': data}, 'latest'])

        if symbol is None or len(symbol) != 194:
            return ""

        strLen = int('0x' + symbol[126:130], 16)
        return str(binascii.unhexlify(symbol[130:194])[:strLen], "utf-8")

    def get_decimal(self, name):
        if name in self.tokens:
            settings = self.tokens[name]
            return int(settings['decimal'])
        raise CriticalException(
            'decimal config missing: coin={}, token:{}'.format(self.name, name))

    def get_transaction(self, txid):
        res = self.make_request('eth_getTransactionByHash', [txid])
        if not res:
            return res

        res['blockNumber'] = int(res['blockNumber'], 16)
        input_ = res['input']
        if len(input_) != 138:
            return

        value = int('0x' + input_[74:], 16)
        to_addr = '0x' + input_[34:74]
        res['to'] = to_addr
        res['value'] = value
        receipt = self.make_request('eth_getTransactionReceipt', [txid])
        if not receipt['logs']:
            return
        return res

    def is_swap(self, tx, scan_address):
        if 'type' not in tx or tx['type'] != self.name:
            return False

        if tx['value'] < 0:
            return False

        if tx['token'] is None or tx['token'] not in self.token_names:
            return False

        return True

    def get_block_by_height(self, height, scan_address):
        block = self.make_request(
            'eth_getBlockByNumber', [hex(int(height)), True])

        block['txs'] = []
        for i, tx in enumerate(block['transactions']):
            if tx['to'] is None \
                    or (tx['to'] not in self.contracts and tx['to'] != self.contract_mapaddress):
                tx['to'] = 'create contract'
                continue

            receipt = self.make_request(
                'eth_getTransactionReceipt', [tx['hash']])
            if not receipt['logs']:
                continue

            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            tx['blockhash'] = tx['blockHash']
            tx['isBinder'] = False
            tx['type'] = self.name
            tx['fee'] = 0
            input_ = tx['input']
            
            if tx['to'] in self.contracts:
                token_setting = self.contracts[tx['to']]
                token_type = token_setting['token_type']
                if token_type == 'erc20':
                    if len(input_) != 138:
                        continue
                    to_addr = '0x' + input_[34:74]
                    if to_addr != scan_address:
                        continue
                    tx['swap_address'] = to_addr
                    tx['token'] = token_setting['name']
                    value = int('0x' + input_[74:], 16)
                    value = self.from_wei(tx['token'], value)
                    tx['value'] = value
                    tx['amount'] = value
                    tx['to'] = None

                elif token_type == 'erc721':
                    if len(input_) != 202:
                        continue
                    to_addr = '0x' + input_[98:138]
                    if to_addr != scan_address:
                        continue
                    tx['swap_address'] = to_addr
                    tx['token'] = token_setting['name']
                    value = int('0x' + input_[138:], 16)
                    tx['value'] = value
                    tx['amount'] = value
                    tx['to'] = None
            else:
                strLen = int('0x' + input_[134:138], 16)
                tx['swap_address'] = tx['to']
                tx['to'] = str(binascii.unhexlify(
                    input_[138:])[:strLen], "utf-8")
                tx['isBinder'] = True
                Logger.get().info('new binder found, from:%s, to:%s' %
                                  (tx['from'], tx['to']))

            block['txs'].append(tx)

        return block
