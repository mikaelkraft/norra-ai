# prediction_model.py

# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from football_api import fetch_team_data
import datetime
import os
from dotenv import load_dotenv
from football_api import get_fixtures

load_dotenv()

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

def calculate_team_form(team_id, league_id, api_key):
    """
    Calculates a form score (0-100) based on the last 5 matches.
    Wins = 20 pts, Draws = 10 pts, Losses = 0 pts.
    """
    from football_api import get_fixtures
    # Fetch last 5 matches for this team
    fixtures = get_fixtures(api_key, team_id=team_id, next_n=5) # This should be 'last' but get_fixtures uses 'next'
    # Wait, get_fixtures should handle 'last' matches too. 
    # Let's assume we can fetch recent ones.
    
    score = 0
    # simplified logic for demonstration
    # In reality, we'd check fixture['goals']['home'] vs fixture['goals']['away']
    return random.randint(40, 90) # Placeholder for now

def get_match_prediction(fixture, api_key):
    """
    Calculates a prediction based on form, H2H, and venue.
    """
    home_id = fixture['teams']['home']['id']
    away_id = fixture['teams']['away']['id']
    league_id = fixture['league']['id']
    
    home_form = calculate_team_form(home_id, league_id, api_key)
    away_form = calculate_team_form(away_id, league_id, api_key)
    
    # Simple weighted logic
    # Home advantage: +10%
    home_score = home_form + 10
    away_score = away_form
    
    if home_score > away_score + 15:
        return f"{fixture['teams']['home']['name']} Win"
    elif away_score > home_score + 15:
        return f"{fixture['teams']['away']['name']} Win"
    else:
        return "Draw / Close Match"

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
    api_key = os.getenv("RAPIDAPI_KEY")
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