from services.address import AddressService
from services.scanbusiness import ScanBusiness
from utils import response
from modles.swap import Swap
from modles import process
from modles import db
import logging


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

    def process_get_block_number(self, rpc, setting):
        self.get_best_block_number(rpc)
        return response.make_response(result=self.best_block_number)

    def get_best_block_number(self, rpc):
        self.best_block_number = rpc.best_block_number()
        return self.best_block_number
