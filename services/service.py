from services.iserver import IService
from services.withdraw import WithdrawService
from services.deposit import DepositService
from utils import response
from flask import Flask, jsonify
from flask_migrate import Migrate, MigrateCommand
import sqlalchemy_utils
from modles import db
from rpcs.rpcmanager import RpcManager
from gevent.pywsgi import WSGIServer
from gevent import monkey
import logging


# need to patch sockets to make requests async
monkey.patch_all()


class WalletService(IService):

    def __init__(self, settings):
        self.app = None
        self.settings = settings
        self.rpcmanager = RpcManager(settings['rpcs'])

    def setup_db(self):
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://%s:%s@%s:%s/%s' % (
            self.settings['mysql_user'],
            self.settings['mysql_passwd'],
            self.settings['mysql_host'],
            self.settings['mysql_port'],
            self.settings['mysql_db'])
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
        self.app.config['extend_existing'] = True

        db.init_app(self.app)
        # migrate = Migrate(self.app, db)
        with self.app.app_context():
            # self.app.app_context().push()
            db.create_all()
        # manager.add_command('db', MigrateCommand)

    def start(self):
        self.app = Flask(__name__)

        # import os
        # if self.settings.get('privkey_path') is None \
        #     or not os.path.exists(self.settings.get('privkey_path')) \
        #     or self.settings.get('pubkey_path') is None \
        #     or not os.path.exists(self.settings.get('pubkey_path')):
        #     raise RuntimeError('failed to get public or private key path')

        # self.privkey = open(self.settings.get('privkey_path')).read()
        # self.pubkey = open(self.settings.get('pubkey_path')).read()
        # os.environ['privkey'] = self.privkey
        # os.environ['pubkey'] = self.pubkey

        @self.app.route('/')
        def root():
            return response.make_response(response.ERR_SUCCESS, 'TokenDroplet service')

        @self.app.errorhandler(404)
        def not_found(error):
            return response.make_response(response.ERR_SERVER_ERROR, '404: TokenDroplet service page not found')

        # @self.app.before_request
        # def before_request():
        #     from flask import request, abort
        #     from utils.crypto import verify

        #     if request.headers.get('signature') is None:
        #         abort(400)
        #         return
        #     s = request.headers['signature'].encode('utf8')
        #     if not verify(self.pubkey, request.path.encode('utf8'), s):
        #         logging.info('invalid signature')
        #         abort(400)

        # @self.app.after_request
        # def per_request_callbacks(response):
        #     from flask import g, make_response
        #     for func in getattr(g, 'call_after_request', ()):
        #         response = func(response)
        #     from utils.crypto import sign_data, encrypt

        #     if response.status_code == 200:
        #         data = response.data
        #         s = sign_data(self.privkey, data)
        #         data = encrypt(os.environ['pubkey'], data)
        #         resp = make_response(data)
        #         resp.headers['signature'] = s
        #         response = resp
        #     return response

        self.setup_db()
        self.rpcmanager.start()

        self.deposit = DepositService(
            self.app, self.rpcmanager, self.settings['deposits'])
        # self.withdraw = WithdrawService(self.app, self.rpcmanager, self.settings['withdraws'])
        self.deposit.start()
        # self.withdraw.start()

        self.http = WSGIServer(
            (self.settings['host'], self.settings['port']), self.app.wsgi_app)
        logging.info('server %s,%s' %
                     (self.settings['host'], self.settings['port']))
        self.http.serve_forever()

    def stop(self):
        if hasattr(self, 'http'):
            self.http.stop()
        if hasattr(self, 'deposit'):
            self.deposit.stop()
        if hasattr(self, 'withdraw'):
            self.withdraw.stop()
