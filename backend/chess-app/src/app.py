#!/usr/bin/python3

from flask import Flask, request, session, redirect, jsonify
import sqlite3
import bcrypt
from ctypes import *
import chess
import chess.engine
from stockfish import Stockfish

(BLACK, WHITE) = (0, 1)
(PAWN, BISHOP, KNIGHT, KING, QUEEN, ROOK) = (0, 1, 2, 3, 4, 5)

class Piece(Structure):
    _fields_ = [
        ('color', c_int),
        ('type', c_int),
        ('hasMoved', c_int),
    ]


chessSDK = CDLL("./table.so")  

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

@app.route("/api/login", methods=["POST"])
def login():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)
    username = json_data["username"]
    password = json_data["password"]
    user = get_user(username, password)
    if user:
        session["username"] = username
        return jsonify({"status": "success", "username": username})
    else:
        return jsonify({"status": "failure", "message": "Invalid username or password"})

# Route for handling sign-up requests
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)
    insert_user(json_data["username"], json_data["password"])
    session["username"] = json_data["username"]
    return jsonify({"status": "success", "username": json_data["username"]})

# Route for handling logout requests
@app.route("/api/logout", methods = ["GET"])
def logout():
    session.pop("username", None)
    return jsonify({"status": "success"})

# Route for displaying the main page
@app.route("/api/")
def index():
    if "username" in session:
        return jsonify({"username": session["username"]})
    else:
        return jsonify({"message": "Not logged in"})

# Play the game
def print_board(board):
    with open('matrix.txt', 'w') as f:
        for row in range(8):
            for col in range(8):
                piece = board.piece_at(chess.square(row, col))
                if piece is not None:
                    color = "WHITE" if piece.color == chess.WHITE else "BLACK"
                    piece_str = f"{color}_{chess.PIECE_NAMES[piece.piece_type].upper()}"
                    x, y = row, col
                    f.write(f"{piece_str},{x},{y}\n")

@app.route("/api/createGame", methods = ['GET'])
def createGame():
    # chessSDK.init_matrix.restype = POINTER(POINTER(Piece))
    # chessboard = chessSDK.init_matrix()
    board = chess.Board()
    print_board(board)
    conn = get_db()
    c = conn.cursor()

    chessboard = []
    with open("matrix.txt", "r") as infile:
        for i in range(0, 8):
            chessboard.append([])
            for _ in range(0, 8):
                chessboard[i].append(None)
        for line in infile:
            (piece, j, i) = line.split(",")
            print(piece, i, j)
            print(chessboard)
            chessboard[int(i)][int(j)] = piece

    pieces = []
    for i in range(0, 8):
        for j in range(0, 8):
            if chessboard[i][j] is not None:
                position = chr(ord('A') + j) + str(i + 1)
                pieces.append({
                    "position": position,
                    "type": chessboard[i][j]
                })
    c.execute("CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY, white_id INTEGER, black_id INTEGER, FOREIGN KEY (white_id) REFERENCES users(id), FOREIGN KEY (black_id) REFERENCES users(id))")
    c.execute("INSERT INTO games (white_id, black_id) VALUES (?, ?)", (1, 2))
    c.execute("SELECT last_insert_rowid()")
    conn.commit()
    row = c.fetchone()
    inserted_id = row[0]
    conn.close()
    
    return jsonify({"pieces": pieces, "game_id": inserted_id})

def print_board(board):
    with open('matrix.txt', 'w') as f:
        for row in range(8):
            for col in range(8):
                square = chess.square(col, 7-row)
                piece = board.piece_at(square)
                if piece is not None:
                    piece_str = chess.COLOR_NAMES[piece.color].upper() + "_" + chess.PIECE_NAMES[piece.piece_type].upper()
                    x, y = chess.square_file(square), chess.square_rank(square)
                    print(f"{piece_str},{x},{y}", file=f)

@app.route("/api/checkMove", methods = ['POST'])
def checkMove():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)
    print(json_data["history"])
    board = chess.Board()
    print("AICI IGL", json_data["history"])
    for piece in json_data["history"]:
        move = (piece["from"] + piece["to"]).lower()
        chess_move = chess.Move.from_uci(move)
        legal_moves = list(board.legal_moves)
        print()
        print(chess_move) 
        print(legal_moves)
        if chess_move in legal_moves:
            print(board)
            board.push(chess_move)
            print(board)
            print(json_data["history"])
        else:
            print(board)
            return jsonify({"isValid": False})
    
    return jsonify({"isValid": True})

@app.route("/api/saveMove", methods = ['POST'])
def saveMove():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)

    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS moves (id INTEGER PRIMARY KEY, game_id INTEGER, piece TEXT, positionFrom TEXT, positionTo TEXT)")
    c.execute("INSERT INTO moves (game_id, piece, positionFrom, positionTo) VALUES (?, ?, ?, ?)", (json_data["game_id"], json_data["piece"], json_data["positionFrom"], json_data["positionTo"]))
    conn.commit()
    return jsonify({"status": "success"})

@app.route("/api/loadGame", methods = ['POST'])
def loadGame():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM moves WHERE game_id = (?)", (json_data["game_id"],))
    moves = c.fetchall()
    history = []
    for move in moves:
        history.append({
            "pieceType": move[2],
            "from": move[3],
            "to": move[4]
        })
    return jsonify({"history": history})

@app.route("/api/saveMessage", methods = ['POST'])
def saveMessage():
    data = request.data.decode('utf-8')
    json_data = json.loads(data)

    conn = get_db()
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, username TEXT, meesage TEXT, game_id INTEGER, FOREIGN KEY (game_id) REFERENCES games(id))")

if __name__ == "__main__":
    create_users_table()
    insert_user("testuser", "testpass")
    app.run(debug=True)
