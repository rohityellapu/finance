import os
import requests
import urllib.parse
import random
from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:

        url = "https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/v2/get-quotes"

        querystring = {"region": "US", "symbols": f"{symbol}"}

        headers = {
            "X-RapidAPI-Key": "9c311fa357msh30825da29fc5b12p1f9426jsnc32b7a4f733c",
            "X-RapidAPI-Host": "apidojo-yahoo-finance-v1.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)

        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()["quoteResponse"]["result"]

        # quote2 = response2.json()
        if len(quote) == 1:
            return {
                "name": quote[0]["longName"],
                "price": float(quote[0]["regularMarketPrice"]),
                "symbol": quote[0]["symbol"]
            }
        else:
            quotes = []
            for q in quote:
                quotes.append({"name": q["longName"],
                               "price": float(q["regularMarketPrice"]),
                               "symbol": q["symbol"]})
            return quotes
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def get_username(email):
    username = ""
    for c in email:
        if c == '@':
            break
        username += c
    username += str(int(random.random()*100))
    return  username
