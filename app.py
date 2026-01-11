from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

@app.get("/predictions", response_model=List[dict])
def read_predictions(db: Session = Depends(database.get_db)):
    predictions = db.query(database.Prediction).order_by(database.Prediction.created_at.desc()).limit(20).all()
    return [{
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

@app.get("/stats")
def read_stats():
    import json
    try:
        with open("bot_stats.json", "r") as f:
            return json.load(f)
    except:
        return {"error": "Stats file not found"}

# Mount files from the root for the dashboard
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
