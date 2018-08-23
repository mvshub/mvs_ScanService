from services.ibusiness import IBusiness
from models import db
from models.constants import Status
from models.scan import Scan
from models.swap import Swap
from models.binder import Binder
from models.coin import Coin
from models.immature import Immature
from utils import response
from utils.timeit import timeit
import threading
import time
from utils.log.logger import Logger
from decimal import Decimal
from functools import partial
from models.swap_ban import Swap_ban
import json
from sqlalchemy import and_,or_

class ScanBusiness(IBusiness):

    def __init__(self, service, rpc, setting):
        IBusiness.__init__(self, service, rpc, setting)
        self.coin = setting['coin']
        self.scan_address = setting['scan_address']
        self.scan_initial_height = setting['scan_initial_height']
        self.scan_height = 0
        self.swaps = {}

        if not self.rpc.is_address_valid(self.scan_address):
            info = "invalid scan address: {}".format(self.scan_address)
            Logger.get().error(info)
            raise Exception(info)

    @timeit
    def load_status(self):
        s = db.session.query(Scan).filter_by(coin=self.coin).first()
        if not s:
            s = Scan()
            s.coin = self.coin
            s.height = self.scan_initial_height

            db.session.add(s)
            db.session.commit()
        self.scan_height = s.height

    @timeit
    def commit_swap(self, swap):
        r = db.session.query(Swap).filter_by(
            coin=self.coin, tx_hash=swap['hash']).first()
        if r:
            Logger.get().info('swap already existed')
            return

        item = Swap()
        item.coin = self.coin
        item.swap_address = swap['swap_address']
        item.to_address = swap['to']
        item.from_address = swap['from']
        item.token = swap['token']
        item.amount = swap['amount']
        item.fee = swap['fee']
        item.block_height = swap['height']
        item.tx_time = swap['time']
        item.tx_hash = swap['hash']
        item.tx_index = swap['index']
        item.output_index = swap.get('output_index')
        item.create_time = int(time.time() * 1000)
        item.status = int(Status.Swap_New)

        db.session.add(item)
        db.session.flush()
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
            Logger.get().info('binder already existed,from: %s, to: %s , tx_hash: %s' % (
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
    def commit_ban(self, tx_ban):
        item = db.session.query(Swap_ban).filter_by(tx_hash=tx_ban['hash']).first()
        if item:
            return
        item = Swap_ban()
        item.coin = self.coin
        item.swap_address = tx_ban['swap_address']
        item.to_address = tx_ban['to']
        item.from_address = tx_ban['from']
        item.token = tx_ban['token']
        item.amount = tx_ban['amount']
        item.fee = tx_ban['fee']
        item.block_height = tx_ban['height']
        item.tx_time = tx_ban['time']
        item.tx_hash = tx_ban['hash']
        item.tx_index = tx_ban['index']
        item.output_index = tx_ban.get('output_index')
        item.create_time = int(time.time() * 1000)
        item.message = tx_ban['message']
        
        db.session.add(item)
        db.session.commit()

    @timeit
    def commit_bans(self, bans):
        for bd in bans:
            self.commit_ban(bd)


    @timeit
    def commit_immature(self, tx_immature):
        item = db.session.query(Immature).filter_by(tx_hash=tx_immature['hash']).first()
        if item:
            return
        item = Immature()
        item.coin = self.coin
        item.block_hash = tx_immature['blockhash']
        item.block_height = tx_immature['blockNumber']
        item.tx_hash = tx_immature['hash']
        item.nonce = tx_immature['nonce']
        item.status = tx_immature['status']
        item.tx_result = json.dumps(tx_immature)

        db.session.add(item)
        db.session.commit()

    @timeit
    def commit_immatures(self, immatures):
        for i in immatures:
            self.commit_immature(i)
    

    @timeit
    def process_scan(self):
        rpc = self.rpc
        try:
            best_block_number = self.service.best_block_number
        except Exception as e:
            return True
        if (best_block_number - self.scan_height + 1) < self.setting['minconf']:
            return True

        block = rpc.get_block_by_height(self.scan_height, self.scan_address)
        swaps = []
        immatures = []
        binders = []
        bans = []
        for tx in block['txs']:
            if tx.get('isBinder', False) == True:
                binders.append(tx)
                Logger.get().info(' binder address, from:%s, to:%s' %
                                  (tx['from'], tx['to']))
            elif tx.get('ban', False) == True:
                bans.append(tx)
                Logger.get().info('new bans found: %s' % tx)
            elif rpc.is_swap(tx, self.scan_address):
                sts = rpc.verify_tx(tx)
                if sts == int(Status.Tx_Checked):
                    swaps.append(tx)
                    Logger.get().info('new swap found: %s' % tx)
                elif sts == int(Status.Tx_Unchecked):
                    tx['status'] = int(Status.Tx_Unchecked)
                    immatures.append(tx)
                    Logger.get().info('new immatures found: %s' % tx)
                elif sts == int(Status.Tx_Ban):
                    bans.append(tx)
                    Logger.get().info('new bans found: %s' % tx)

        for swap in swaps:
            swap['amount'] = swap['value']
            swap['height'] = int(swap['blockNumber'])

        self.commit_swaps(swaps)


        self.commit_immatures(immatures)

        for ban in bans:
            ban['amount'] = ban['value']
            ban['height'] = int(ban['blockNumber'])
        self.commit_bans(bans)

        for bd in binders:
            bd['height'] = int(bd['blockNumber'])
        self.commit_binders(binders)

        Logger.get().info("> scan {} block {} : {} txs, {} swaps, {} binders".format(
            self.coin, self.scan_height, len(block['txs']), len(swaps), len(binders)))

        if swaps or self.scan_height % 50 == 0:
            s = db.session.query(Scan).filter_by(coin=self.coin).first()
            if not s:
                s = Scan()
                s.coin = self.coin
            s.height = self.scan_height

            db.session.add(s)

            coins = rpc.get_coins()
            for c in coins:
                s = db.session.query(Coin).filter_by(
                    name=c.name, token=c.token).first()
                if s is None:
                    s = c
                s.block_height = self.scan_height
                s.total_supply = c.total_supply
                db.session.add(s)

            db.session.commit()

        self.scan_height += 1
        return True

    @timeit
    def process_immature(self):
        rpc = self.rpc
        results = db.session.query(Immature).filter(and_(
            Immature.coin == self.coin, Immature.status != int(Status.Tx_Unchecked))).all()

        if not results:
            return True
        
        for result in results:
            try:
                tx = json.loads(result.tx_result)
                sts = rpc.verify_tx(tx)
                if sts == int(Status.Tx_Checked):
                    tx['amount'] = tx['value']
                    tx['height'] = int(tx['blockNumber'])
                    self.commit_swap(tx)
                    result.status = int(Status.Tx_Checked)

                elif sts == int(Status.Tx_Ban):
                    Logger.get().info('new bans found: %s' % tx)
                    self.commit_swap(tx)
                    result.status = int(Status.Tx_Ban)

                db.session.add(result)
                db.session.commit()
            except Exception as e:
                Logger.get().info('exception occured while process immature, coin=%s, tx_hash=%s' % (result.coin ,result.tx_hash))
                continue

        return True

    def start(self):
        IBusiness.start(self)
        self.post(self.load_status)
        self.post(self.process_scan)
        self.post(self.process_immature)
