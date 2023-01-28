from schema import Users, Holdings, History
import os
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, sessionmaker
from flask import Flask, flash, redirect, render_template, request, session, Blueprint

from helpers import apology, login_required, lookup, usd

stock = Blueprint('stock', __name__)


# Configure SQLAlchemy Library to use PostgresSQL database
engine = create_engine(os.environ.get('DB_URL'), echo=True)
db_Session = sessionmaker(bind=engine)
db_session = db_Session()


@stock.route("/quote", methods=["GET", "POST"])
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
            return render_template('quote.html', quote=quote)
        else:
            return render_template('quote.html', err='Invalid stock symbol.')

    else:
        return render_template('quote.html')


@stock.route("/buy", methods=["GET", "POST"])
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
            balance = db_session.query(Users.cash).filter(Users.id == session['id']).all()[0]['cash']

            # Total value of shares.
            total = quote['price'] * float(request.form.get('shares'))

            # Ensuring user has enough cash to buy the shares.
            if balance >= total:

                # Adding the current transaction into history of transactions.
                h1 = History(user_id=session["id"], transaction_type="BUY", symbol=quote["symbol"],
                             stock_name=quote["name"], stock_price=quote["price"],
                             no_of_shares=request.form.get('shares'),
                             total=total, transacted=datetime.now(), p_l=0)

                balance -= total
                try:
                    # Updating user's balance.
                    db_session.query(Users).filter(Users.id == session["id"])\
                        .update({Users.cash: round(balance, 2)}, synchronize_session='evaluate')

                    # Adding transaction to history
                    db_session.add(h1)

                    user_stock_holds = db_session.query(Holdings).filter(Holdings.user_id == session["id"],
                                                                         Holdings.symbol == quote["symbol"]).all()
                    if len(user_stock_holds) != 0:
                        total_shares = int(request.form.get('shares')) + user_stock_holds[0].shares
                        average_price = (total + user_stock_holds[0].total)/float(total_shares)
                        total_invested = average_price * total_shares

                        db_session.query(Holdings)\
                            .filter(Holdings.user_id == session["id"], Holdings.symbol == quote["symbol"])\
                            .update({Holdings.shares: total_shares, Holdings.average_price: average_price,
                                    Holdings.total: total_invested}, synchronize_session='evaluate')

                    else:
                        new_holds = Holdings(user_id=session["id"], symbol=quote["symbol"], stock_name=quote["name"],
                                             average_price=quote["price"], total=total, shares=request.form.get("shares"))
                        db_session.add(new_holds)

                    db_session.commit()

                except:
                    db_session.rollback()
                    return apology("Something went wrong", 500)
                session["cash"] = round(balance, 2)
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


@stock.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Find all the stocks that the user holds aggregate.
    user_stocks = db_session.query(Holdings.stock_name, Holdings.symbol, Holdings.total,
                                   Holdings.average_price, Holdings.shares). \
        filter(Holdings.user_id == session["id"], Holdings.shares > 0).all()
    user_stocks = [dict(row) for row in user_stocks]

    if request.method == 'POST':

        # Ensuring Valid number of shares
        if not request.form.get("shares") or int(request.form.get('shares')) < 1:
            return render_template('sell.html', stocks=user_stocks, err='Must provide valid number of shares.')

        quote = lookup(request.form.get('symbol'))

        # Ensuring user has sufficient amount of shares
        for stock in user_stocks:
            if stock['symbol'] == request.form.get('symbol'):
                if stock['shares'] < int(request.form.get('shares')):
                    return render_template('sell.html', stocks=user_stocks,
                                           err='Number of shares are more than you own. Try a different number.')

        # Querying user available cash
        balance = db_session.query(Users.cash).filter(Users.id == session['id']).all()[0]['cash']

        # Total value of stocks
        total = quote['price'] * float(request.form.get('shares'))

        # Average price of the stock the user is holding
        avg = [stk["average_price"] for stk in user_stocks if stk["symbol"] == quote["symbol"]][0]

        # Profit or loss on this sell
        pl = total - avg*float(request.form.get('shares'))

        # Updating the history of transaction
        shares = -int(request.form.get('shares'))
        h1 = History(user_id=session["id"], transaction_type="SELL", symbol=quote["symbol"],
                     stock_name=quote["name"], stock_price=quote["price"], no_of_shares=shares,
                     total=total, transacted=datetime.now(), p_l=pl)

        user_stock_holds = db_session.query(Holdings).filter(Holdings.user_id == session["id"],
                                                             Holdings.symbol == quote["symbol"]).all()
        total_shares = user_stock_holds[0].shares - int(request.form.get('shares'))
        total_invested = user_stock_holds[0].average_price * total_shares

        # Updating user's available balance
        balance += total
        try:
            db_session.query(Users).filter(Users.id == session["id"]) \
                .update({Users.cash: round(balance, 2)}, synchronize_session='evaluate')
            db_session.query(Holdings) \
                .filter(Holdings.user_id == session["id"], Holdings.symbol == quote["symbol"]) \
                .update({Holdings.shares: total_shares, Holdings.total: total_invested}, synchronize_session='evaluate')
            db_session.add(h1)
            db_session.commit()
        except:
            db_session.rollback()
            return apology("Something went wrong", 500)

        session["cash"] = round(balance, 2)
        # Flash sold message
        flash(
            f"Sold! {request.form.get('shares')} shares of {quote['name']} worth {usd(quote['price'])} each.")

        # Redirect to index page.
        return redirect('/')
    else:
        return render_template('sell.html', stocks=user_stocks)


@stock.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Query all the user's transactions from history table.
    user_history = db_session.query(History).filter(History.user_id == session["id"]) \
        .order_by(desc(History.transacted)).all()

    # Render history template
    return render_template('history.html', history=user_history, round=round)

