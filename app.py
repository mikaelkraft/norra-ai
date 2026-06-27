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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Norra AI API is active. Predictions are available at /predictions and statistics at /stats."
    }

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
        "ou_refined": p.ou_refined,
        "btts": p.btts,
        "dnb": p.dnb,
        "multi_goals": p.multi_goals,
        "ht_ft": p.ht_ft,
        "combos": p.combos,
        "stars": p.star_power,
        "h2h": p.h2h_dom,
        "league_avg_goals": p.league_avg_goals,
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

@app.get("/api/timeline")
def get_timeline(db: Session = Depends(database.get_db)):
    posts = db.query(database.PostTimeline).order_by(database.PostTimeline.created_at.desc()).limit(15).all()
    return [{
        "id": p.id,
        "fixture_id": p.fixture_id,
        "platform": p.platform,
        "content": p.content,
        "link": p.link,
        "date": p.created_at.strftime("%Y-%m-%d %H:%M")
    } for p in posts]

@app.post("/api/post-manual")
def post_manual(fixture_id: int, platform: str, token: str, db: Session = Depends(database.get_db)):
    secure_token = os.getenv("CRON_TOKEN")
    if not secure_token or token != secure_token:
        raise HTTPException(status_code=401, detail="Unauthorized token.")
        
    if platform not in ["X", "Telegram"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Choose 'X' or 'Telegram'.")
        
    pred = db.query(database.Prediction).filter(database.Prediction.fixture_id == fixture_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")
        
    content = f"🛰️ NorraAI VIP Pick! ⚽ {pred.home_team} vs {pred.away_team}\n\n"
    content += f"🔮 Market: {pred.prediction_main} ({pred.confidence})\n"
    content += f"🛡️ DC: {pred.dc} | 💎 O/U: {pred.ou_refined}\n"
    content += f"🌟 Combo: {pred.combos} | 🔮 HT/FT: {pred.ht_ft}\n\n"
    content += "🔗 Visit: norra-ai.vercel.app"

    if platform == "Telegram":
        import telegram_bot
        if telegram_bot.bot and telegram_bot.TELEGRAM_CHANNEL_ID:
            try:
                telegram_bot.bot.send_message(telegram_bot.TELEGRAM_CHANNEL_ID, content, parse_mode="Markdown")
                post_record = database.PostTimeline(fixture_id=fixture_id, platform="Telegram", content=content)
                db.add(post_record)
                db.commit()
                return {"status": "success", "message": "Posted to Telegram successfully!"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Telegram error: {e}")
        else:
            raise HTTPException(status_code=500, detail="Telegram bot credentials unconfigured.")
            
    elif platform == "X":
        import tweepy
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        if not (consumer_key and consumer_secret and access_token and access_token_secret):
            raise HTTPException(status_code=500, detail="Twitter API keys not configured.")
            
        try:
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            response = client.create_tweet(text=content)
            tweet_id = response.data.get("id") if response.data else None
            tweet_link = f"https://x.com/user/status/{tweet_id}" if tweet_id else None
            
            post_record = database.PostTimeline(fixture_id=fixture_id, platform="X", content=content, link=tweet_link)
            db.add(post_record)
            db.commit()
            return {"status": "success", "message": "Posted to X successfully!", "link": tweet_link}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Twitter error: {e}")

from fastapi.responses import HTMLResponse

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(token: str = ""):
    secure_token = os.getenv("CRON_TOKEN", "")
    if not secure_token or token != secure_token:
        return """
        <html>
        <head>
            <title>Norra AI Admin Access</title>
            <style>
                body { font-family: Arial, sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .box { background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; max-width: 400px; width: 100%; }
                input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #475569; border-radius: 6px; background: #0f172a; color: white; box-sizing: border-box; font-size: 16px; }
                button { background: #3b82f6; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; transition: background 0.2s; }
                button:hover { background: #2563eb; }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>Norra AI Admin Access</h2>
                <p style="color: #94a3b8; font-size: 14px;">Enter your admin cron token to access the dashboard.</p>
                <form method="get" action="/admin">
                    <input type="password" name="token" placeholder="Enter Token..." required />
                    <button type="submit">Access Dashboard</button>
                </form>
            </div>
        </body>
        </html>
        """
    
    return f"""
    <html>
    <head>
        <title>Norra AI Admin Panel</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f172a; color: white; padding: 40px; margin: 0; }}
            h1 {{ color: #3b82f6; }}
            .card {{ background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }}
            .btn {{ padding: 10px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: bold; margin-left: 10px; transition: opacity 0.2s; text-decoration: none; display: inline-block; }}
            .btn:hover {{ opacity: 0.9; }}
            .btn-x {{ background: #1da1f2; color: white; }}
            .btn-tg {{ background: #0088cc; color: white; }}
            .info {{ display: flex; flex-direction: column; gap: 5px; }}
            .teams {{ font-size: 18px; font-weight: bold; }}
            .league {{ font-size: 14px; color: #94a3b8; }}
            .options {{ font-size: 14px; color: #e2e8f0; }}
        </style>
        <script>
            async function triggerPost(fixtureId, platform) {{
                const token = "{secure_token}";
                const res = await fetch(`/api/post-manual?fixture_id=${{fixtureId}}&platform=${{platform}}&token=${{token}}`, {{ method: "POST" }});
                const data = await res.json();
                if (data.status === "success") {{
                    alert(`Successfully posted to ${{platform}}!`);
                }} else {{
                    alert(`Error: ${{data.detail}}`);
                }}
            }}
        </script>
    </head>
    <body>
        <h1>🛰️ Norra AI Beacon Force Admin Panel</h1>
        <p style="color: #94a3b8; margin-bottom: 30px;">Direct manual verification and posting engine.</p>
        <div id="predictions-list">
            Loading predictions...
        </div>
        <script>
            async function loadPredictions() {{
                const res = await fetch('/predictions');
                const data = await res.json();
                const list = document.getElementById('predictions-list');
                if (!data.predictions || data.predictions.length === 0) {{
                    list.innerHTML = "<p>No active predictions available to post today.</p>";
                    return;
                }}
                list.innerHTML = "";
                data.predictions.forEach(p => {{
                    const card = document.createElement('div');
                    card.className = "card";
                    card.innerHTML = `
                        <div class="info">
                            <div class="teams">${{p.home}} vs ${{p.away}}</div>
                            <div class="league">${{p.league}} | FT: ${{p.main}} (${{p.conf}}) | Avg Goals: ${{p.league_avg_goals || 'N/A'}}</div>
                            <div class="options">DC: ${{p.dc}} | BTTS: ${{p.btts}} | DNB: ${{p.dnb}} | Combo: ${{p.combos}}</div>
                        </div>
                        <div>
                            <button class="btn btn-x" onclick="triggerPost(${{p.fixture_id}}, 'X')">Post to X</button>
                            <button class="btn btn-tg" onclick="triggerPost(${{p.fixture_id}}, 'Telegram')">Post to Telegram</button>
                        </div>
                    `;
                    list.appendChild(card);
                }});
            }}
            loadPredictions();
        </script>
    </body>
    </html>
    """

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
                # Runs twice daily predictions, filtering and auto-posting only those with confidence > 90%
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

