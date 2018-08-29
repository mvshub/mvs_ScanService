from services.iserver import IService
from services.scan import ScanService
from rpcs.rpcmanager import RpcManager
from utils import response
from utils.log.logger import Logger
from flask import Flask, jsonify
import sqlalchemy_utils
from models import db
from gevent.pywsgi import WSGIServer
from gevent import monkey
import time


# need to patch sockets to make requests async
monkey.patch_all()


class MainService(IService):

    def __init__(self, settings):
        self.app = None
        self.settings = settings
        self.rpcmanager = RpcManager(settings['rpcs'], settings['tokens'])

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
        with self.app.app_context():
            db.create_all()

    def start(self):
        self.app = Flask(__name__)

        @self.app.route('/')
        def root():
            return response.make_response(response.ERR_SUCCESS, 'TokenDroplet service')

        @self.app.errorhandler(404)
        def not_found(error):
            return response.make_response(response.ERR_SERVER_ERROR, '404: TokenDroplet service page not found')

        self.setup_db()
        self.rpcmanager.start()

        # start scan service
        self.scan = ScanService(
            self.app, self.rpcmanager, self.settings['scans'])
        self.scan.start()

        # do not exit the main thread
        self.stopped = False
        while not self.stopped:
            time.sleep(1)

    def stop(self):
        self.stopped = True
        if hasattr(self, 'scan'):
            self.scan.stop()
