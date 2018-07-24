from services.address import AddressService
import logging
from utils import response
from modles.swap import Swap
from services.scanbusiness import ScanBusiness
from modles import process
from modles import db


class ScanService(AddressService):

    def __init__(self, app, rpcmanager, settings):
        AddressService.__init__(self, app, rpcmanager, settings)
        self.businesses = {}

    def on_address_change(self, coin):
        try:
            self.businesses[coin].on_address_change()
        except Exception as e:
            logging.error('on address change failed,%s' % e)

    def start_service(self):
        AddressService.start_service(self)

        for d in self.settings['services']:
            if not d['enable']:
                continue

            coin = d['coin']
            rpc = self.rpcmanager.get_available_feed(d['rpc'])

            logging.info(
                "start ScanBusiness for {}, height: {}, with setting {}".format(
                coin, self.best_block_number, d))

            self.get_best_block_number(rpc)

            b = ScanBusiness(self, rpc, d)
            self.businesses[coin] = b
            b.start()

        if not self.businesses:
            return

        self.registe_service('/service/%s/block/number',
                             self.process_get_block_number, 'block_number')

    def stop(self):
        AddressService.stop(self)

    # def process_get_transaction(self, rpc, setting, txid):
    #     try:
    #         res = rpc.get_transaction(txid)
    #     except Exception as e:
    #         return response.make_response(response.ERR_BAD_PARAMETER, '%s' % e)
    #     return response.make_response(result=res)

    # def process_get_scan(self, rpc, setting, address, page, limit=10):
    #     if not rpc.is_address_valid(address):
    #         return response.make_response(response.ERR_INVALID_ADDRESS)
    #     ds = db.session.query(Swap).filter_by(
    #         address=address, asset=rpc.name,
    #         status=process.PROCESS_DEPOSIT_NEW).limit(limit).offset(page * limit).all()
    #     ds = [{'deposit_id': d.iden, 'asset': d.asset, 'amount': d.amount,
    #            'to_address': d.address, 'txid': d.tx_hash, 'height': d.block_height} for d in ds]
    #     return response.make_response(result=ds)

    def process_get_block_number(self, rpc, setting):
        self.get_best_block_number(rpc)
        return response.make_response(result=self.best_block_number)

    def get_best_block_number(self, rpc):
        self.best_block_number = rpc.best_block_number()
        return self.best_block_number
