from services.ibusiness import IBusiness
from services.address import AddressService
from modles import process
from modles.status import Status
from modles import db
from modles.swap import Swap
from modles.address import Address
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
            Swap.tx_hash, Swap.tx_index, Swap.output_index).having(db.func.count(Swap.status) == 1).all()

        for id_ in ids:
            dep = db.session.query(Swap).filter_by(
                tx_hash=id_[0], tx_index=id_[1], output_index=id_[2]).filter_by(coin=self.coin).first()
            if not dep:
                continue
            dep.status = process.PROCESS_DEPOSIT_NOTIFY
            dep.tx_time = 0
            self.swaps[dep.iden] = Swap.copy(dep)

    @timeit
    def process_notify(self):
        t = int(time.time())
        finished_notifies = []
        try:
            best_block_height = self.service.best_block_number
        except Exception as e:
            return True

        for i, d in self.swaps.items():
            if d.tx_time is None:
                d.tx_time = 0
            if (t - d.tx_time) < self.setting['retry_interval']:
                continue
            if (best_block_height - d.block_height + 1) < self.setting['minconf']:
                continue

            d.tx_time = t
            try:
                import copy
                d1 = Swap.copy(d)
                d1.amount = self.rpc.from_wei(d1.amount)
                notify.notify_deposit(
                    d1, self.service.best_block_number, self.setting['feedback'])
            except Exception as e:
                logging.error('%s notify swap failed,%s,%s' %
                              (self.coin, e, d))
                continue

            d.iden = None
            d.status = process.PROCESS_DEPOSIT_NOTIFY
            db.session.add(d)
            db.session.commit()

            self.swaps[i] = Swap.copy(d)
            logging.info('%s notify swap success,%s' % (self.coin, d))
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
            coin=self.coin, tx_hash=swap['hash'],
            tx_index=swap['index'],
            output_index=swap.get('output_index')).first()
        if r:
            logging.info('swap already existed')
            return

        dep = Swap()
        dep.coin = self.coin
        dep.address = swap['to']
        dep.amount = swap['amount']
        dep.block_height = swap['height']
        dep.status = process.PROCESS_DEPOSIT_NEW
        dep.tx_hash = swap['hash']
        dep.tx_index = swap['index']
        dep.output_index = swap.get('output_index')
        dep.create_time = swap['time']
        db.session.add(dep)
        db.session.flush()
        # print(dep.tx_hash)
        db.session.commit()

        self.swaps[dep.iden] = Swap.copy(dep)

    @timeit
    def commit_swaps(self, swaps):
        for d in swaps:
            self.commit_swap(d)

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

        block = rpc.get_block_by_height(self.status)
        swaps = []
        for tx in block['txs']:
            existed = [x for x in self.addresses if rpc.is_swap(tx, x)]
            if len(existed):
                swaps.extend([tx])
                logging.info('new swap found, block height: {}, value: {}, to: {}'.format(
                    tx['blockNumber'], tx['value'], tx['to']))

        if len(block['txs']) > 0:
            logging.info(" > scan block {} : {} txs, {} swaps".format(
                self.status, len(block['txs']), len(swaps)))

        if swaps:
            logging.info('new swap found, %s' % swaps)

        for d in swaps:
            d['amount'] = d['value']
            d['height'] = int(d['blockNumber'])
        self.commit_swaps(swaps)

        if swaps or self.status % 50 == 0:
            s = db.session.query(Status).filter_by(coin=self.coin).first()
            if not s:
                s = Status()
                s.coin = self.coin
            s.height = self.status
            db.session.add(s)
            db.session.commit()

        self.status += 1
        return True

    def start(self):
        IBusiness.start(self)
        self.post(self.load_address)
        self.post(self.load_status)
        self.post(self.load_to_notify_swap)
        self.post(self.process_scan)
        self.post(self.process_notify)
