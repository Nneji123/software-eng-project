import re
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3 as sql
import cv2
import io
from PIL import Image
import numpy as np
from utils import *


app = Flask(__name__, static_folder="static")
app.secret_key = 'testsecret'

@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        con = sql.connect('database.db')
        cur = con.cursor()
        # cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT NOT NULL, password TEXT NOT NULL);")
        password = hash_password(password)
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        account = cur.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # session['email'] = account['email']
            msg = 'Logged in successfully !'
            return render_template('index.html', msg = msg)
        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg = msg)
 
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))
 
@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        con = sql.connect('database.db')
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT, password TEXT);")
        cur.execute('SELECT * FROM users WHERE username=? OR email=?', (username, email))
        account = cur.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
            password = hash_password(password)
            cur.execute('INSERT INTO  users VALUES (NULL,?, ?, ?)', (username, password, email,))
            msg = 'You have successfully registered !'
            return render_template('index.html')  
        
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)



@app.route('/upload', methods =['GET', 'POST'])
async def upload():
    if request.method == "POST":
        f = request.files['file']
        f.save('image.png')
        image_ = f
        submit= ''
        try:
            image = Image.open('image.png')
            image = np.array(image)
            inference(image=image)
            submit= 'View Your Image'
            from flask import send_from_directory
            return send_from_directory("static", "output.png"), render_template('index.html')
        except ValueError:
            vals = "Error! Please upload a valid image type."
            return vals

def delete_file():
    if os.path.exists('static/output.png'):
        os.remove('static/output.png')
        print('file removed')

@app.route('/output')
def output():
    return 'output.png', delete_file()
    
#     return send_from_directory(filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')