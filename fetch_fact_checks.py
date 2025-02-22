import pandas as pd
import requests

# Google Fact Check Tools API endpoint
API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
API_KEY = "AIzaSyDxMcAbYq3WkrdOKT6mnl6KwRVlq0FQIaY"  

# Function to fetch fact-checked claims
def fetch_fact_checks(query, max_results=10):
    params = {
        "query": query,
        "key": API_KEY,
        "pageSize": max_results,
        "languageCode": "en"
    }
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json().get("claims", [])
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

# Function to format fetched data
def format_fact_checks(claims):
    data = []
    for claim in claims:
        text = claim.get("text", "")
        claim_review = claim.get("claimReview", [{}])[0]
        label = claim_review.get("textualRating", "UNVERIFIED").upper()
        data.append({"text": text, "label": label})
    return data

# Fetch fact-checked claims
query = "COVID-19"  # Replace with your desired query
claims = fetch_fact_checks(query)

# Format the fetched data
new_data = format_fact_checks(claims)

# Load existing dataset (if any)
try:
    df = pd.read_csv("fmt_checking_dataset.csv")
except FileNotFoundError:
    df = pd.DataFrame(columns=["text", "label"])

# Add new data to the dataset
new_df = pd.DataFrame(new_data)
df = pd.concat([df, new_df], ignore_index=True)

# Save the updated dataset
df.to_csv("fmt_checking_dataset.csv", index=False)

print(f"Added {len(new_data)} new claims to fmt_checking_dataset.csv")