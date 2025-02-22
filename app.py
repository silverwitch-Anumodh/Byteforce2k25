from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
import requests
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)  # Session expires after 30 minutes

# Database setup
def get_db_connection():
    conn = sqlite3.connect('factchecker.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Fetch real articles from Google
def fetch_google_articles(query):
    api_key = 'AIzaSyDxMcAbYq3WkrdOKT6mnl6KwRVlq0FQIaY'  # Replace with your Google API key
    cx = 'e45d94a7a7ec0486a'  # Replace with your Custom Search Engine ID
    url = f'https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cx}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        articles = []
        for item in data.get('items', []):
            articles.append({
                "title": item.get('title'),
                "snippet": item.get('snippet'),
                "link": item.get('link')
            })
        return articles
    return []

# Routes
@app.route('/')
def home():
    logged_in = 'user_id' in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/search')
def search():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Check search limit for non-logged-in users
    if 'user_id' not in session:
        conn = get_db_connection()
        search_count = conn.execute('SELECT COUNT(*) FROM searches WHERE user_id IS NULL').fetchone()[0]
        if search_count >= 5:
            return jsonify({"error": "Search limit reached. Please log in."}), 403

    # Save search query
    user_id = session.get('user_id')
    conn = get_db_connection()
    conn.execute('INSERT INTO searches (user_id, query) VALUES (?, ?)', (user_id, query))
    conn.commit()
    conn.close()

    # Fetch real articles from Google
    articles = fetch_google_articles(query)
    return jsonify({"articles": articles})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        return "Invalid credentials", 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists", 400
        finally:
            conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    searches = conn.execute('SELECT * FROM searches WHERE user_id = ? ORDER BY timestamp DESC', (user_id,)).fetchall()
    conn.close()

    return render_template('history.html', searches=searches)

if __name__ == '__main__':
    app.run(debug=True)