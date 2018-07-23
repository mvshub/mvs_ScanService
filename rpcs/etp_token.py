from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
from etp import Etp


class EtpToken(Etp):

    def __init__(self, settings):
        Etp.__init__(self, settings)
        self.name = settings['name']

    def get_balance(self, address):
        res = self.make_request('getaddressasset', [address])
        return res

    def to_wei(self, ether):
        return int(ether * 10.0**self.settings['decimal'])
        # return long(ether * 10.0**18)

    def from_wei(self, wei):
        return wei / decimal.Decimal(10.0**self.settings['decimal'])
