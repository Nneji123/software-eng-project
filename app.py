import re
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3 as sql
import cv2
import io
from PIL import Image
import numpy as np
from utils import *
import bcrypt

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
        print(password)
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        account = cur.fetchone()

        if account and check_password_hashed(hash_password(password))==True:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # session['email'] = account['email']
            msg = 'Logged in successfully !'
            return render_template('index.html')
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
        con.commit()
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
            cur.execute('INSERT INTO  users VALUES (NULL,?, ?, ?)', (username, email, password, ))
            con.commit()
            msg = 'You have successfully registered !'
            return render_template('index.html')  
        
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)

import os
from flask import Flask, request, redirect, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import base64
from io import BytesIO


allowed_exts = {'jpg', 'jpeg','png','JPG','JPEG','PNG'}


def check_allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts



@app.route("/index",methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		if 'file' not in request.files:
			print('No file attached in request')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			print('No file selected')
			return redirect(request.url)
		if file and check_allowed_file(file.filename):
			filename = secure_filename(file.filename)
			print(filename)
			img = Image.open(file.stream).resize((320,320))
            
			with BytesIO() as buf:
				img.save(buf, 'jpeg')
				image_bytes = buf.getvalue()
			encoded_string = base64.b64encode(image_bytes).decode()         
		return render_template('index.html', img_data=encoded_string), 200
	else:
		return render_template('index.html', img_data=""), 200



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')