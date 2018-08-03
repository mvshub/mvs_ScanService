import decimal


class Base:

    def __init__(self, settings):
        self.settings = settings
        self.name = ''

    def is_swap(self, name, tx, addresses):
        pass

    def is_address_valid(self, address):
        return address is not None and address != ''

    def get_transaction(self, txid):
        pass

    def get_total_supply(self, token_name=None):
        pass

    def best_block_number(self):
        pass

    def get_coins(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_decimal(self, token):
        return 0

    def to_wei(self, token, amount):
        dec = self.get_decimal(token)
        return long(amount * decimal.Decimal(10.0**dec))

    def from_wei(self, token, wei):
        dec = self.get_decimal(token)
        return decimal.Decimal(wei) / decimal.Decimal(10.0**dec)
