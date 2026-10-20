"""
AgriPredict AI - Database Models
Defines User and Prediction entities with SQLAlchemy ORM,
secure password hashing via Werkzeug, and relational constraints.
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    """Registered application user entity."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    predictions = db.relationship(
        "Prediction", 
        backref="user", 
        cascade="all, delete-orphan", 
        lazy=True,
        order_by="desc(Prediction.created_at)"
    )

    def set_password(self, password: str):
        """Generates a secure cryptographic password hash."""
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        """Verifies candidate plaintext password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }


class Prediction(db.Model):
    """Historical crop yield prediction record."""
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_type = db.Column(db.String(50), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False) # State
    district = db.Column(db.String(100), nullable=True)
    land_area = db.Column(db.Float, nullable=False) # In hectares
    season = db.Column(db.String(50), nullable=False)
    soil_type = db.Column(db.String(50), nullable=False)
    avg_temp = db.Column(db.Float, nullable=False) # °C
    rainfall = db.Column(db.Float, nullable=False) # mm
    humidity = db.Column(db.Float, nullable=False) # %
    soil_moisture = db.Column(db.Float, nullable=True) # %
    ndvi = db.Column(db.Float, nullable=True) # Normalized index [0-1]
    predicted_yield = db.Column(db.Float, nullable=False) # tonnes/ha
    estimated_total_production = db.Column(db.Float, nullable=False) # tonnes
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "crop_type": self.crop_type,
            "location": self.location,
            "district": self.district or "",
            "land_area": self.land_area,
            "season": self.season,
            "soil_type": self.soil_type,
            "avg_temp": self.avg_temp,
            "rainfall": self.rainfall,
            "humidity": self.humidity,
            "soil_moisture": self.soil_moisture,
            "ndvi": self.ndvi,
            "predicted_yield": self.predicted_yield,
            "estimated_total_production": self.estimated_total_production,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "formatted_date": self.created_at.strftime("%b %d, %Y")
        }
