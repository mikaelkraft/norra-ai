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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

