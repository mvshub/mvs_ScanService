from rpcs.eth import Eth
import decimal
import logging
from utils.exception import TransactionNotfoundException
import binascii


class EthToken(Eth):

    def __init__(self, settings):
        Eth.__init__(self, settings)
        self.name = settings['name']
        self.contract_address = settings['contract_address']
        self.contract_mapaddress = settings['contract_mapaddress']
        self.tokens = settings['tokens']
        self.token_names = [x['name'] for x in self.tokens]
        logging.info("EthToken: contract_address: {}, contract_mapaddress".format(
            self.contract_address, self.contract_mapaddress))

    def start(self):
        Eth.start(self)
        return True

    def stop(self):
        return False

    def get_balance(self, address):
        if len(address) == 42:
            address = address[2:]
        data = '0x70a08231000000000000000000000000%s' % address
        balance = self.make_request(
            'eth_call', [{'to': self.contract_address, 'data': data}, 'latest'])
        return int(balance, 16)

    def decimals(self):
        data = '0x784c4fb1'
        balance = self.make_request(
            'eth_call', [{'to': self.contract_address, 'data': data}, 'latest'])
        return int(balance, 16)

    def total_supply(self):
        data = '0x18160ddd'
        balance = self.make_request(
            'eth_call', [{'to': self.contract_address, 'data': data}, 'latest'])
        return int(balance['result'], 16)

    def symbol(self):
        data = '0x95d89b41'
        symbol = self.make_request(
            'eth_call', [{'to': self.contract_address, 'data': data}, 'latest'])

        if len(symbol) != 194:
            return ""

        strLen = int('0x' + symbol[126:130], 16)    
        return str(binascii.unhexlify(symbol[130:194])[:strLen], "utf-8")

    def transfer(self, passphrase, from_address, to_address, amount):  # maybe failed
        if len(to_address) == 42:
            to_address = to_address[2:]
        # self.unlock_account(from_address, passphrase)
        data = '0xa9059cbb' + ('0' * 24) + to_address + ('%064x' % amount)
        res = self.make_request('eth_sendTransaction', [
                                {'from': from_address, 'to': self.contract_address, 'data': data}])
        return res, 0

    def to_wei(self, token):
        return long(token * decimal.Decimal(10.0**self.settings['decimal']))

    def from_wei(self, wei):
        return decimal.Decimal(wei) / decimal.Decimal(10.0**self.settings['decimal'])

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

    def is_swap(self, tx, addresses):
        if 'type' not in tx  or tx['type'] != self.name:
            return False

        if tx['value'] <= 0:
            return False
        if tx['token'] is None or tx['token'] not in self.token_names:
            return False

        return True



    def get_block_by_height(self, height, addresses):
        block = self.make_request(
            'eth_getBlockByNumber', [hex(int(height)), True])

        block['txs'] = block['transactions']
        for i, tx in enumerate(block['txs']):
            if tx['to'] is None or tx['to'] not in (self.contract_address, self.contract_mapaddress):
                tx['to'] = 'create contract'
                continue

            receipt = self.make_request(
                'eth_getTransactionReceipt', [tx['hash']])
            if not receipt['logs']:
                continue

            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            tx['isBinder'] = False
            tx['type'] = 'ETH'

            input_ = tx['input']
            if tx['to'] == self.contract_address:
                if len(input_) != 138:
                    continue
                value = int('0x' + input_[74:], 16)
                to_addr = '0x' + input_[34:74]
                tx['swap_address'] = to_addr
                tx['value'] = value
                tx['amount'] = value
                tx['token'] = self.symbol()

            else:
                if len(input_) != 202:
                    continue
                strLen = int('0x' + input_[134:138], 16)
                tx['to'] = binascii.unhexlify(input_[138:202])[:strLen]

                tx['isBinder'] = True
                logging.info('new binder found, from:%s, to:%s' % (tx['from'], tx['to']))

        return block
