import os

from schema import Users, History, Holdings
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, sessionmaker

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session

from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, get_username


from auth import auth
from stock import stock
# Configure application
app = Flask(__name__)
app.register_blueprint(auth)
app.register_blueprint(stock)


# Configure SQLAlchemy Library to use PostgresSQL database
engine = create_engine("postgresql://postgres:mrlonely@database-1.conyko6usosg.us-east-1.rds.amazonaws.com/postgres", echo=True)
db_Session = sessionmaker(bind=engine)
db_session = db_Session()

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Find all the stocks that the user holds aggregately.
    user_stocks = db_session.query(Holdings.stock_name, Holdings.symbol, Holdings.total,
                                   Holdings.average_price, Holdings.shares).\
        filter(Holdings.user_id == session["id"]).all()

    user_stocks = [dict(row) for row in user_stocks]

    # Stocks to quote the latest price.
    stocks = ""
    for s in user_stocks:
        stocks += s["symbol"] + ","
    curr = lookup(stocks)

    # Value of all the shares user holding
    total_stocks_value = 0
    total_invested = 0
    # Add current price and total value of each stock of user stocks
    for stock in user_stocks:
        # Get current value of the stock
        price = curr["price"] if isinstance(curr, dict) else [stk["price"] for stk in curr if stk["symbol"] == stock["symbol"]][0]

        # Add new current price field
        stock['price'] = price

        # Adding total value of the number of shares of particular stock
        stock['curr_total'] = round(price * stock['shares'], 2)
        total_invested += stock["total"]
        total_stocks_value += stock['curr_total']

    # User's current available cash
    user_cash = db_session.query(Users.cash).filter(Users.id == session['id']).all()[0]['cash']

    return render_template('index.html', stocks=user_stocks, cash=user_cash, total_invested=round(total_invested, 2),
                           total=round(total_stocks_value, 2), usd=usd, user=session["user"], round=round)


@app.errorhandler(404)
def page_not_found(e):
    """For no page"""
    # note that we set the 404 status explicitly
    return render_template("no_page.html"), 404


@app.errorhandler(500)
def server_error():
    return render_template("500.html"), 500

