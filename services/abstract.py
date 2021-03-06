from services.iserver import IService
from utils import response
from functools import partial
from flask import request
import json
from utils.log.logger import Logger
from utils.parameter import parameter_check
import time
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


class AbstractService(IService):

    def __init__(self, app, rpcmanager, settings):
        IService.__init__(self, settings)
        self._default_interval = settings['interval']
        self._interval = 0
        self.rpcmanager = rpcmanager
        self.__tasks = []
        self.services = []
        self.app = app
        self.businesses = {}
        self.best_block_number = -1
        self.db_engine = create_engine(
            self.app.config['SQLALCHEMY_DATABASE_URI'])
        self.DBSession = scoped_session(
            sessionmaker(
                autoflush=True,
                autocommit=False,
                bind=self.db_engine
            )
        )

    def __init_app(self, app):

        for i, d in enumerate(self.settings['services']):
            if not d['enable']:
                continue
            for s in self.services:
                url = s['uri'] % d['coin']
                endpoint = s['name']
                Logger.get().info('route {}'.format(url))
                f = partial(
                    s['f'], self.rpcmanager.get_available_feed(d['rpc']))
                app.add_url_rule(rule=url, endpoint=endpoint,
                                 view_func=partial(f, d), methods=s['methods'])

    def work(self):
        while not self.stopped:
            try:
                old_tasks = self.__tasks
                new_tasks = []
                for t in old_tasks:
                    with self.app.app_context():
                        res = t()
                        if self.stopped:
                            break
                        if res:
                            new_tasks.append(t)
                while self.__tasks:
                    self.__tasks.pop(0)
                self.__tasks.extend(new_tasks)
                time.sleep(self.get_interval())
            except Exception as e:
                Logger.get().error('work exception, {}'.format(e))
                Logger.get().error('{}'.format(traceback.format_exc()))

    def post(self, f):
        self.__tasks.append(f)

    def get_interval(self):
        return self._interval if self._interval != 0 else self._default_interval

    def set_interval(self, interval):
        self._interval = interval

    def get_best_block_number(self, rpc):
        try:
            self.best_block_number = rpc.best_block_number()
        except Exception as e:
            pass
        return self.best_block_number

    def start_service(self):
        pass

    def start(self):

        self.stopped = False
        self.spawn(self.work)
        no_service = True
        for i, d in enumerate(self.settings['services']):
            if not d['enable']:
                continue

            no_service = False
            rpc = self.rpcmanager.get_available_feed(d['rpc'])
            self.get_best_block_number(rpc)
            self.post(partial(self.get_best_block_number, rpc))
        if no_service:
            self.stopped = True

        self.start_service()
        self.__init_app(self.app)

    def stop(self):
        self.stopped = True
