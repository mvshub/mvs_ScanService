from . import db


class Status(db.Model):
    __tablename__ = 'status'
    iden = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asset = db.Column(db.String(12))
    height = db.Column(db.Integer)
