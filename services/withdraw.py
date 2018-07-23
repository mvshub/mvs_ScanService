from services.abstract import AbstractService
from utils import response
from functools import partial
from flask import request
import json
from utils.parameter import parameter_check
from modles import process, db
import time
from modles.withdraw import Withdraw
from modles.address import Address
import logging
from services.withdrawbusiness import WithdrawBusiness


class WithdrawService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)

    def process_post_withdraw(self, rpc, setting):
        try:
            logging.info('withdraw content,%s' % request.data)
            req = json.loads(request.data)
            parameter_check(req, {'withdraw_id': int, 'to': [
                            str, unicode], 'amount': [float, int]})
            if not rpc.is_address_valid(req['to']):
                return response.make_response(response.ERR_INVALID_ADDRESS)
            withdraw_id = req['withdraw_id']
            w = Withdraw.query.filter_by(
                withdraw_id=withdraw_id, asset=rpc.name).first()
            if w or rpc.name not in self.businesses:
                return response.make_response(response.ERR_WITHDRAW_EXISTED)
            wd_ = Withdraw()
            wd_.iden = None
            wd_.withdraw_id = withdraw_id
            wd_.address = req['to']
            wd_.amount = rpc.to_wei(req['amount'])
            wd_.asset = rpc.name
            wd_.status = process.PROCESS_NEW
            wd_.height = -1
            wd_.create_time = int(time.time())
            db.session.add(wd_)
            db.session.commit()
            # self.tasks[withdraw_id] = w
            self.businesses[wd_.asset].on_new_withdraw(Withdraw.copy(wd_))
        except Exception as e:
            return response.make_response(response.ERR_BAD_PARAMETER, '%s' % e)
        return response.make_response(result=req['withdraw_id'])

    def start_service(self):
        for d in self.settings['services']:
            if not d['enable']:
                continue
            b = WithdrawBusiness(
                self, self.rpcmanager.get_available_feed(d['rpc']), d)
            self.businesses[d['coin']] = b
            b.start()

        if not self.businesses:
            return

        # self.registe_service('/wallet/address/%s', partial(self.process_get_address, self.rpcmanager.get_available_feed(d['rpc'])), 'address')
        self.registe_service('/service/%s/withdraw',
                             self.process_post_withdraw, 'withdraw', ['POST'])

    def stop(self):
        AbstractService.stop(self)

    # def get_best_block_number(self, rpc):
    #     return False #remove this if best block number is not needed
