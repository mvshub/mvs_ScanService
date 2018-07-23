from rpcs.btc import Btc
import logging

class Usd(Btc):
	def __init__(self, settings):
		Btc.__init__(self, settings)
		self.name = settings['name']

	def get_block_by_height(self, height):
		block_hash = self.make_request('getblockhash', [int(height)])
		block = self.make_request('getblock', [block_hash])
		txs = []
		for i, txid in enumerate(block['tx']):
			res = None
			try:
				res = self.make_request('omni_gettransaction', [txid])
				if res is None:
					continue
			except Exception as e:
				continue
			if not res['valid']:
				continue
			amount = res.get('amount')
			if amount is None:
				continue
			if float(amount) == 0:
				continue
			tx = {}
			tx['value'] = amount
			to = res.get('referenceaddress')
			if to is None:
				continue
			tx['to'] = to
			tx['blockNumber'] = height
			tx['hash'] = txid
			tx['index'] = i
			tx['time'] = res['blocktime']
			txs.append(tx)
		block['txs'] = txs
		return block
