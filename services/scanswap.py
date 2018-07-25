from services.abstract import AbstractService
from modles.swap import Swap
from modles import process
from modles import db
import logging


class SwapService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)
        self.continue_flag = False

    def process_swap_table(self):
        ids = db.session.query(Swap.tx_hash, Swap.tx_index, Swap.output_index).group_by(
            Swap.tx_hash, Swap.tx_index, Swap.output_index).having(
            db.func.count(Swap.status) == process.PROCESS_SWAP_NEW).all()

        for id_ in ids:
            if not self.continue_flag:
                break

            swap = db.session.query(Swap).filter_by(
                tx_hash=id_[0], tx_index=id_[1], output_index=id_[2]).first()
            if swap is None:
                continue

            swap.status = process.PROCESS_SWAP_NOTIFY
            swap.tx_time = 0
            self.process_swap_row(swap)

    def process_swap_row(self, swap):
        for service in self.settings['services']:
            if not service['enable']:
                continue
            service_founded = False
            coin = swap.coin
            if service['coin'] == coin:
                service_founded = True
                rpc = self.rpcmanager.get_available_feed(service['rpc'])

                if coin == 'ETP':
                    self.swap_etp_asset(rpc, swap)
                elif coin == 'ETH':
                    self.swap_eth(rpc, swap)
                elif coin == 'ETHToken':
                    self.swap_eth_token(rpc, swap)
                else:
                    logging.error('not supported coin type, {}'.format(coin))

            if not service_founded:
                logging.error('no config service for coin type, {}'.format(coin))

    def swap_etp_asset(self, rpc, swap):
        pass

    def swap_eth(self, rpc, swap):
        pass

    def swap_eth_token(self, rpc, swap):
        pass

    def start(self):
        self.continue_flag = True
        self.process_swap_table()

    def stop(self):
        self.continue_flag = False
