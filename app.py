from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')  # Use environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # SQLite database
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Fetch NewsAPI key from environment variables
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

# Claim History model
class ClaimHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    claim = db.Column(db.String(500), nullable=False)
    result = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        claim = request.form['claim']

        # Check if the user is logged in
        if current_user.is_authenticated:
            # Logged-in users get unlimited searches
            prediction = verify_claim(claim)
            articles = fetch_evidence(claim)

            # Save claim history for logged-in users
            history = ClaimHistory(user_id=current_user.id, claim=claim, result=prediction)
            db.session.add(history)
            db.session.commit()

            return render_template('result.html', prediction=prediction, articles=articles)
        else:
            # Guests get a limited number of searches
            if 'search_count' not in session:
                session['search_count'] = 0

            if session['search_count'] >= 5:
                flash('You have reached the search limit for guests. Please log in for unlimited searches.', 'warning')
                return redirect(url_for('login'))

            # Increment search count for guests
            session['search_count'] += 1

            prediction = verify_claim(claim)
            articles = fetch_evidence(claim)
            return render_template('result.html', prediction=prediction, articles=articles)

    return render_template('index.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            session.pop('search_count', None)  # Reset search count
            return redirect(url_for('home'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('search_count', None)  # Clear search count
    return redirect(url_for('home'))

# Profile route
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Change Password route
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if the old password is correct
        if not bcrypt.check_password_hash(current_user.password, old_password):
            flash('Incorrect old password. Please try again.', 'danger')
            return redirect(url_for('change_password'))

        # Check if the new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match. Please try again.', 'danger')
            return redirect(url_for('change_password'))

        # Update the password
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('home'))

    return render_template('change_password.html')

# Search route
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        query = request.form.get('query')
        claims = ClaimHistory.query.filter(ClaimHistory.claim.contains(query)).all()
        return render_template('search.html', claims=claims)
    return render_template('search.html')

# Fact-Checking Code
# Load dataset (replace with your fact-checking dataset)
df = pd.read_csv('fmt_checking_dataset.csv')  # Dataset with claims and labels (TRUE, FALSE, UNVERIFIED)

# Balance the dataset (if needed)
fake_df = df[df['label'] == 'FALSE']
true_df = df[df['label'] == 'TRUE']
balanced_df = pd.concat([fake_df, true_df.sample(len(fake_df), replace=True)])

# Use the balanced dataset
X = balanced_df['text']
y = balanced_df['label']

# Train the model
tfidf = TfidfVectorizer(stop_words='english', max_df=0.7)
X_tfidf = tfidf.fit_transform(X)
model = PassiveAggressiveClassifier(max_iter=50)
model.fit(X_tfidf, y)

# Function to verify a claim
def verify_claim(claim):
    claim_tfidf = tfidf.transform([claim])
    prediction = model.predict(claim_tfidf)
    return prediction[0]

# Function to fetch evidence for claims
def fetch_evidence(claim, num_articles=5):
    try:
        url = f"https://newsapi.org/v2/everything?q={claim}&apiKey={NEWSAPI_KEY}&pageSize={num_articles}"
        response = requests.get(url)
        response.raise_for_status()  # Check for errors
        data = response.json()
        if data.get('articles'):
            return [(article['title'], article['url']) for article in data['articles']]
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching evidence: {e}")
        return None

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)