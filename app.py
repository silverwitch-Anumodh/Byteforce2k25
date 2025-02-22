from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import pandas as pd
from sklearn.utils import resample  # <-- Add this import

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # SQLite database
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        news_text = request.form['news_text']
        prediction = predict_news(news_text)
        if prediction == "FAKE":
            query = " ".join(news_text.split()[:5])  # Use first 5 words as search query
            real_news_title, real_news_url = get_real_news(query)
            return render_template('result.html', prediction=prediction, real_news_title=real_news_title, real_news_url=real_news_url)
        else:
            return render_template('result.html', prediction=prediction, real_news_title=None, real_news_url=None)
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
            return redirect(url_for('home'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Profile route
@app.route('/profile')
@login_required  # Only logged-in users can access this route
def profile():
    return render_template('profile.html', user=current_user)

# Fake News Detection Code
# Load fake news dataset
df = pd.read_csv('fake_news_dataset.csv')  # Replace with your dataset path

# ====== FIXED CODE TO BALANCE THE DATASET ======
# Separate FAKE and REAL news
fake_df = df[df['label'] == 'FAKE']
real_df = df[df['label'] == 'REAL']

# Make both FAKE and REAL news equal in number (with replacement)
balanced_df = pd.concat([fake_df, real_df.sample(len(fake_df), replace=True)])

# Use the balanced dataset
X = balanced_df['text']
y = balanced_df['label']
# ===============================================

# Train the model
tfidf = TfidfVectorizer(stop_words='english', max_df=0.7)
X_tfidf = tfidf.fit_transform(X)
model = PassiveAggressiveClassifier(max_iter=50)
model.fit(X_tfidf, y)

# Function to predict if news is fake or real
def predict_news(text):
    text_tfidf = tfidf.transform([text])
    prediction = model.predict(text_tfidf)
    return prediction[0]

# ====== TEST THE MODEL ======
# Test with a REAL news example
real_news = "Scientists discovered a new species of butterfly."
print(predict_news(real_news))  # Should say "REAL"

# Test with a FAKE news example
fake_news = "Aliens landed in New York City."
print(predict_news(fake_news))  # Should say "FAKE"
# ============================

# Function to fetch real news from NewsAPI
def get_real_news(query):
    api_key = "2663da56477343a69c9dd02bc5931904" 
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey={api_key}"
    response = requests.get(url)
    data = response.json()
    if data['articles']:
        return data['articles'][0]['title'], data['articles'][0]['url']
    else:
        return None, None

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)