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
from modles.withdraw import Withdraw
from utils.exception import SendingWithdrawException


class WithdrawBusiness(IBusiness):

    def __init__(self, service, rpc, setting):
        IBusiness.__init__(self, service, rpc, setting)
        self.coin = setting['coin']
        self.tasks = {}
        self.retry_interval = 60 * \
            5 if setting.get('retry_interval') is None else setting[
                'retry_interval']

    def on_new_withdraw(self, w):
        self.tasks[w.iden] = w

    def load_new_withdraw(self):
        ids = db.session.query(Withdraw.withdraw_id).group_by(
            Withdraw.withdraw_id).having(db.func.count(Withdraw.status) == 1).filter_by(asset=self.coin).all()
        ids = [i[0] for i in ids]
        if not ids:
            return
        deps = db.session.query(Withdraw).filter(Withdraw.withdraw_id.in_(
            ids)).filter_by(asset=self.coin, status=process.PROCESS_NEW).all()
        for d in deps:
            self.tasks[d.iden] = Withdraw.copy(d)

    def load_sending_withdraw(self):
        ids = db.session.query(Withdraw.withdraw_id).group_by(
            Withdraw.withdraw_id).having(db.func.count(Withdraw.status) == 2).filter_by(asset=self.coin).all()
        ids = [i[0] for i in ids]
        if not ids:
            return
        deps = db.session.query(Withdraw).filter(Withdraw.withdraw_id.in_(
            ids)).filter_by(asset=self.coin, status=process.PROCESS_SENDING).all()
        if deps:
            txt = '%s sending state withdraws(%s) found, their ids are %s ' % (
                len(deps), self.coin, [i.iden for i in deps])
            raise SendingWithdrawException(txt)

    def load_sent_withdraw(self):
        ids = db.session.query(Withdraw.withdraw_id).group_by(
            Withdraw.withdraw_id).having(db.func.count(Withdraw.status) == 3).filter_by(asset=self.coin).all()
        ids = [i[0] for i in ids]
        if not ids:
            return
        deps = db.session.query(Withdraw).filter(Withdraw.withdraw_id.in_(
            ids)).filter_by(asset=self.coin, status=process.PROCESS_SENT).all()
        for d in deps:
            self.tasks[d.iden] = Withdraw.copy(d)

    def process_new_withdraw(self, t):
        try:
            now = int(time.time())
            if (now - t.create_time) < self.retry_interval:
                return True
            ws = db.session.query(Withdraw).filter_by(
                iden=t.iden, asset=t.asset).all()
            if not ws:
                return True

            if len(ws) != 1 or ws[0].status != process.PROCESS_NEW:
                logging.error('impossible withdraw %s' % t)
                return

            w = ws[0]
            w = Withdraw.copy(w)
            balance = self.rpc.get_balance(self.setting['from_address'])
            if balance < w.amount:
                logging.error('balance is not enough,%s' %
                              self.rpc.from_wei(balance))
                return True

            w.iden = None
            w.status = process.PROCESS_SENDING
            db.session.add(w)
            db.session.commit()
            t.status = process.PROCESS_SENDING
            w = Withdraw.copy(w)
            res, fee = self.rpc.transfer(self.setting['passphrase'], self.setting[
                                         'from_address'], w.address, w.amount)
            w.iden = None
            w.status = process.PROCESS_SENT
            w.fee = fee
            w.tx_hash = res
            db.session.add(w)
            db.session.commit()
            t.tx_hash = res
            t.create_time = 0
            t.status = process.PROCESS_SENT
            return True
        except Exception as e:
            logging.error('process new withdraw failed,%s' % e)
        return False

    def process_new_withdraws(self):
        to_removes = []
        try:
            for k, t in self.tasks.items():
                if t.status != process.PROCESS_NEW:
                    continue
                is_ok = self.process_new_withdraw(t)
                if not is_ok:
                    to_removes.append(k)
        except Exception as e:
            logging.error('process new withdraws failed,%s' % e)
        while to_removes:
            k = to_removes.pop(0)
            self.tasks.pop(k)
        return True

    def process_notify_withdraw(self, block_height, t):
        now = int(time.time())
        try:
            if not t.height or t.height < 0:
                res = self.rpc.get_transaction(t.tx_hash)
                if not res or not res['blockNumber'] or res['blockNumber'] < 0:
                    return
                t.height = res['blockNumber']
                return

            if (now - t.create_time) > 100 and (block_height - t.height + 1) > self.setting['minconf']:
                from utils.notify import notify_withdraw
                t.create_time = now
                notify_withdraw(t, self.setting['feedback'])
                t1 = Withdraw.copy(t)
                t1.iden = None
                t1.status = process.PROCESS_NOTIFY
                db.session.add(t1)
                db.session.commit()
                return True

        except Exception as e:
            logging.error('process notify withdraw failed,%s' % e)
        return False

    def process_notify_withdraws(self):
        to_removes = []
        try:
            block_height = self.service.best_block_number
            for k, t in self.tasks.items():
                if t.status != process.PROCESS_SENT:
                    continue
                is_notified = self.process_notify_withdraw(block_height, t)
                if is_notified:
                    to_removes.append(k)
        except Exception as e:
            logging.error('process new withdraws failed,%s' % e)
        while to_removes:
            k = to_removes.pop(0)
            self.tasks.pop(k)
        return True

    def start(self):
        IBusiness.start(self)
        self.post(self.load_sent_withdraw)
        self.post(self.load_sending_withdraw)
        self.post(self.load_new_withdraw)
        self.post(self.process_new_withdraws)
        self.post(self.process_notify_withdraws)
