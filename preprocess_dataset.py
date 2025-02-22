import pandas as pd

# Load fake and real news datasets
fake_df = pd.read_csv('Fake.csv')
true_df = pd.read_csv('True.csv')

# Add labels to the datasets
fake_df['label'] = 'FAKE'
true_df['label'] = 'REAL'

# Combine the datasets
df = pd.concat([fake_df, true_df], ignore_index=True)

# Save the combined dataset
df.to_csv('fake_news_dataset.csv', index=False)
print("Dataset preprocessed and saved as 'fake_news_dataset.csv'")