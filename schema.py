from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker
from schema import Users, History
from datetime import  datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, sessionmaker
engine = create_engine("postgresql://postgres:mrlonely@database-1.conyko6usosg.us-east-1.rds.amazonaws.com/postgres", echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    transaction_type = Column(String)
    symbol = Column(String)
    stock_name = Column(String)
    stock_price = Column(Integer)
    no_of_shares = Column(Integer)
    total = Column(Integer)
    transacted = Column(DateTime)

    def __init__(
            self,
            username=None,
            transaction_type=None,
            symbol=None,
            stock_name=None,
            stock_price=None,
            no_of_shares=None,
            total=None,
            transacted=None):
        self.username = username
        self.transaction_type = transaction_type
        self.symbol = symbol
        self.stock_name = stock_name
        self.stock_price = stock_price
        self.no_of_shares = no_of_shares
        self.total = total
        self.transacted = transacted

    def __repr__(self):
        return "History(%r, %r, %r)" % (self.username, self.transaction_type, self.symbol)


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    hash = Column(String, nullable=False)
    cash = Column(Integer, default=10000)

    def __init__(self, username=None, hash=None):
        self.username = username
        self.hash = hash

    def __repr__(self):
        return "User(%r, %r)" % (self.username, self.hash)


engine = create_engine("postgresql://postgres:mrlonely@database-1.conyko6usosg.us-east-1.rds.amazonaws.com/postgres", echo=True)

Base.metadata.create_all(engine)

