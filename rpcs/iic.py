from eth_token import EthToken
import decimal


class Iic(EthToken):
    def get_block_by_height(self, height):
        block = self.make_request('eth_getBlockByNumber', [hex(int(height)), True])
        block['txs'] = block['transactions']
        for i, tx in enumerate(block['txs']):
            if tx['to'] is None or tx['to'] != self.contract_address:
                tx['to'] = 'create contract'
                continue
            receipt = self.make_request('eth_getTransactionReceipt', [tx['hash']])
            if not receipt['logs']:
                continue
            tx['index'] = i
            tx['blockNumber'] = int(tx['blockNumber'], 16)
            tx['time'] = int(block['timestamp'], 16)
            input_ = tx['input']
            if len(input_) == 202:
                value = int('0x' + input_[138:], 16)
                to_addr = '0x' + input_[98:138]
                tx['to'] = to_addr
                tx['value'] = value
                tx['amount'] = value
            elif len(input_) == 138:
                value = int('0x' + input_[74:], 16)
                to_addr = '0x' + input_[34:74]
                tx['to'] = to_addr
                tx['value'] = value
                tx['amount'] = value

        return block