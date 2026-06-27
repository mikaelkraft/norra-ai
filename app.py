import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import database
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Norra AI Prediction API")

# Enable CORS for the web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
database.init_db()

@app.get("/predictions")
def read_predictions(db: Session = Depends(database.get_db)):
    predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(20).all()
    formatted_preds = [{
        "fixture_id": p.fixture_id,
        "home": p.home_team,
        "away": p.away_team,
        "league": p.league_name,
        "main": p.prediction_main,
        "conf": p.confidence,
        "dc": p.dc,
        "ht": p.ht,
        "ou": p.ou_refined,
        "stars": p.star_power,
        "h2h": p.h2h_dom,
        "date": p.created_at.strftime("%Y-%m-%d %H:%M")
    } for p in predictions]
    
    last_updated = "Unknown"
    if predictions:
        last_updated = predictions[0].created_at.strftime("%Y-%m-%d %H:%M UTC")
        
    return {
        "last_updated": last_updated,
        "predictions": formatted_preds
    }

@app.get("/stats")
def read_stats():
    from Norra import load_bot_stats
    try:
        return load_bot_stats()
    except Exception as e:
        return {"error": f"Failed to load stats: {e}"}

@app.get("/api/run-predictions")
def run_predictions_endpoint(token: str, background_tasks: BackgroundTasks):
    secure_token = os.getenv("CRON_TOKEN")
    if not secure_token:
        raise HTTPException(status_code=500, detail="CRON_TOKEN env variable not configured on server.")
    
    if token != secure_token:
        raise HTTPException(status_code=401, detail="Unauthorized token.")
    
    # Run in background to prevent client timeouts
    from Norra import verify_previous_matches, fetch_predictions
    
    def run_prediction_job():
        print("Starting background prediction sequence...")
        api_key = os.getenv("FOOTBALL_API_KEY")
        if api_key:
            try:
                verify_previous_matches(api_key)
            except Exception as e:
                print(f"Error in background match verification: {e}")
                
            try:
                fetch_predictions(api_key=api_key, dry_run=False)
            except Exception as e:
                print(f"Error in background prediction run: {e}")
        else:
            print("FOOTBALL_API_KEY missing in background task context.")

    background_tasks.add_task(run_prediction_job)
    return {"status": "started", "message": "Prediction sequence launched in background."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

