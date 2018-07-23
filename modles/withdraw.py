from . import db
import time


class Withdraw(db.Model):
    __tablename__ = 'withdraw'
    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    withdraw_id = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Numeric(64, 16), nullable=False)
    height = db.Column(db.Integer)
    from_ = db.Column(db.String(128))
    tx_hash = db.Column(db.String(256))
    tx_time = db.Column(db.Numeric(32))
    # fee = db.Column(db.NUMERIC(64, 16))
    asset = db.Column(db.String(12), nullable=False)
    # new sent confirmed committed
    status = db.Column(db.Integer, nullable=False)
    create_time = db.Column(db.Numeric(32), nullable=False)

    @classmethod
    def copy(cls, wd_):
        wd = Withdraw()
        wd.iden = wd_.iden
        wd.withdraw_id = wd_.withdraw_id
        wd.address = wd_.address
        wd.amount = wd_.amount
        wd.height = wd_.height
        wd.from_ = wd_.from_
        wd.tx_hash = wd_.tx_hash
        wd.tx_time = wd_.tx_time
        # wd.fee = wd_.fee
        wd.asset = wd_.asset
        wd.status = wd_.status
        wd.create_time = wd_.create_time
        return wd


def create_withdraw(withdraw_id, asset_, address_, amount_, status_, tx_hash=None, tx_index=None, tx_time=None):
    wd = Withdraw()
    wd.withdraw_id = withdraw_id
    wd.asset = asset_
    wd.address = address_
    wd.amount = amount_
    wd.create_time = int(time.time())
    wd.status = status_
    return wd
