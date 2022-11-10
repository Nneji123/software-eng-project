import re
from flask import Flask, render_template, request, redirect, url_for, session
from database import insert_user, retrieve_users
import sqlite3 as sql
import cv2
import io
from PIL import Image
from utils import *

app = Flask(__name__)
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
        cur.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        account = cur.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['email'] = account['email']
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
        # account = retrieve_users()
        con = sql.connect('database.db')
        cur = con.cursor()
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
            cur.execute('INSERT INTO  users VALUES (NULL, ?, ?, ?)', (username, password, email, ))
            msg = 'You have successfully registered !'
            return render_template('index.html')  
        
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)



@app.route('index', methods=['GET', 'POST'])
async def upload():
    if request.method == "POST":
        form = await request.form()
        submit= ''
        if form["file"]:
            files = form["file"]
            contents = io.BytesIO(await files.read())
            file_bytes = np.asarray(bytearray(contents.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            cv2.imwrite("./images/image.jpg", img)
            try:
                image = Image.open('./images/image.jpg')
                image = np.array(image)
                inference(image=image)
                return submit
            except ValueError:
                vals = "Error! Please upload a valid image type."
                return vals



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')