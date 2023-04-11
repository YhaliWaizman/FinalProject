from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
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
import bcrypt


app = Flask(__name__)
app.config.from_pyfile('config.py')
mongo = db
password_pattern = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&.])[A-Za-z\d@$!%*?&.]{8,}$')
# Configuration of limiter extension, limits the amount of requests per client
limiter = Limiter(get_remote_address, app=app, default_limits=[
                  "200 per day", "50 per hour"])


def password_strength_check(form, field):
    if not password_pattern.match(field.data):
        raise ValidationError(
            'Password must contain at least 8 characters, including at least 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character (@$!%*?&.)')


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(max=50)])
    email = StringField('Email', validators=[
                        InputRequired(), Email(), Length(max=100)])
    password = PasswordField('Password', validators=[
                             InputRequired(), password_strength_check])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     InputRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')


@app.route('/submit', methods=['POST'])
def submit():
    if not session.get("logged_in"):
        return "access denied"
    eTime = int(request.args.get("eTime"))
    session['score'] = session['score'] + 1
    if(session['bestTime'] > eTime):
        session['bestTime'] = eTime
    mongo.db.users.find_one_and_update({'email': session['user']}, {
                                       "$set": {"score": session['score']}})
    mongo.db.users.find_one_and_update({'email': session['user']}, {
                                       "$set": {"bestTime": session['bestTime']/1000}})
    return jsonify({'success': True}), 200, {'ContentType': 'application/json'}


@app.route('/')
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # Retrieve user data from the database
    users = mongo.db.users.find(
        {}, {"_id": 0, "name": 1, "score": 1, "bestTime": 1})

    # Render the template with the user data
    return render_template("home.html", users=users, Username=session['name'])


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST':
        name = form.name.data
        email = form.email.data
        password = form.password.data
        hashed_password = bcrypt.hashpw(password)

        if not form.validate_on_submit():
            form.confirm_password.errors.append(
                'Passwords must match and meet the specified criteria.')
            return render_template('register.html', form=form)

        # check if user already exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already taken, please try again.', 'alert')
            return redirect(url_for('register'))
        else:

            # add user to the database with a "verified" flag set to False
            mongo.db.users.insert_one({
                'name': name,
                'email': email,
                'password': hashed_password,
                'score': 0,
                'bestTime': 999999999
            })
            flash("Please log in!", 'positive-alert')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = mongo.db.users.find_one({'email': email})
        if user and bcrypt.checkpw(user['password'], password):
            session['user'] = user['email']
            session['logged_in'] = True
            session['score'] = user['score']
            session['bestTime'] = user['bestTime']
            session['name'] = user['name']
            return redirect(url_for('home'))
        else:
            flash('Incorrect email or password, please try again.', 'alert')

    return render_template('login.html')


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
    winText = ["YEEPEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE, YOU WIN!", "Congratulations! You've Won!",
               "Welldone! Thanks For Playing!", "Oh Yeah, Mario Time!", "Nice!"]
    num = random.randint(0, 4)
    return render_template("maze.html", win=winText[num])


@ app.route("/deleteuser")
def delete_user():
    session["logged_in"] = False
    session.pop("username", None)
    mongo.db.users.find_one_and_delete({'email': session['user']})
    return redirect(url_for("login"))


@app.route("/update", methods=['GET', 'POST'])
def update_user():
    if request.method == "POST":
        # retrieve form data
        new_name = request.form["name"]
        new_email = request.form["email"]

        if mongo.db.users.find_one({'email': new_email}):
            flash('Email already taken, please try again.', 'alert')

        # update user data in the database
        mongo.db.users.update_one(
            {"email": session["user"]},
            {"$set": {"name": new_name, "email": new_email}}
        )

        # update session data with new user data
        session["user"] = new_email
        session["name"] = new_name

        flash("Your profile has been updated.", 'positive-alert')
        return redirect(url_for("home"))

    return render_template('update.html', username=session["name"], mail=session['user'])


if __name__ == "__main__":
    app.run(debug=True)
