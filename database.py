import os
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./norra_ai.db")

# Resolve compatibility between older connection strings and SQLAlchemy v2+
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, unique=True, index=True)
    home_team = Column(String)
    away_team = Column(String)
    league_name = Column(String)
    prediction_main = Column(String)
    confidence = Column(String)
    dc = Column(String)
    ht = Column(String)
    ou_refined = Column(String)
    star_power = Column(String)
    h2h_dom = Column(Integer)
    btts = Column(String)
    dnb = Column(String)
    multi_goals = Column(String)
    ht_ft = Column(String)
    combos = Column(String)
    league_avg_goals = Column(Float)
    match_date = Column(DateTime, nullable=True)
    actual_home_goals = Column(Integer, nullable=True)
    actual_away_goals = Column(Integer, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MatchTrainingData(Base):
    __tablename__ = "match_training_data"

    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, unique=True, index=True)
    league_id = Column(Integer)
    home_rank = Column(Integer)
    away_rank = Column(Integer)
    home_motivation = Column(Float)
    away_motivation = Column(Float)
    home_star_power = Column(Float)
    home_defensive_wall = Column(Float)
    h2h_dominance = Column(Integer)
    home_advantage = Column(Integer)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    result = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PlayedMatch(Base):
    __tablename__ = "played_matches"

    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, unique=True, index=True)
    league_id = Column(Integer, index=True)
    season = Column(String)
    match_date = Column(DateTime)
    home_team = Column(String, index=True)
    away_team = Column(String, index=True)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class BotStats(Base):
    __tablename__ = "bot_stats"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) # e.g. "global_stats"
    data = Column(JSON) # Dict storing stats and predictions_to_verify
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class PostTimeline(Base):
    __tablename__ = "post_timeline"

    id = Column(Integer, primary_key=True, index=True)
    fixture_id = Column(Integer, index=True)
    platform = Column(String) # "X" or "Telegram"
    content = Column(String)
    link = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Check and migrate schema for existing databases in a dialect-agnostic way
    from sqlalchemy import inspect, text
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        columns = [col["name"] for col in inspector.get_columns("predictions")]
        if "league_avg_goals" not in columns:
            print("Migration: Adding 'league_avg_goals' column to 'predictions' table...")
            db.execute(text("ALTER TABLE predictions ADD COLUMN league_avg_goals FLOAT;"))
            db.commit()
        if "match_date" not in columns:
            print("Migration: Adding 'match_date' column to 'predictions' table...")
            db.execute(text("ALTER TABLE predictions ADD COLUMN match_date TIMESTAMP;"))
            db.commit()
        if "actual_home_goals" not in columns:
            print("Migration: Adding 'actual_home_goals' column to 'predictions' table...")
            db.execute(text("ALTER TABLE predictions ADD COLUMN actual_home_goals INTEGER;"))
            db.commit()
        if "actual_away_goals" not in columns:
            print("Migration: Adding 'actual_away_goals' column to 'predictions' table...")
            db.execute(text("ALTER TABLE predictions ADD COLUMN actual_away_goals INTEGER;"))
            db.commit()
        if "status" not in columns:
            print("Migration: Adding 'status' column to 'predictions' table...")
            db.execute(text("ALTER TABLE predictions ADD COLUMN status VARCHAR(20) DEFAULT 'pending';"))
            db.commit()
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

