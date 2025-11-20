# prediction_model.py

# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from football_api import fetch_team_data
import datetime
from football_api import get_fixtures

def fetch_and_prepare_data(api_key, league_ids):
    all_data = []
    
    for league_id in league_ids:
        fixtures_data = get_fixtures(league_id, datetime.datetime.now().date(), api_key=api_key)
        if fixtures_data:
            # Process fixtures data and extract relevant features
            league_data = process_fixtures_data(fixtures_data)
            all_data.extend(league_data)

    return all_data

def process_fixtures_data(fixtures_data):
    processed_data = []

    for fixture in fixtures_data:
        # Extract relevant features from fixtures_data and structure them
        # Adjust this part based on your data structure
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "Home")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "Away")
        result = fixture.get("goals", {}).get("home", 0) - fixture.get("goals", {}).get("away", 0)

        # Add more features as needed

        # Structure the data
        data_point = {
            "home_team": home_team,
            "away_team": away_team,
            "result": result
            # Add more features here
        }

        processed_data.append(data_point)

    return processed_data

def preprocess_data(data):
    # Placeholder for data preprocessing logic
    # Replace with your actual preprocessing steps
    # For simplicity, we assume the data is already in a suitable format
    preprocessed_data = data
    return preprocessed_data

def train_model(data):
    # Extract features and labels from the data
    features = data.drop(columns=['result'])
    labels = data['result']

    # Split the data into training and testing sets
    train_features, test_features, train_labels, test_labels = train_test_split(features, labels, test_size=0.2, random_state=42)

    # Initialize and train the Random Forest Classifier
    model = RandomForestClassifier(random_state=42)
    model.fit(train_features, train_labels)

    return model

def extract_features(stats):
    # Placeholder for extracting features from team statistics
    # Replace with your actual feature extraction logic
    # For simplicity, we assume 'total_goals' and 'total_shots' as features
    features = [stats.get('goals', 0), stats.get('shots', 0)]
    return features

def extract_label(stats):
    # Placeholder for extracting labels from team statistics
    # Replace with your actual label extraction logic
    # For simplicity, we assume 'win' as the label
    label = 1 if stats.get('win', 0) else 0
    return label

def evaluate_model(model, test_data):
    # Function to evaluate the model's performance
    # Add logic to evaluate the model's performance on a test data set

    return model_performance  # Return the model's performance metrics
def make_predictions(model, new_data):
    # Placeholder for making predictions using the trained model
    # Replace with your actual prediction logic
    predictions = {}

    for league_id, team_data in new_data.items():
        for team_id, stats in team_data.items():
            # Extract relevant features for prediction
            features = extract_features(stats)

            # Make a prediction using the trained model
            prediction = model.predict([features])[0]
            predictions[(league_id, team_id)] = prediction

    return predictions

def main(api_key, league_ids):
    fetched_data = fetch_and_prepare_data(api_key, league_ids)
    processed_data = preprocess_data(fetched_data)

    # Split data for training and testing
    train, test = train_test_split(processed_data, test_size=0.2, random_state=42)

    # Train the model
    model = train_model(train)

    # Fetch new data for predictions
    new_data = fetch_and_prepare_data(api_key, league_ids)

    # Make predictions
    predictions = make_predictions(model, new_data)
    return predictions

if __name__ == "__main__":
    api_key = "008362339amsh83fe9d1584cd2e8p150ebejsnd291e823113c"
    league_ids = [2, 3, 848, 39, 40, 78, 140, 135, 61, 94, 203, 399]
    # Fetch, preprocess, and train the model
    fetched_data = fetch_and_prepare_data(api_key, league_ids)
    processed_data = preprocess_data(fetched_data)
    model = train_model(processed_data)

# New data for prediction from the football API
    new_data = fetch_and_prepare_data(api_key, league_ids)

# Make predictions using the trained model
    predictions = make_predictions(model, new_data)
    # Run the main function
    main(api_key, league_ids)
    print(predictions)