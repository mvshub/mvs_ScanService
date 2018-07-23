from rpcs.eth import Eth
import decimal
import logging
from utils.exception import TransactionNotfoundException


class EthToken(Eth):

    def __init__(self, settings):
        Eth.__init__(self, settings)
        self.name = settings['name']
        self.contract_address = settings['contract_address']
        logging.info("EthToken: contract_address: {}".format(
            self.contract_address))

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

    def get_block_by_height(self, height):
        block = self.make_request(
            'eth_getBlockByNumber', [hex(int(height)), True])

        block['txs'] = block['transactions']
        for i, tx in enumerate(block['txs']):
            logging.info("get_tx: {}".format(tx))
            if tx['to'] is None or tx['to'] != self.contract_address:
                tx['to'] = 'create contract'
                continue

            receipt = self.make_request(
                'eth_getTransactionReceipt', [tx['hash']])
            if not receipt['logs']:
                continue

            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            input_ = tx['input']
            if len(input_) != 138:
                continue

            value = int('0x' + input_[74:], 16)
            to_addr = '0x' + input_[34:74]
            logging.info("input_: {}, to: {}, value: {}".format(
                input_, to_addr, value))
            tx['to'] = to_addr
            tx['value'] = value
            tx['amount'] = value
        return block
