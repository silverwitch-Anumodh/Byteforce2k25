import pandas as pd

# Load fake and real news datasets
fake_df = pd.read_csv('Fake.csv')
true_df = pd.read_csv('True.csv')

# Add labels to the datasets
fake_df['label'] = 'FAKE'
true_df['label'] = 'REAL'

# Combine the datasets
df = pd.concat([fake_df, true_df], ignore_index=True)

# Save the combined dataset (optional)
df.to_csv('fake_news_dataset.csv', index=False)


from flask import Flask, request, render_template
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import pandas as pd

# Load fake news dataset 
# Load the combined dataset
df = pd.read_csv('fake_news_dataset.csv')

# Use the 'text' column for training
X = df['text']
y = df['label']

# Train a simple fake news detection model
tfidf = TfidfVectorizer(stop_words='english', max_df=0.7)
X_tfidf = tfidf.fit_transform(X)
model = PassiveAggressiveClassifier(max_iter=50)
model.fit(X_tfidf, y)

# Function to predict if news is fake or real
def predict_news(text):
    text_tfidf = tfidf.transform([text])
    prediction = model.predict(text_tfidf)
    return prediction[0]

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

# Flask app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
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

if __name__ == '__main__':
    app.run(debug=True)