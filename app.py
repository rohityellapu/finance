import os

from schema import Users, History, Holdings
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, sessionmaker

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session

from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, get_username

# Configure application
app = Flask(__name__)

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

    user_stocks = db_session.query(History.stock_name, History.symbol,
                                   func.sum(History.no_of_shares).label('shares'))\
        .filter(History.username == session['user'])\
        .group_by(History.symbol, History.stock_name).all()
    stocks_bought_at = db_session.query(History.stock_name, History.symbol,
                                   func.sum(History.stock_price).label('average'))\
        .filter(History.username == session['user'], History.transaction_type == "BUY")\
        .group_by(History.symbol, History.stock_name).all()

    user_stocks = [dict(row) for row in user_stocks]

    # Value of all the shares user holding
    total_stocks_value = 0
    stocks = ""
    for s in user_stocks:
        s["average"] = [stk["average"] for stk in stocks_bought_at if stk["symbol"] == s["symbol"]][0]
        stocks += s["symbol"] + ","
    curr = lookup(stocks)

    # Add current price and total value of each stock of user stocks

    for stock in user_stocks:
        # Get current value of the stock
        price = curr["price"] if isinstance(curr, dict) else [stk["price"] for stk in curr if stk["symbol"] == stock["symbol"]][0]

        # Add new current price field
        stock['price'] = price

        # Adding total value of the number of shares of particular stock
        stock['total'] = round(price * stock['shares'], 2)

        total_stocks_value += stock['total']

    # User's current available cash
    user_cash = db_session.query(Users.cash).filter(Users.username == session['user']).all()[0]['cash']

    return render_template('index.html', stocks=user_stocks, cash=user_cash,
                           total=total_stocks_value, usd=usd, user=session["user"], round=round)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("email"):
            return render_template("login.html", err="Must provide email")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", err="Must provide password")

        # Query database for username
        rows = db_session.query(Users).filter(Users.email == request.form.get('email')).all()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0].hash, request.form.get("password")):
            return render_template("login.html", err="Invalid email and/or password")

        # Remember which user has logged in
        session["user"] = rows[0].username

        # Flash a login message
        flash('Logged in.')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == 'POST':
        # Ensure username was submitted
        if not request.form.get("email"):
            return render_template('register.html', err="Must provide Email.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template('register.html', err="Must provide password.")

        # Ensure both the given are same.
        elif request.form.get('password') != request.form.get('confirmation'):
            return render_template('register.html', err="Passwords doesn't match.")

        # Query database for username
        rows = db_session.query(Users).filter(Users.email == request.form.get('email')).all()

        # Check if the user already exists.
        if len(rows) != 0:
            return render_template('register.html', err="User already exists, try loggin in.")

        new_user = Users(email=request.form.get("email"), hash=generate_password_hash(request.form.get("password")),
                         username=get_username(request.form.get("email")))
        try:
            db_session.add(new_user)
            db_session.commit()
        except:
            db_session.rollback()
            return apology("Something went wrong", 500)
        # Remember which user has logged in
        session["user"] = new_user.username

        flash('Registered!')
        # Redirect user to home page
        return redirect("/")

    else:
        return render_template('register.html')

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Flash log out message
    flash('Logged out.')
    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        if not request.form.get('symbol'):
            return render_template('quote.html', err='Must provide Symbol.')
        quote = lookup(request.form.get('symbol'))
        # Ensure the valid stock symbol
        if quote:
            quote['price'] = usd(quote['price'])
            return render_template('quoted.html', quote=quote)
        else:
            return render_template('quote.html', err='Invalid stock symbol.')

    else:
        return render_template('quote.html')



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return render_template('buy.html', err='Must provide symbol.')

        # Ensure shares was submitted
        elif not request.form.get("shares") or not request.form.get('shares').isdigit() or int(request.form.get('shares')) < 1:
            return render_template('buy.html', err='Must provide valid number of shares.')

        quote = lookup(request.form.get('symbol'))

        # Ensure the stock quote exists on the given symbol.
        if quote:

            # Query user's current available cash.
            balance = db_session.query(Users.cash).filter(Users.username == session['user']).all()[0]['cash']

            # Total value of shares.
            total = quote['price'] * float(request.form.get('shares'))

            # Ensuring user has enough cash to buy the shares.
            if balance >= total:

                # Adding the current transaction into history of transactions.
                h1 = History(username=session["user"], transaction_type="BUY", symbol=quote["symbol"],
                             stock_name=quote["name"], stock_price=quote["price"],
                             no_of_shares=request.form.get('shares'),
                             total=total, transacted=datetime.now())
                # Updating user's balance.
                balance -= total
                try:
                    db_session.query(Users).filter(Users.username == session["user"])\
                        .update({Users.cash: balance}, synchronize_session='evaluate')

                    db_session.add(h1)
                    db_session.commit()
                except:
                    db_session.rollback()
                    return apology("Something went wrong", 500)

                # Flash the bought message.
                flash(f"Bought! {request.form.get('shares')} shares of {quote['name']} worth {usd(quote['price'])} each.")

                # Redirect to index page
                return redirect("/")

            else:
                return render_template('buy.html', err='No enough balance.Try different number of shares.')

        else:
            return render_template('buy.html', err='Invalid stock symbol.')

    else:
        return render_template('buy.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Find all the stocks that the user holds aggregately.
    user_stocks = []
    try:
        user_stocks = db_session.query(History.stock_name, History.symbol, func.sum(History.no_of_shares).label('shares'))\
            .filter(History.username == session['user'])\
            .group_by(History.symbol, History.stock_name, History.symbol).all()
        user_stocks = [dict(row) for row in user_stocks]
    except:
        db_session.rollback()
        return apology("Something went wrong", 500)

    if request.method == 'POST':

        # Ensuring Valid number of shares
        if not request.form.get("shares") or int(request.form.get('shares')) < 1:
            return render_template('sell.html', stocks=user_stocks, err='Must provide valid number of shares.')

        quote = lookup(request.form.get('symbol'))

        # Ensuring user has sufficient amout of shares
        for stock in user_stocks:
            if stock['symbol'] == request.form.get('symbol'):
                if stock['shares'] < int(request.form.get('shares')):
                    return render_template('sell.html', stocks=user_stocks,
                                           err='Number of shares are more than you own. Try a different number.')


        # Querying user available cash
        balance = db_session.query(Users.cash).filter(Users.username == session['user']).all()[0]['cash']

        # Total value of stocks
        total = quote['price'] * float(request.form.get('shares'))

        # Updating the history of transaction
        shares = -int(request.form.get('shares'))
        h1 = History(username=session["user"], transaction_type="SELL", symbol=quote["symbol"],
                     stock_name=quote["name"], stock_price=quote["price"], no_of_shares=shares,
                     total=total, transacted=datetime.now())

        # Updating user's available balance
        balance += total
        try:
            db_session.query(Users).filter(Users.username == session["user"]) \
                .update({Users.cash: balance}, synchronize_session='evaluate')
            db_session.add(h1)
            db_session.commit()
        except:
            db_session.rollback()
            return apology("Something went wrong", 500)

        # Flash sold message
        flash(
            f"Sold! {request.form.get('shares')} shares of {quote['name']} worth {usd(quote['price'])} each.")

        # Redirect to index page.
        return redirect('/')
    else:
        return render_template('sell.html', stocks=user_stocks)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Query all the user's transactions from history table.
    user_history = db_session.query(History).filter(History.username == session["user"]) \
        .order_by(desc(History.transacted)).all()

    # Render history template
    return render_template('history.html', history=user_history)


@app.route("/password", methods=["GET", "POST"])
def change_password():
    """Change the password of the user."""
    if request.method == 'POST':

        # Ensure password was submitted.
        if not request.form.get("password") or not request.form.get('confirmation'):
            return render_template('password.html', err='Must provide password.')

        # Ensuring the two password are same.
        elif request.form.get('password') != request.form.get('confirmation'):
            return render_template('password.html', err='Passwords doesn"t match.')

        # Updating the user's hash with new password.
        db_session.query(Users).filter(Users.username == session["user"]) \
            .update({Users.hash: generate_password_hash(request.form.get("password"))}, synchronize_session='evaluate')

        # Flash update message.
        flash('Password Updated')

        # Redirect to index page.
        return redirect('/')
    else:
        return render_template('password.html')
