import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if it exists
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Application configuration with secure defaults and database fallbacks."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "agripredict_dev_secret_key_change_in_production_98234")
    
    # MySQL Database credentials
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "agripredict_db")
    
    # Primary MySQL Connection URI
    # mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>
    MYSQL_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    
    # SQLite fallback URI in case MySQL server is not active
    SQLITE_DATABASE_URI = f"sqlite:///{BASE_DIR / 'agripredict_fallback.db'}"
    
    # Set SQLALCHEMY_DATABASE_URI default
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", MYSQL_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    # External APIs
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    SENTINEL_CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID", "")
    SENTINEL_CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET", "")
    AGROMONITORING_API_KEY = os.getenv("AGROMONITORING_API_KEY", "")
    
    # Simulation / Demo Fallback toggle
    ENABLE_API_DEMO_FALLBACK = os.getenv("ENABLE_API_DEMO_FALLBACK", "True").lower() in ("true", "1", "t", "yes")

    # ML Model Path
    MODEL_PATH = BASE_DIR / "models" / "crop_yield_model.joblib"
    DATA_PATH = BASE_DIR / "data" / "crop_yield_dataset.csv"
