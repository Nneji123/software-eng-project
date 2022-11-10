import sqlite3 as sql

def insert_user(username: str, email: str, password: str):
    con = sql.connect("database.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, email TEXT NOT NULL, password TEXT NOT NULL);")
    cur.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", (username, email, password))
    con.commit()
    con.close()

def retrieve_users():
	con = sql.connect("database.db")
	cur = con.cursor()
	cur.execute("SELECT username, email, password FROM users")
	users = cur.fetchone()
	con.close()
	return [users]

insert_user("ifeanyi", "ifeanyinneji777@gmail.com", "linda321")