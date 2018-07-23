from . import db
import time


class Deposit(db.Model):
    __tablename__ = 'deposit'

    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # deposit_id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Numeric(64, 18), nullable=False)
    tx_hash = db.Column(db.String(256))
    tx_index = db.Column(db.Integer)
    output_index = db.Column(db.Integer)
    block_height = db.Column(db.Integer)
    tx_time = db.Column(db.Numeric(32))
    asset = db.Column(db.String(12))
    # new confirmed transferred committed
    status = db.Column(db.Integer, nullable=False)
    create_time = db.Column(db.Numeric(32), nullable=False)

    @classmethod
    def copy(cls, dep_):
        dep = Deposit()
        dep.iden = dep_.iden
        dep.address = dep_.address
        dep.amount = dep_.amount
        dep.tx_hash = dep_.tx_hash
        dep.tx_index = dep_.tx_index
        dep.output_index = dep_.output_index
        dep.block_height = dep_.block_height
        dep.tx_time = dep_.tx_time
        dep.asset = dep_.asset
        dep.status = dep_.status
        dep.create_time = dep_.create_time
        return dep


def create_deposit(address, amount, tx_hash, tx_index, output_index, block_height, tx_time, asset, status):
    dep = Deposit()
    dep.create_time = int(time.time() * 1000)
    dep.address = address
    dep.amount = amount
    dep.tx_hash = tx_hash
    dep.tx_index = tx_index
    dep.output_index = output_index
    dep.block_height = block_height
    dep.tx_time = tx_time
    dep.asset = asset
    dep.status = status
    return dep
