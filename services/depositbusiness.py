from decimal import Decimal

from services.address import AddressService
import threading
import time
import logging
from functools import partial
from modles import process
from modles.status import Status
from modles import db
from utils import response
from modles.deposit import Deposit
from modles.address import Address
from utils import notify
from utils.timeit import timeit
from services.ibusiness import IBusiness


class DepositBusiness(IBusiness):

    def __init__(self, service, rpc, setting):
        IBusiness.__init__(self, service, rpc, setting)
        self.coin = setting['coin']
        self.addresses = set()
        self.status = 0
        self.deposits = {}

    @timeit
    def load_to_notify_deposit(self):
        ids = db.session.query(Deposit.tx_hash, Deposit.tx_index, Deposit.output_index).group_by(
            Deposit.tx_hash, Deposit.tx_index, Deposit.output_index).having(db.func.count(Deposit.status) == 1).all()

        for id_ in ids:
            dep = db.session.query(Deposit).filter_by(
                tx_hash=id_[0], tx_index=id_[1], output_index=id_[2]).filter_by(asset=self.coin).first()
            if not dep:
                continue
            dep.status = process.PROCESS_DEPOSIT_NOTIFY
            dep.tx_time = 0
            self.deposits[dep.iden] = Deposit.copy(dep)

    @timeit
    def process_notify(self):
        t = int(time.time())
        finished_notifies = []
        try:
            best_block_height = self.service.best_block_number
        except Exception as e:
            return True

        for i, d in self.deposits.items():
            if d.tx_time is None:
                d.tx_time = 0
            if (t - d.tx_time) < self.setting['retry_interval']:
                continue
            if (best_block_height - d.block_height + 1) < self.setting['minconf']:
                continue

            d.tx_time = t
            try:
                import copy
                d1 = Deposit.copy(d)
                d1.amount = self.rpc.from_wei(d1.amount)
                notify.notify_deposit(
                    d1, self.service.best_block_number, self.setting['feedback'])
            except Exception as e:
                logging.error('%s notify deposit failed,%s,%s' %
                              (self.coin, e, d))
                continue

            d.iden = None
            d.status = process.PROCESS_DEPOSIT_NOTIFY
            db.session.add(d)
            db.session.commit()
            self.deposits[i] = Deposit.copy(d)
            logging.info('%s notify deposit success,%s' % (self.coin, d))
            finished_notifies.append(i)

        for i in finished_notifies:
            self.deposits.pop(i)
        return True

    @timeit
    def load_status(self):
        s = db.session.query(Status).filter_by(asset=self.coin).first()
        if not s:
            s = Status()
            s.asset = self.coin
            s.height = 1
            db.session.add(s)
            db.session.commit()
        self.status = s.height

    @timeit
    def load_address(self):
        addresses = db.session.query(Address).filter_by(
            asset=self.coin, inuse=1).all()
        self.addresses.update([a.display for a in addresses])
        for a in addresses:
            logging.info("load addresses: {}".format(a.display))

    @timeit
    def on_address_change(self):
        self.post(self.load_address)

    @timeit
    def process_deposits(self):
        pass

    @timeit
    def commit_deposit(self, deposit):
        r = db.session.query(Deposit).filter_by(
            asset=self.coin, tx_hash=deposit['hash'],
            tx_index=deposit['index'],
            output_index=deposit.get('output_index')).first()
        if r:
            logging.info('deposit already existed')
            return

        dep = Deposit()
        dep.asset = self.coin
        dep.address = deposit['to']
        dep.amount = deposit['amount']
        dep.block_height = deposit['height']
        dep.status = process.PROCESS_DEPOSIT_NEW
        dep.tx_hash = deposit['hash']
        dep.tx_index = deposit['index']
        dep.output_index = deposit.get('output_index')
        dep.create_time = deposit['time']
        db.session.add(dep)
        db.session.flush()
        # print(dep.tx_hash)
        db.session.commit()

        self.deposits[dep.iden] = Deposit.copy(dep)

    @timeit
    def commit_deposits(self, deposits):
        for d in deposits:
            self.commit_deposit(d)

    @timeit
    def process_deposit(self):
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
        deposits = []
        for tx in block['txs']:
            existed = [x for x in self.addresses if rpc.is_deposit(tx, x)]
            if len(existed):
                deposits.extend([tx])
                logging.info('new deposit found, block height: {}, value: {}, to: {}'.format(
                    tx['blockNumber'], tx['value'], tx['to']))

        if len(block['txs']) > 0:
            logging.info(" > scan block {} : {} txs, {} deposits".format(
                self.status, len(block['txs']), len(deposits)))

        if deposits:
            logging.info('new deposit found, %s' % deposits)

        for d in deposits:
            d['amount'] = d['value']
            d['height'] = int(d['blockNumber'])
        self.commit_deposits(deposits)

        if deposits or self.status % 50 == 0:
            s = db.session.query(Status).filter_by(asset=self.coin).first()
            if not s:
                s = Status()
                s.asset = self.coin
            s.height = self.status
            db.session.add(s)
            db.session.commit()

        self.status += 1
        return True

    def start(self):
        IBusiness.start(self)
        self.post(self.load_address)
        self.post(self.load_status)
        self.post(self.load_to_notify_deposit)
        self.post(self.process_deposit)
        self.post(self.process_notify)
