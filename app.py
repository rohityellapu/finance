import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


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
    user_stocks = db.execute(
        "SELECT symbol,stock_name, SUM(no_of_shares) AS shares FROM history WHERE username = ? GROUP BY symbol;", session['user'])

    # Value of all the shares user holding
    total_stocks_value = 0

    # Add current price and total value of each stock of user stocks
    for stock in user_stocks:
        # Get current value of the stock
        price = lookup(stock['symbol'])['price']

        # Add new current price field
        stock['price'] = price

        # Adding total value of the number of shares of particular stock
        stock['total'] = round(price * stock['shares'], 2)

        total_stocks_value += stock['total']

    # User's current available cash
    user_cash = db.execute('SELECT cash FROM users WHERE username = ?', session['user'])[0]['cash']

    return render_template('index.html', stocks=user_stocks, cash=user_cash, total=total_stocks_value, usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("Must provide symbol", 400)

        # Ensure shares was submitted
        elif not request.form.get("shares") or not request.form.get('shares').isdigit() or int(request.form.get('shares')) < 1:
            return apology("Must provide valid number of shares", 400)

        quote = lookup(request.form.get('symbol'))

        # Ensure the stock quote exists on the given symbol.
        if quote:

            # Query user's current available cash.
            balance = db.execute(
                'SELECT cash FROM users WHERE username = ?', session["user"])

            # Total value of shares.
            total = quote['price'] * float(request.form.get('shares'))

            # Ensuring user has enough cash to buy the shares.
            if balance[0]['cash'] >= total:

                # Adding the current transaction into histiry of transactions.
                db.execute(
                    'INSERT INTO history (username, transaction_type, symbol,stock_name, stock_price,no_of_shares,total, transacted) VALUES (?,?,?,?,?,?,?,?)',
                    session["user"], "buy", quote["symbol"], quote["name"], quote["price"], request.form.get('shares'), total, datetime.now())

                # Updating user's balance.
                balance[0]['cash'] -= total
                db.execute('UPDATE users SET cash = ? WHERE username = ?',
                           balance[0]['cash'], session['user'])

                # Flash the bought message.
                flash(f"Bought! {request.form.get('shares')} shares of {quote['name']} worth {usd(quote['price'])} each.")

                # Redirect to index page
                return redirect("/")

            else:
                return apology('No enough balance.Try different number of shares', 400)

        else:
            return apology('Invalid stock symbol.', 400)

    else:
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Query all the user's transactions from history table.
    user_history = db.execute("SELECT * FROM history WHERE username = ? ORDER BY transacted DESC", session['user'])

    # Render history template
    return render_template('history.html', history=user_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)

        # Remember which user has logged in
        session["user"] = rows[0]["username"]

        # Flash a login message
        flash('Logged in.')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


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
            return apology('Must provide Symbol', 400)

        quote = lookup(request.form.get('symbol'))
        # Ensure the valid stock symbol
        if quote:
            quote['price'] = usd(quote['price'])
            return render_template('quoted.html', quote=quote)
        else:
            return apology('Invalid stock symbol.', 400)

    else:
        return render_template('quote.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == 'POST':
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 400)

        # Ensure both the given are same.
        elif request.form.get('password') != request.form.get('confirmation'):
            return apology('Passwords doesn"t match', 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Check if the user already exists.
        if len(rows) != 0:
            return apology("User already exists, try loggin in", 400)

        db.execute('INSERT INTO users (username, hash) VALUES (?,?)',
                   request.form.get("username"), generate_password_hash(request.form.get("password")))
        # Remember which user has logged in
        session["user"] = request.form.get("username")

        flash('Registered!')
        # Redirect user to home page
        return redirect("/")

    else:
        return render_template('register.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Find all the stocks that the user holds aggregately.
    user_stocks = db.execute(
        'SELECT symbol, SUM(no_of_shares) AS shares FROM history WHERE username = ? GROUP BY symbol', session['user'])

    if request.method == 'POST':

        # Ensuring Valid number of shares
        if not request.form.get("shares") or int(request.form.get('shares')) < 1:
            return apology("Must provide valid number of shares", 400)

        quote = lookup(request.form.get('symbol'))

        # Ensuring user has sufficient amout of shares
        for stock in user_stocks:
            if stock['symbol'] == request.form.get('symbol'):
                if stock['shares'] < int(request.form.get('shares')):
                    return apology('Number of shares are more than you own. Try a different number.', 400)

        # Querying user available cash
        balance = db.execute('SELECT cash FROM users WHERE username = ?', session["user"])

        # Total value of stocks
        total = quote['price'] * float(request.form.get('shares'))

        # Updating the history of transaction
        shares = -int(request.form.get('shares'))
        db.execute(
            'INSERT INTO history (username, transaction_type, symbol,stock_name, stock_price,no_of_shares,total, transacted) VALUES (?,?,?,?,?,?,?,?)',
            session["user"], "sell", quote["symbol"], quote["name"], quote["price"], shares, total, datetime.now())

        # Updating user's available balance
        balance[0]['cash'] += total
        db.execute('UPDATE users SET cash = ? WHERE username = ?',
                   balance[0]['cash'], session['user'])

        # Flash sold message
        flash(
            f"Sold! {request.form.get('shares')} shares of {quote['name']} worth {usd(quote['price'])} each.")

        # Redirect to index page.
        return redirect('/')
    else:
        return render_template('sell.html', stocks=user_stocks)


@app.route("/password", methods=["GET", "POST"])
def change_password():
    """Change the password of the user."""
    if request.method == 'POST':

        # Ensure password was submitted.
        if not request.form.get("password") or not request.form.get('confirmation'):
            return apology("Must provide password", 400)

        # Ensuring the two password are same.
        elif request.form.get('password') != request.form.get('confirmation'):
            return apology('Passwords doesn"t match', 400)

        # Updating the user's hash with new password.
        db.execute('UPDATE users SET hash = ? WHERE username = ?',
                   generate_password_hash(request.form.get("password")), session['user'])

        # Flash update message.
        flash('Password Updated')

        # Redirect to index page.
        return redirect('/')
    else:
        return render_template('password.html')
