

class Base:
    def __init__(self, settings):
        self.settings = settings
        self.name = ''

    def get_balance(self, address):
        pass

    def is_deposit(self, tx, addresses):
        pass

    def get_transaction(self, txid):
        pass

    def best_block_number(self):
        pass

    def is_address_required(self):
        return True

    def transfer(self, from_, to_, amount):
        pass

    def start(self):
        pass

    def stop(self):
        pass
