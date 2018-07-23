from rpcs.btc import Btc


class Bch(Btc):
	def __init__(self, settings):
		Btc.__init__(self, settings)

	def get_block_by_height(self, height):
		block = Btc.get_block_by_height(self, height)
		for tx in block['txs']:
			if tx['to'][0:len('bitcoincash:')] == 'bitcoincash:':
				tx['to'] = tx['to'][len('bitcoincash:'):len(tx['to'])]

		return block
