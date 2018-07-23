from . import db


class Address(db.Model):
    __tablename__ = 'address'
    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    display = db.Column(db.String(128), unique=True)
    asset = db.Column(db.String(12))
    inuse = db.Column(db.Integer)
