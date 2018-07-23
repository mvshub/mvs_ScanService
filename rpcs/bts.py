from rpcs.base import Base
import requests
from utils.exception import RpcException, CriticalException
import json
import decimal
import websocket
from websocket import create_connection
from utils.decimal_encoder import DecimalEncoder
import time
# import StringIO
from io import BytesIO
import struct
from utils.base58 import Base58
import binascii
import hashlib
from Crypto.Cipher import AES
import ecdsa
import logging


def pack(f, val):
    while True:
        b = val & 0x7f
        val >>= 7
        b |= ((val > 0) << 7)
        f.write(chr(b))#.put(b)
        if not val:
            break


def is_transfer_transaction(tx):
    for o in tx['operations']:
        if o[0] != 0:
            return False
    return True


def get_transaction_id(tx, prefix_base):
    # f = StringIO.StringIO()
    f = BytesIO()
    s = struct.pack('<H', tx['ref_block_num'])
    # print(binascii.hexlify(s))
    f.write(s)
    s = struct.pack('<I', tx['ref_block_prefix'])
    # print(binascii.hexlify(s))
    f.write(s)
    import time
    t = time.strptime(tx['expiration'], "%Y-%m-%dT%H:%M:%S")
    seconds = int(time.mktime(t))
    if time.tzname[0] == 'CST':
        seconds += 28800
    elif time.tzname[0] == 'UTC':
        seconds += 0
    else:
        raise RuntimeError('invalid time zone')
    s = struct.pack('<I', seconds)
    # print(binascii.hexlify(s))
    f.write(s)
    val = len(tx['operations'])
    pack(f, val)
    for o in tx['operations']:
        if o[0] != 0:
            raise RuntimeError('bad operation type')
        op = o[1]
        f.write(chr(0)) #transfer operation
        s = struct.pack('<Q', int(op['fee']['amount']))
        l = len(s)
        # print(binascii.hexlify(s))
        f.write(s)
        val = int(op['fee']['asset_id'][len('1.3.'):])
        pack(f, val)
        val = int(op['from'][len('1.2.'):])
        pack(f, val)
        val = int(op['to'][len('1.2.'):])
        pack(f, val)
        try:
            s = struct.pack('<Q', op['amount']['amount'])
            f.write(s)
        except Exception as e:
            val = int(op['amount']['amount'])
            pack(f, val)
        # print(binascii.hexlify(s))
        # f.write(s)
        val = int(op['amount']['asset_id'][len('1.3.'):])
        pack(f, val)

        if op.get('memo') is not None:
            s = struct.pack('<B', 1)
            f.write(s)
            prefix_base = op['memo']['from'][:3]
            from_ = Base58(op['memo']['from'], prefix_base)
            s = repr(from_)
            s = binascii.unhexlify(s)
            f.write(s)
            prefix_base = op['memo']['to'][:3]
            to_ = Base58(op['memo']['to'], prefix_base)
            s = binascii.unhexlify(repr(to_))
            f.write(s)
            s = struct.pack('<Q', int(op['memo']['nonce']))
            f.write(s)
            s = binascii.unhexlify(op['memo']['message'])
            pack(f, len(s))
            f.write(s)
            pack(f, 0)
            pack(f, 0)
        sha = hashlib.sha256()
        # print(binascii.hexlify(f.getvalue()))
        sha.update(f.getvalue())
        res = sha.digest()
        res = res[:20]
        res = binascii.hexlify(res)
        # print(res)
        # if res == 'd617c883f845e56234ab627f7a9e2180eeef09a1':
        #     print('fuck=============================')
        return res


if __name__ == '__main__':
    tx = {
      "ref_block_num": 61992,
      "ref_block_prefix": 1212457831,
      "expiration": "2017-11-04T07:39:55",
      "operations": [[
          0,{
            "fee": {
              "amount": 24079,
              "asset_id": "1.3.0"
            },
            "from": "1.2.356919",
            "to": "1.2.179737",
            "amount": {
              "amount": 26123,
              "asset_id": "1.3.121"
            },
            "memo": {
              "from": "BTS514Q3hah5TTq2WMUyjPN9ZBV1gcjcDmCKr9gYMhkYKjePKw1ss",
              "to": "BTS5dCrVrqYYQir5PR83ywEPwkS7ofdJZKrPqT5Pu6NeWet9puXhE",
              "nonce": "386503981978336",
              "message": "17f641eaba2185d5b77ade107e8f6aef0d1a6ff543c9782bfad409b76e7223fe72c62871d6330c5f30330c32aa925f3e1e51013d721f38b523aedaf24a489d579341e3ba87412ba346d992fef24df52e6c8357fb9a897bb629f934e33da3773828991dac649450478de8fda4ab92d170"
            },
            "extensions": []
          }
        ]
      ],
      "extensions": [],
      "signatures": [
        "206b615d71c6161498a81e630604d1179bf46d5d0f8e46e0ac51305ded29ee31326f93e8b477aaee51986c47b28478ba776d54e4ad20b888f5b20be79b69584b3e"
      ],
      "operation_results": [[
          0,{}
        ]
      ]
    }
    get_transaction_id(tx, 'BTS')


def decode_memo(priv, pub, nonce, message, prefix_base):
    priv = Base58(priv, prefix_base)
    pk = Base58(pub, prefix_base)
    public_key = repr(pk)
    prefix = public_key[0:2]
    if prefix == "04":
        return public_key
    assert prefix == "02" or prefix == "03"
    x = int(public_key[2:], 16)
    curve = ecdsa.SECP256k1.curve
    a, b, p = curve.a(), curve.b(), curve.p()
    alpha = (pow(x, 3, p) + a * x + b) % p
    beta = ecdsa.numbertheory.square_root_mod_prime(alpha, p)
    if (beta % 2) == (prefix == "02"):
        beta = p - beta
    y = beta

    key = '04' + '%064x' % x + '%064x' % y
    string = binascii.unhexlify(key)
    pub_point = ecdsa.VerifyingKey.from_string(string[1:], curve=ecdsa.SECP256k1).pubkey.point



    priv_point = int(repr(priv), 16)
    res = pub_point * priv_point
    res_hex = '%032x' % res.x()
    # Zero padding
    shared_secret = '0' * (64 - len(res_hex)) + res_hex
    ss = hashlib.sha512(binascii.unhexlify(shared_secret)).digest()
    " Seed "
    seed = str(nonce) + binascii.hexlify(ss)
    seed_digest = binascii.hexlify(hashlib.sha512(seed).digest()).decode('ascii')
    " AES "
    key = binascii.unhexlify(seed_digest[0:64])
    iv = binascii.unhexlify(seed_digest[64:96])
    aes = AES.new(key, AES.MODE_CBC, iv)
    raw = message
    cleartext = aes.decrypt(binascii.unhexlify(raw))

    message = cleartext[4:]
    # return _unpad(message.decode('utf8'), 16)
    # s = message.decode('utf8')
    s = message
    count = int(struct.unpack('B', s[-1])[0])
    if s[-count::] == count * struct.pack('B', count):
        return s[:-count]
    return s


class Bts(Base):
    def __init__(self, settings):
        Base.__init__(self, settings)
        self.name = settings['name']
        self.decimal = settings['decimal']
        self.common_address_id = ''
        self.__prefix_base = 'GXC' if self.name == 'GXS' else 'BTS'

    def create_websocket(self):
        uri = '%s://%s:%s/ws' % ('wss' if self.settings['witness_ssl'] else 'ws', self.settings['witness_host'], self.settings['witness_port'])
        self.conn = create_connection(uri)

    def __get_account_by_name(self, name):
        acc = self.make_request('get_account_by_name', [name])
        return acc

    def __get_asset_by_name(self, name):
        ass = self.make_request('lookup_asset_symbols', [[name]])
        return ass
    def _setup(self, setup=False):
        data_base_id = self.make_request('database', api_id=1, setup=setup)
        history_id = self.make_request('history', api_id=1, setup=setup)
        network_id = self.make_request('network_broadcast', api_id=1, setup=setup)

    def _init(self):
        self.common_address_id = self.__get_account_by_name(self.settings['common-address'])
        if not self.common_address_id:
            raise RuntimeError('not account found for %s' % self.settings['common-address'])
        self.common_address_id = self.common_address_id['id']
        self.asset_id = self.__get_asset_by_name(self.name)
        if not self.asset_id[0]:
            raise RuntimeError('not asset for %s' % self.name)
        self.asset_id = self.asset_id[0]['id']

    def start(self):
        self.create_websocket()
        self._setup()
        self._init()
        self.best_block_number()
        return True

    def stop(self):
        return False

    def make_request(self, method, params=[], api_id=0, setup=False):
        res = json.dumps({'method':'call', 'params':[api_id, method, params], "id":1}, cls=DecimalEncoder)
        for i in range(10):
            try:
                if not self.conn:
                    raise RpcException('')
                self.conn.send(res)
                try:
                    res = self.conn.recv()
                    break
                except websocket.WebSocketConnectionClosedException as e:
                    raise RpcException('%s' % e)
            except Exception as e:
                if setup:
                    raise RpcException('failed to request when setting up,%s,%s,%s' % (method, params, e))
                logging.error('failed to request,%s,%s, %s' % (method, params, e) )
                time.sleep(1)
                try:
                    self.create_websocket()
                except Exception as e:
                    logging.error('failed to connect,%s' % self.settings['witness_host'])
                    time.sleep(5)
                    continue
                self._setup(True)

        try:
            res = json.loads(res)
            if isinstance(res, dict) and res.get('error') is not None:
                raise RpcException(res['error']['message'])
        except ValueError as e:
            raise RpcException('bad response,%s' % res)
        return res['result']

    def get_balance(self, address):
        res = self.make_request('fetch-balance', [address])
        return res

    def get_block_by_height(self, height):
        # height = 5019219 # for gxs
        # height = 23465411
        block = self.make_request('get_block', [height])
        if not block:
            return {'txs':[]}
        txs = []
        for tx in block['transactions']:
            if not is_transfer_transaction(tx):
                continue
            tx_hash = get_transaction_id(tx, self.__prefix_base)
            for i, o in enumerate(tx['operations']):
                op = o[1]
                if op['to'] != self.common_address_id:
                    continue
                if op['amount']['asset_id'] != self.asset_id:
                    continue
                t = {}
                to_address = ''
                if op.get('memo') is not None:
                    prefix_base = op['memo']['from'][:3]
                    to_address = decode_memo(self.settings['wifkey'], op['memo']['from'], op['memo']['nonce'], op['memo']['message'], prefix_base)
                t['to'] = to_address
                t['blockNumber'] = height
                t['value'] = op['amount']['amount']
                t['asset_id'] = op['amount']['asset_id']
                t['hash'] = tx_hash
                t['index'] = i
                t['time'] = int(time.time())

                txs.append(t)
        block['txs'] = txs
        return block

    def is_deposit(self, tx, addresses):
        if tx['to'] in addresses:
            return True
        return False

    def get_transaction(self, txid):
        res = self.make_request('gettransaction', [txid])
        return res

    # def is_address_required(self):
    #     return False

    def new_address(self, account, passphase):
        import uuid
        return uuid.uuid1().hex

    def best_block_number(self):
        res = self.make_request('get_dynamic_global_properties')
        return res['last_irreversible_block_num']

    def to_wei(self, ether):
        return int(ether*10.0**self.settings['decimal'])
        # return long(ether * 10.0**18)

    def from_wei(self, wei):
        return wei/decimal.Decimal(10.0)**decimal.Decimal(self.settings['decimal'])
