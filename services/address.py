from services.abstract import AbstractService
from utils import response
from modles import process, db
from modles.address import Address
import logging
from utils.timeit import timeit


class AddressService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)

    def on_address_change(self, coin):
        pass

    def fill_new_address(self, rpc, setting):
        coin = rpc.name
        address_size = db.session.query(
            Address).filter_by(asset=coin, inuse=0).count()
        to_generate_size = 10 - address_size
        if to_generate_size <= 0:
            return
        account = setting.get('account')
        passphrase = setting.get('passphrase')
        for i in range(to_generate_size):
            try:
                if self.stopped:
                    return False
                addr = rpc.new_address(account, passphrase)
                a = Address()
                a.asset = rpc.name
                a.display = addr
                a.inuse = 0
                db.session.add(a)
                db.session.commit()
            except Exception as e:
                logging.error(
                    'failed to generate new address for %s,%s' % (rpc.name, e))
        self.post(lambda: self.on_address_change(rpc.name))
        return False

    @timeit
    def process_get_address(self, rpc, setting):
        try:
            import time
            # print('get address')
            # time.sleep(10)
            # if not rpc.is_address_required():
            # return
            # response.make_response(result=rpc.new_address(setting.get('account'),
            # setting.get('passphrase')))
            addr = Address.query.filter_by(asset=rpc.name, inuse=0).first()
            t1 = time.time()
            if addr:
                addr.inuse = 1
                db.session.add(addr)
                db.session.flush()
                db.session.commit()
                new_address = addr.display
                t2 = time.time()
                a = Address.query.filter_by(iden=addr.iden).first()
                logging.info('process_get_address commit,%s' % (t2 - t1))
            else:
                t2 = time.time()
                new_address = rpc.new_address(setting.get(
                    'account'), setting.get('passphrase'))
                logging.info('newaddress cost,%s' % (t2 - t1))
                addr = Address()
                addr.inuse = 1
                addr.asset = rpc.name
                addr.display = new_address
                db.session.add(addr)
                db.session.commit()
                t1 = time.time()
                logging.info('newaddress cost,%s' % (t1 - t2))
            self.post(lambda: self.fill_new_address(rpc, setting))
        except Exception as e:
            return response.make_response(response.ERR_BAD_PARAMETER, '%s' % e)
        return response.make_response(result=new_address)

    def start_service(self):
        for d in self.settings['services']:
            if not d['enable']:
                continue
            from functools import partial
            self.post(partial(self.fill_new_address,
                              self.rpcmanager.get_available_feed(d['rpc']), d))
        self.registe_service('/service/%s/address',
                             self.process_get_address, 'address')

    def stop(self):
        AbstractService.stop(self)
