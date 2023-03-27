from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker
import os

Base = declarative_base()

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_type = Column(String)
    symbol = Column(String)
    stock_name = Column(String)
    stock_price = Column(Numeric)
    no_of_shares = Column(Integer)
    total = Column(Numeric)
    transacted = Column(DateTime)
    user = relation('Users', backref="users")
    p_l = Column(Float)

    def __init__(
            self,
            user_id=None,
            transaction_type=None,
            symbol=None,
            stock_name=None,
            stock_price=None,
            no_of_shares=None,
            total=None,
            transacted=None,
            p_l=None):
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.symbol = symbol
        self.stock_name = stock_name
        self.stock_price = stock_price
        self.no_of_shares = no_of_shares
        self.total = total
        self.transacted = transacted
        self.p_l = p_l

    def __repr__(self):
        return "History(%r, %r, %r)" % (self.username, self.transaction_type, self.symbol)


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    hash = Column(String, nullable=False)
    cash = Column(Float, default=10000)
    email = Column(String, unique=True)

    def __init__(self, username=None, hash=None, email=None):
        self.username = username
        self.hash = hash
        self.email = email

    def __repr__(self):
        return "User(%r, %r)" % (self.username, self.hash)


class Holdings(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    stock_name = Column(String)
    average_price = Column(Float)
    symbol = Column(String)
    total = Column(Float)
    shares = Column(Integer)

    def __init__(self, user_id=None, symbol=None, stock_name=None, average_price=None, shares=None, total=None):
        self.user_id = user_id
        self.symbol = symbol
        self.stock_name = stock_name
        self.average_price = average_price
        self.shares = shares
        self.total = total

    def __repr__(self):
        return "User(%r, %r, %r)" % (self.username, self.shares, self.average_price)


engine = create_engine(os.environ.get('DB_URL'), echo=True)

Base.metadata.create_all(engine)

