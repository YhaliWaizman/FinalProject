from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, request
from flask_pymongo import PyMongo
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from config import db, SECRET_KEY
import random
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Email, Length, EqualTo, ValidationError, Regexp
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from Emailer import SendMessage
import socket
import secrets
import time

app = Flask(__name__)
app.config.from_pyfile('config.py')
mongo = db
password_pattern = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&.])[A-Za-z\d@$!%*?&^][^,\"\';\\\{\}\<\>]{7,}$')
user_pattern = re.compile(r'^[^,\"\';\\\{\}\<\>]{1,}$')
limiter = Limiter(app, default_limits=["200 per day", "50 per hour"])
limiter._key_func = get_remote_address

subject = "MAZEGAME"
body = """<!DOCTYPE html>
<html>
<head>
	<title>Server Status Update</title>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<style>
		body {
			background-color: #e6b7fc;
		}
		a {
			color: #cfcecebe;
		}
		.container {
			width: 400px;
			margin: 50px auto;
			padding: 20px;
			border: 1px solid #ccc;
			border-radius: 5px;
			background-color: #4e059699;
			color: #ffffff;
		}
		.general_button{
			padding: 10px;
			font-size: 18px;
			background-color: #9b2fb6;
			color: white;
			border: none;
			border-radius: 5px;
			cursor: pointer;
			margin-top: 20px;
			text-decoration: none;
		}
		.general_button:hover {
			background-color: #84239c;
		}
		.center{
			text-align: center;
		}
	</style>
</head>
<body>
	<div class="container">
		<h1 class="center">Server Status Update</h1>
		<p class="center">The server is up and running.</p>
		<button class="general_button"><a href="/login">Join Server</a></button>
	</div>
</body>
</html>"""
sender = "mazegamecyber@gmail.com"

# helper function for generating token


def generate_token(email):
    token = secrets.token_urlsafe(16)
    mongo.db.users.find_one_and_update(
        {'email': email}, {"$set": {'token': token}})
    mongo.db.users.find_one_and_update(
        {'email': email}, {"$set": {'time': time.time()}})
    return token

# helper function for verifying token


def verify_token(email, token):
    user = mongo.db.users.find_one({'email': email})
    delta = time.time() - user['time']
    if user['token'] == token and delta < 18000:
        return email
    else:
        return False


def password_strength_check(form, field):
    if not password_pattern.match(field.data):
        raise ValidationError(
            'Password must contain at least 8 characters, including at least 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character (@$!%*?&.)')


def user_strength_check(form, field):
    if not user_pattern.match(field.data):
        raise ValidationError(
            'Username must not contain any special characters or spaces')

# Form for user registration


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[
                       InputRequired(), Length(max=50), user_strength_check])
    email = StringField('Email', validators=[
                        InputRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[
                             InputRequired(), password_strength_check])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     InputRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')


@ app.route('/submit', methods=['POST'])
def submit():
    if not session.get("logged_in"):
        return "access denied"
    eTime = int(request.args.get("eTime"))
    session['score'] = session['score'] + 1
    if(session['bestTime'] > eTime):
        session['bestTime'] = eTime
        mongo.db.users.find_one_and_update({'email': session['user']}, {
            "$set": {"bestTime": session['bestTime']/1000}})
    mongo.db.users.find_one_and_update({'email': session['user']}, {
                                       "$set": {"score": session['score']}})
    return jsonify({'success': True}), 200, {'ContentType': 'application/json'}

# route for sending verification email


@ app.route('/send_verification_email', methods=['POST', 'GET'])
def send_verification_email():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    email = session['user']
    token = generate_token(email)
    subject = "Verify your email for MAZEGAME"
    sender = "mazegamecyber@gmail.com"
    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    body = """<!DOCTYPE html>
        <html>
        <head>
            <title>MAZEGAME Email Verification</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    background-color: #e6b7fc;
                }
                a {
                    color: #cfcecebe;
                }
                .container {
                    width: 400px;
                    margin: 50px auto;
                    padding: 20px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    background-color: #4e059699;
                    color: #ffffff;
                }
                .general_button{
                    padding: 10px;
                    font-size: 18px;
                    background-color: #9b2fb6;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                    text-decoration: none;
                }
                .general_button:hover {
                    background-color: #84239c;
                }
                .center{
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="center">MAZEGAME Email Verification</h1>
                <p>Please click the following link to verify your email for MAZEGAME:</p>
                <a class="general_button" href="http://currip/verify_email/token">Verify Email</a>
            </div>
        </body>
        </html>""".replace('token', token).replace('currip', 'localhost:5000')
    try:
        SendMessage(sender, email, subject, body)
        flash("A verification email has been sent to your email address.",
              "positive-alert")
    except:
        flash("Failed to send verification email. Please try again later.", "alert")
    return redirect(url_for('home'))

# route for verifying email


@ app.route('/verify_email/<token>')
def verify_email(token):
    email = verify_token(session['user'], token)
    if email == False:
        flash("Invalid or expired token. Please try again.", "alert")
        return redirect(url_for('home'))
    user = mongo.db.users.find_one({"email": email})
    if user and not user.get("email_verified"):
        mongo.db.users.update_one(
            {"email": email}, {"$set": {"email_verified": True}})
        mongo.db.users.find_one_and_update(
            {'email': email}, {"$set": {'token': None}})
        mongo.db.users.find_one_and_update(
            {'email': email}, {"$set": {'time': None}})
        flash("Your email has been successfully verified.", "positive-alert")
    else:
        flash("Your email has already been verified.", "info")
    return redirect(url_for('home'))


@ app.route('/')
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Retrieve user data from the database
    users = mongo.db.users.find(
        {}, {"_id": 0, "name": 1, "score": 1, "bestTime": 1})

    # Render the template with the user data
    return render_template("home.html", users=users, Username=session['name'])


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST':
        name = form.name.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(password)

        if not form.validate_on_submit():
            form.confirm_password.errors.append(
                'Passwords must match and meet the specified criteria.')
            return render_template('register.html', form=form)

        if mongo.db.users.find_one({'email': email}):
            flash('Email already taken, please try again.', 'alert')
            return redirect(url_for('register'))
        else:
            mongo.db.users.insert_one({
                'name': name,
                'email': email,
                'password': hashed_password,
                'score': 0,
                'bestTime': 999999999,
                'email_verified': False,
                'token': None,
                'time': None
            })
            flash("Please log in!", 'positive-alert')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)


@ app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get("logged_in"):
        flash("already logged in", "alert")
        return redirect(url_for("home"))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = mongo.db.users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user'] = user['email']
            session['logged_in'] = True
            session['score'] = user['score']
            session['bestTime'] = user['bestTime']
            session['name'] = user['name']
            return redirect(url_for('home'))
        else:
            flash('Incorrect email or password, please try again.', 'alert')

    return render_template('login.html', form=RegistrationForm)


@ app.route("/logout")
def logout():
    session["logged_in"] = False
    session.pop("username", None)
    return redirect(url_for("login"))


@ app.route("/maze")
def maze():
    if session["logged_in"] != True:
        flash('please log in.', 'alert')
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"email": session['user']})
    if user['email_verified'] == False:
        flash('Verify your account to play the Game', 'alert')
        return redirect(url_for('home'))
    winText = ["YEEPEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE, YOU WIN!", "Congratulations! You've Won!",
               "Welldone! Thanks For Playing!", "Oh Yeah, Mario Time!", "Nice!"]
    num = random.randint(0, 4)
    return render_template("maze.html", win=winText[num])


@ app.route("/deleteuser", methods=['GET', 'POST'])
def delete_user():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == 'POST':
        confirmation = request.form['confirmation']
        if confirmation == 'yes':
            mongo.db.users.delete_one({'email': session['user']})
            session.clear()
            flash('Your account has been deleted.', 'positive-alert')
            return redirect(url_for('login'))
        if confirmation == 'no':
            return redirect(url_for('home'))

    # Render the confirmation template if the request method is GET
    return render_template('delete.html')


@ app.route("/update", methods=['GET', 'POST'])
def update_user():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        # retrieve form data
        new_name = request.form["name"]
        new_email = request.form["email"]

        if mongo.db.users.find_one({'email': new_email}) and session["user"] != new_email:
            flash('Email already taken, please try again.', 'alert')
        else:
            flash("Your profile has been updated.", 'positive-alert')
        # update user data in the database
        mongo.db.users.update_one(
            {"email": session["user"]},
            {"$set": {"name": new_name, "email": new_email}}
        )

        # update session data with new user data
        session["user"] = new_email
        session["name"] = new_name

        return redirect(url_for("home"))

    return render_template('update.html', username=session["name"], mail=session['user'], form=RegistrationForm)


@ app.errorhandler(404)
def page_not_found(e):
    flash("404 error", "alert")
    return redirect(url_for('home'))


"""
recipients = db.db.users.find({}, {"_id": 0, "email": 1})
lrecipients = list(recipients)
for recipient in lrecipients:
    emailrecp = recipient["email"]
    SendMessage(sender, emailrecp, subject, body)"""
app.run(debug=True)
