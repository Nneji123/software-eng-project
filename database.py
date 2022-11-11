import sqlite3 as sql


username='if'
password='linda3'
email='ifeanyii777@gl.com'
con = sql.connect('database.db')
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT, password TEXT);")
cur.execute('INSERT INTO  users VALUES (NULL,?, ?, ?)', (username, email, password, ))
cur.execute('SELECT * FROM users')
account = cur.fetchall()
print(account)