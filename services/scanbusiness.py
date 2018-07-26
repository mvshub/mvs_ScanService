from services.ibusiness import IBusiness
from services.address import AddressService
from modles import process
from modles.status import Status
from modles import db
from modles.swap import Swap
from modles.address import Address
from modles.binder import Binder
from modles.coin import Coin
from utils import response
from utils import notify
from utils.timeit import timeit
import threading
import time
import logging
from decimal import Decimal
from functools import partial


class ScanBusiness(IBusiness):

    def __init__(self, service, rpc, setting):
        IBusiness.__init__(self, service, rpc, setting)
        self.coin = setting['coin']
        self.addresses = set()
        self.status = 0
        self.swaps = {}

    @timeit
    def load_to_notify_swap(self):
        ids = db.session.query(Swap.tx_hash, Swap.tx_index, Swap.output_index).group_by(
            Swap.tx_hash, Swap.tx_index, Swap.output_index).having(
            db.func.count(Swap.status) == process.PROCESS_SWAP_NEW).all()

        for id_ in ids:
            swap = db.session.query(Swap).filter_by(
                tx_hash=id_[0], tx_index=id_[1], output_index=id_[2]).filter_by(coin=self.coin).first()
            if swap is None:
                continue

            swap.status = process.PROCESS_SWAP_NOTIFY
            swap.tx_time = 0
            self.swaps[swap.iden] = Swap.copy(swap)

    @timeit
    def process_notify(self):
        t = int(time.time())
        finished_notifies = []
        try:
            best_block_height = self.service.best_block_number
        except Exception as e:
            return True

        for i, swap in self.swaps.items():
            if swap.tx_time is None:
                swap.tx_time = 0
            if (t - swap.tx_time) < self.setting['retry_interval']:
                continue
            if (best_block_height - swap.block_height + 1) < self.setting['minconf']:
                continue

            swap.tx_time = t
            try:
                import copy
                dup = Swap.copy(swap)
                dup.amount = self.rpc.from_wei(dup.token, dup.amount)
                notify.notify_swap(
                    dup, self.service.best_block_number, self.setting['feedback'])
            except Exception as e:
                logging.error('%s notify swap failed,%s,%s' %
                              (self.coin, e, swap))
                continue

            item = db.session.query(Swap).filter_by(
                tx_hash=swap.tx_hash, tx_index=swap.tx_index,
                output_index=swap.output_index).filter_by(coin=self.coin).first()

            if item is not None:
                item.status = process.PROCESS_SWAP_NOTIFY
                db.session.add(item)
                db.session.commit()
            else:
                swap.iden = None
                swap.status = process.PROCESS_SWAP_NOTIFY
                db.session.add(swap)
                db.session.commit()

            self.swaps[i] = Swap.copy(swap)
            logging.info('%s notify swap % success, swap_address: %s' %
                         (self.coin, swap.token, swap.to_address))
            finished_notifies.append(i)

        for i in finished_notifies:
            self.swaps.pop(i)
        return True

    @timeit
    def load_status(self):
        s = db.session.query(Status).filter_by(coin=self.coin).first()
        if not s:
            s = Status()
            s.coin = self.coin
            s.height = 1

            db.session.add(s)
            db.session.commit()
        self.status = s.height

    @timeit
    def load_address(self):
        addresses = db.session.query(Address).filter_by(
            coin=self.coin, inuse=1).all()
        self.addresses.update([a.address for a in addresses])
        for a in addresses:
            logging.info("load addresses: {}".format(a.address))

    @timeit
    def on_address_change(self):
        self.post(self.load_address)

    @timeit
    def process_swaps(self):
        pass

    @timeit
    def commit_swap(self, swap):
        r = db.session.query(Swap).filter_by(
            coin=self.coin, tx_hash=swap['hash']).first()
        if r:
            logging.info('swap already existed')
            return

        item = Swap()
        item.coin = self.coin
        item.to_address = swap['swap_address']
        item.token = swap['token']
        item.amount = swap['amount']
        item.block_height = swap['height']
        item.tx_time = swap['time']
        item.tx_hash = swap['hash']
        item.tx_index = swap['index']
        item.output_index = swap.get('output_index')
        item.create_time = int(time.time() * 1000)
        item.status = process.PROCESS_SWAP_NEW

        db.session.add(item)
        db.session.flush()
        # print(item.tx_hash)
        db.session.commit()

        self.swaps[item.iden] = Swap.copy(item)

    @timeit
    def commit_swaps(self, swaps):
        for swap in swaps:
            self.commit_swap(swap)

    @timeit
    def commit_binder(self, binder_):
        r = db.session.query(Binder).filter_by(tx_hash=binder_['hash']).all()
        if r:
            logging.info('binder already existed,from: %s, to: %s , tx_hash: %s' % (
                binder_['from'], binder_['to'], binder_['hash']))
            return

        binder = Binder()
        binder.binder = binder_['from']
        binder.to = binder_['to']
        binder.block_height = binder_['height']
        binder.tx_hash = binder_['hash']
        binder.tx_time = binder_['time']

        db.session.add(binder)
        db.session.flush()
        db.session.commit()

    @timeit
    def commit_binders(self, binders):
        for bd in binders:
            self.commit_binder(bd)

    @timeit
    def process_scan(self):
        rpc = self.rpc
        try:
            best_block_number = self.service.best_block_number
        except Exception as e:
            return True
        if (best_block_number - self.status + 1) < self.setting['minconf']:
            return True
        if not self.addresses:
            return True

        block = rpc.get_block_by_height(self.status, self.addresses)
        swaps = []
        binders = []
        for tx in block['txs']:
            if tx.get('isBinder', False) == True:
                binders.append(tx)
                logging.info(' binder address, from:%s, to:%s' %
                             (tx['from'], tx['to']))
            elif rpc.is_swap(tx, self.addresses):
                swaps.append(tx)
                logging.info('new swap found: %s' % tx)

        for swap in swaps:
            swap['amount'] = swap['value']
            swap['height'] = int(swap['blockNumber'])
        self.commit_swaps(swaps)

        for bd in binders:
            bd['height'] = int(bd['blockNumber'])
        self.commit_binders(binders)

        logging.info("> scan block {} : {} txs, {} swaps, {} binders".format(
            self.status, len(block['txs']), len(swaps), len(binders)))

        if swaps or self.status % 50 == 0:
            s = db.session.query(Status).filter_by(coin=self.coin).first()
            if not s:
                s = Status()
                s.coin = self.coin
            s.height = self.status

            db.session.add(s)

            coins = rpc.get_coins()
            for c in coins:
                s = db.session.query(Coin).filter_by(
                    name=c.name, token=c.token).first()
                if s is None:
                    s = c
                s.block_height = self.status
                s.total_supply = c.total_supply
                db.session.add(s)

            db.session.commit()

        self.status += 1
        return True

    def start(self):
        IBusiness.start(self)
        self.post(self.load_address)
        self.post(self.load_status)
        # self.post(self.load_to_notify_swap)
        self.post(self.process_scan)
        # self.post(self.process_notify)
