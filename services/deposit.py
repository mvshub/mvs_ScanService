from services.address import AddressService
import logging
from utils import response
from modles.deposit import Deposit
from services.depositbusiness import DepositBusiness
from modles import process
from modles import db


class DepositService(AddressService):

    def __init__(self, app, rpcmanager, settings):
        AddressService.__init__(self, app, rpcmanager, settings)
        self.businesses = {}

    def on_address_change(self, coin):
        try:
            self.businesses[coin].on_address_change()
        except Exception as e:
            logging.error('on address change failed,%s' % e)

    def process_get_transaction(self, rpc, setting, txid):
        try:
            res = rpc.get_transaction(txid)
        except Exception as e:
            return response.make_response(response.ERR_BAD_PARAMETER, '%s' % e)
        return response.make_response(result=res)

    def process_get_deposit(self, rpc, setting, address, page, limit=10):
        if not rpc.is_address_valid(address):
            return response.make_response(response.ERR_INVALID_ADDRESS)
        ds = db.session.query(Deposit).filter_by(
            address=address, asset=rpc.name,
            status=process.PROCESS_DEPOSIT_NEW).limit(limit).offset(page * limit).all()
        ds = [{'deposit_id': d.iden, 'asset': d.asset, 'amount': d.amount,
               'to_address': d.address, 'txid': d.tx_hash, 'height': d.block_height} for d in ds]
        return response.make_response(result=ds)

    def process_get_block_height(self, rpc, setting):
        return response.make_response(result=self.best_block_number)

    def process_get_minconf(self, rpc, setting):
        return response.make_response(result=setting['minconf'])

    def process_get_all_minconf(self, rpc, setting):
        import json
        settings = json.loads(open('config/service.json').read())
        res = {'min-conf': []}
        for setting in settings['deposits']['services']:
            res['min-conf'].append({'coin': setting['coin'],
                                    'height': setting['minconf']})
        return response.make_response(result=res)

    def process_get_tx_status(self, rpc, setting, txHash):
        try:
            tx = rpc.get_transaction(txHash)
            best_block_height = rpc.best_block_number()
            db_tx = db.session.query(Deposit).filter_by(
                tx_hash=tx['hash']).order_by(Deposit.status).limit(1).all()
            if len(db_tx) == 0:
                raise RuntimeError('Cant find identified tx')
            else:
                db_tx = db_tx[0]
        except Exception as e:
            return response.make_response(response.ERR_BAD_PARAMETER, '%s' % e)
        res = {'process': '', 'txid': txHash, 'amount': db_tx.amount,
               'address': db_tx.address, 'processTime': db_tx.create_time}
        curHgt = best_block_height - int(tx['blockNumber'])
        if curHgt > int(setting['minconf']):
            res['process'] = '-'
        else:
            res['process'] = '%d/%s' % (curHgt, setting['minconf'])
        return response.make_response(result=res)

    def start_service(self):
        AddressService.start_service(self)
        for d in self.settings['services']:
            if not d['enable']:
                continue
            logging.info(
                "start DepositBusiness for {} with setting {}".format(d['coin'], d))
            b = DepositBusiness(
                self, self.rpcmanager.get_available_feed(d['rpc']), d)
            self.businesses[d['coin']] = b
            b.start()

        if not self.businesses:
            return

        self.registe_service('/service/%s/block/number',
                             self.process_get_block_height, 'block_number')
        self.registe_service('/service/%s/tx/<txid>',
                             self.process_get_transaction, 'tx')
        self.registe_service('/service/%s/deposit/tx/<txHash>/status',
                             self.process_get_tx_status, "get_tx_status")
        self.registe_service('/service/%s/deposit/<address>/<int:page>/<int:limit>',
                             self.process_get_deposit, 'deposit')
        self.registe_service('/service/%s/deposit/<address>/<int:page>',
                             self.process_get_deposit, 'deposit_default_page')
        self.registe_service('/service/%s/min/confirm',
                             self.process_get_minconf, "minconf")
        self.registe_service('/service/%s/all/min/confirm',
                             self.process_get_all_minconf, "all_minconf")

    def stop(self):
        AddressService.stop(self)

    # def get_best_block_number(self, rpc):
    #     return False #remove this if best block number is not needed
