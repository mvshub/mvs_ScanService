from services.abstract import AbstractService
from utils import response
from modles import process, db
from modles.address import Address
import logging
from utils.timeit import timeit

MAX_ADDRESS_SIZE = 10

class AddressService(AbstractService):

    def __init__(self, app, rpcmanager, settings):
        AbstractService.__init__(self, app, rpcmanager, settings)

    def on_address_change(self, coin):
        pass

    def fill_new_address(self, rpc, setting):
        coin = rpc.name
        account = setting.get('account')
        passphrase = setting.get('passphrase')

        # get from database
        db_size = db.session.query(Address).filter_by(coin=coin).count()
        if db_size >= MAX_ADDRESS_SIZE:
            return False

        # generate new addresses
        addresses = rpc.get_addresses(account, passphrase)
        to_generate_size = MAX_ADDRESS_SIZE - len(addresses)

        for i in range(to_generate_size):
            try:
                if self.stopped:
                    return False
                addr = rpc.new_address(account, passphrase)
            except Exception as e:
                logging.error(
                    'failed to generate new address for %s,%s' % (rpc.name, e))

        # add to database
        addresses = rpc.get_addresses(account, passphrase)
        for address in addresses:
            exists = db.session.query(
                Address).filter_by(coin=coin, address=address).count()
            if exists:
                continue

            a = Address()
            a.coin = coin
            a.address = address
            a.inuse = 0
            db.session.add(a)
            db.session.commit()

        self.post(lambda: self.on_address_change(rpc.name))
        return True

    @timeit
    def process_get_address(self, rpc, setting):
        try:
            coin = rpc.name
            account = setting.get('account')
            passphrase = setting.get('passphrase')
            import time
            addr = Address.query.filter_by(coin=coin).first()
            t1 = time.time()
            if addr:
                addr.inuse = 1
                db.session.add(addr)
                db.session.flush()
                db.session.commit()
                new_address = addr.address
                t2 = time.time()
                a = Address.query.filter_by(iden=addr.iden).first()
                logging.info('process_get_address commit, %s' % (t2 - t1))
            else:
                t2 = time.time()
                new_address = rpc.new_address(account, passphrase)
                logging.info('newaddress cost, %s' % (t2 - t1))
                addr = Address()
                addr.inuse = 1
                addr.coin = rpc.name
                addr.address = new_address
                db.session.add(addr)
                db.session.commit()
                t1 = time.time()
                logging.info('newaddress cost, %s' % (t1 - t2))

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
