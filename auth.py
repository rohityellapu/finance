
from schema import Users, History, Holdings
from datetime import datetime
from sqlalchemy import *
from sqlalchemy.orm import relation, sessionmaker
from flask import Flask, flash, redirect, render_template, request, session, Blueprint
from flask_session import Session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, get_username

auth = Blueprint('auth', __name__)


# Configure SQLAlchemy Library to use PostgresSQL database
engine = create_engine("postgresql://postgres:mrlonely@database-1.conyko6usosg.us-east-1.rds.amazonaws.com/postgres", echo=True)
db_Session = sessionmaker(bind=engine)
db_session = db_Session()


@auth.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Flash log out message
    flash('Logged out.')
    # Redirect user to login form
    return redirect("/")


@auth.route("/login", methods=["GET", "POST"])
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
        session["email"] = rows[0].email
        session["cash"] = rows[0].cash
        session["id"] = rows[0].id

        # Flash a login message
        flash('Logged in.')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@auth.route("/register", methods=["GET", "POST"])
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
        session["email"] = new_user.email
        session["cash"] = 10000
        session["id"] = new_user.id

        flash('Registered!')
        # Redirect user to home page
        return redirect("/")

    else:
        return render_template('register.html')


@auth.route("/settings", methods=["GET", "POST"])
@login_required
def change_password():
    """Change the password of the user."""
    if request.method == 'POST':
        # Ensure input fields are submitted.
        # If updating password
        if request.form.get("password") and request.form.get('confirmation'):

            # Ensuring the two password are same.
            if request.form.get('password') != request.form.get('confirmation'):
                return render_template('settings.html', err='Passwords doesn"t match.')

            # Updating the user's hash with new password.

            db_session.query(Users).filter(Users.id == session["id"]) \
                .update({Users.hash: generate_password_hash(request.form.get("password"))}, synchronize_session='evaluate')
            db_session.commit()

            # Flash update message.
            flash('Password Updated')

            # Redirect to index page.
            return redirect('/settings')

        # If updating username
        elif request.form.get('username'):
            # If user entered same username
            if request.form.get("username") == session["user"]:
                return render_template('settings.html', err='Enter a new username for updating.')
            # Check if the given username already taken
            is_users_present = db_session.query(Users).filter(Users.username == request.form.get("username")).all()

            # Update user's username
            if len(is_users_present) != 1:

                db_session.query(Users).filter(Users.username == session["user"]) \
                    .update({Users.username: request.form.get('username')},
                            synchronize_session='evaluate')
                db_session.commit()
                session["user"] = request.form.get('username')
                # Flash update message.
                flash(f'Username Updated to {session["user"]}')

                # Redirect to index page.
                return redirect('/settings')

            else:
                return render_template('settings.html', err='Username already exists try a different one.')
        else:
            return render_template('settings.html', err='All fields are necessary.')
    else:
       return render_template('settings.html')
