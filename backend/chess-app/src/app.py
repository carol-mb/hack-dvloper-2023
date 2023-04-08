from flask import Flask, request, session, redirect, jsonify
import bcrypt
import sqlite3

app = Flask(__name__)
app.secret_key = "mysecretkey"

# Define a function to connect to the SQLite database
def get_db():
    conn = sqlite3.connect("users.db")
    return conn

# Define a function to create the users table
def create_users_table():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, salt TEXT)")
    conn.commit()
    conn.close()

# Define a function to insert a user into the users table
def insert_user(username, password):
    conn = get_db()
    c = conn.cursor()
    salt = bcrypt.gensalt(12)
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    c.execute("INSERT INTO users (username, password, salt) VALUES (?, ?, ?)", (username, hashed_password, salt))
    conn.commit()
    conn.close()

# Define a function to retrieve a user from the users table
def get_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if user and bcrypt.checkpw(password.encode('utf-8'), user[2]):
        return user
    else:
        return None

# Route for handling login requests
import json

@app.route("/login", methods=["POST"])
def login():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)
    username = json_data["username"]
    password = json_data["password"]
    user = get_user(username, password)
    if user:
        session["username"] = username
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "failure", "message": "Invalid username or password"})

# Route for handling sign-up requests
@app.route("/signup", methods=["POST"])
def signup():
    username = request.json["username"]
    password = request.json["password"]
    insert_user(username, password)
    session["username"] = username
    return jsonify({"status": "success"})

# Route for handling logout requests
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/")

# Route for displaying the main page
@app.route("/")
def index():
    if "username" in session:
        return jsonify({"username": session["username"]})
    else:
        return jsonify({"message": "Not logged in"})

if __name__ == "__main__":
    create_users_table()
    insert_user("testuser", "testpass")
    app.run(debug=True)