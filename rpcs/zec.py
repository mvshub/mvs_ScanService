from rpcs.btc import Btc


class Zec(Btc):

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
                output['hash'] = res['txid']
                output['index'] = i
                output['output_index'] = output['n']
                output['time'] = block['time']
                txs.append(output)
        block['txs'] = txs
        return block
