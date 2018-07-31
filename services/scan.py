from services.abstract import AbstractService
from services.scanbusiness import ScanBusiness
from utils import response
from utils.log.logger import Logger
from models.swap import Swap
from models import db


class ScanService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)
        self.businesses = {}

    def start_service(self):
        for d in self.settings['services']:
            if not d['enable']:
                continue

            coin = d['coin']
            rpc = self.rpcmanager.get_available_feed(d['rpc'])

            Logger.get().info(
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

    def process_get_block_number(self, rpc, setting):
        self.get_best_block_number(rpc)
        return response.make_response(result=self.best_block_number)

    def get_best_block_number(self, rpc):
        self.best_block_number = rpc.best_block_number()
        return self.best_block_number
