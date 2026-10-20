"""
AgriPredict AI - Main Flask Application
Full-stack web application for crop yield prediction using weather,
soil characteristics, and satellite NDVI data.
"""

import os
import json
import logging
from functools import wraps
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify, abort
)
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from config import Config
from models_db import db, User, Prediction
from ml.predict import CropYieldPredictor, CROP_BENCHMARKS
from services.weather_service import WeatherService
from services.satellite_service import SatelliteService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AgriPredict")

app = Flask(__name__)
app.config.from_object(Config)

# Database connectivity setup with intelligent fallback
active_db_type = "MySQL"
try:
    # Test MySQL connection
    test_engine = create_engine(Config.MYSQL_DATABASE_URI, connect_args={"connect_timeout": 3})
    with test_engine.connect() as conn:
        logger.info("Successfully connected to primary MySQL database: %s", Config.DB_NAME)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.MYSQL_DATABASE_URI
    active_db_type = "MySQL"
except Exception as e:
    logger.warning("MySQL connection could not be established (%s).", e)
    logger.info("Engaging SQLite fallback engine at: %s", Config.SQLITE_DATABASE_URI)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.SQLITE_DATABASE_URI
    active_db_type = "SQLite (Local Fallback)"

db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error("Error creating database tables: %s", e)


# -------------------------------------------------------------------------
# Authentication Decorator & Helpers
# -------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this feature.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if "user_id" in session:
        return db.session.get(User, session["user_id"])
    return None

@app.context_processor
def inject_global_vars():
    """Injects user context and active database type into all templates."""
    return {
        "current_user": get_current_user(),
        "active_db_type": active_db_type,
        "supported_crops": list(CROP_BENCHMARKS.keys())
    }


# -------------------------------------------------------------------------
# Public Routes
# -------------------------------------------------------------------------
@app.route("/")
def index():
    """Landing Page displaying value proposition, workflow, and model highlights."""
    metrics_path = Config.MODEL_PATH.parent / "metrics.json"
    metrics = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
        except Exception:
            pass

    return render_template("index.html", metrics=metrics)


@app.route("/register", methods=["GET", "POST"])
def register():
    """User account registration with validation and password hashing."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validation
        if not name or len(name) < 2:
            flash("Please enter a valid full name (minimum 2 characters).", "danger")
            return render_template("register.html", name=name, email=email)

        if not email or "@" not in email or "." not in email:
            flash("Please provide a valid email address.", "danger")
            return render_template("register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template("register.html", name=name, email=email)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists. Please log in.", "warning")
            return redirect(url_for("login"))

        new_user = User(name=name, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account registered successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            logger.error("Registration error: %s", e)
            flash("An error occurred during account creation. Please try again.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User authentication and session initialization."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.args.get("next") or url_for("dashboard")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_email"] = user.email
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(next_url)
        else:
            flash("Invalid email or password. Please verify your credentials.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Terminates active session."""
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("index"))


# -------------------------------------------------------------------------
# Core Prediction Routes
# -------------------------------------------------------------------------
@app.route("/predict", methods=["GET", "POST"])
def predict():
    """Crop Yield Prediction form view and calculation handler."""
    if request.method == "POST":
        try:
            # Extract inputs
            crop_type = request.form.get("crop_type", "").strip()
            state = request.form.get("state", "Punjab").strip()
            district = request.form.get("district", "").strip()
            land_area = float(request.form.get("land_area", 1.0))
            season = request.form.get("season", "Kharif").strip()
            soil_type = request.form.get("soil_type", "Alluvial").strip()
            
            temp = float(request.form.get("temperature", 25.0))
            rainfall = float(request.form.get("rainfall", 750.0))
            humidity = float(request.form.get("humidity", 65.0))
            
            soil_moisture = request.form.get("soil_moisture")
            soil_moisture = float(soil_moisture) if soil_moisture else None
            
            ndvi = request.form.get("ndvi")
            ndvi = float(ndvi) if ndvi else None

            # Input validation checks
            if land_area <= 0:
                flash("Cultivated land area must be greater than zero.", "danger")
                return redirect(url_for("predict"))

            # Execute ML model inference
            input_payload = {
                "crop_type": crop_type,
                "state": state,
                "district": district,
                "land_area": land_area,
                "season": season,
                "soil_type": soil_type,
                "temperature": temp,
                "rainfall": rainfall,
                "humidity": humidity,
                "soil_moisture": soil_moisture,
                "ndvi": ndvi
            }

            prediction_result = CropYieldPredictor.predict(input_payload)

            # Persist to database if user is authenticated
            prediction_id = None
            if "user_id" in session:
                record = Prediction(
                    user_id=session["user_id"],
                    crop_type=crop_type,
                    location=state,
                    district=district,
                    land_area=land_area,
                    season=season,
                    soil_type=soil_type,
                    avg_temp=temp,
                    rainfall=rainfall,
                    humidity=humidity,
                    soil_moisture=soil_moisture,
                    ndvi=ndvi,
                    predicted_yield=prediction_result["predicted_yield"],
                    estimated_total_production=prediction_result["estimated_total_production"]
                )
                db.session.add(record)
                db.session.commit()
                prediction_id = record.id

            return render_template(
                "results.html",
                result=prediction_result,
                prediction_id=prediction_id,
                input_data=input_payload
            )

        except Exception as e:
            logger.error("Prediction computation error: %s", e)
            flash(f"Failed to generate prediction: {str(e)}", "danger")
            return redirect(url_for("predict"))

    # GET Request: render form
    # Optional query param to pre-fill district / weather
    preset_city = request.args.get("city", "Ludhiana")
    weather_preview = WeatherService.get_weather(preset_city)
    satellite_preview = SatelliteService.get_satellite_health(preset_city)

    return render_template(
        "predict.html",
        weather_preview=weather_preview,
        satellite_preview=satellite_preview
    )


# -------------------------------------------------------------------------
# Dashboards & User Management
# -------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """Aggregated User Dashboard with statistical overviews and recent queries."""
    user_id = session["user_id"]
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.created_at.desc()).all()

    total_predictions = len(predictions)
    total_area_analyzed = round(sum(p.land_area for p in predictions), 2)
    total_production_projected = round(sum(p.estimated_total_production for p in predictions), 2)

    # Crop frequency breakdown for charts
    crop_counts = {}
    for p in predictions:
        crop_counts[p.crop_type] = crop_counts.get(p.crop_type, 0) + 1

    return render_template(
        "dashboard.html",
        predictions=predictions[:5], # Recent 5
        total_predictions=total_predictions,
        total_area=total_area_analyzed,
        total_production=total_production_projected,
        crop_counts=crop_counts
    )


@app.route("/history")
@login_required
def history():
    """Detailed Prediction History with filtering by crop type and sorting."""
    user_id = session["user_id"]
    crop_filter = request.args.get("crop", "").strip()
    
    query = Prediction.query.filter_by(user_id=user_id)
    if crop_filter:
        query = query.filter_by(crop_type=crop_filter)

    predictions = query.order_by(Prediction.created_at.desc()).all()

    return render_template(
        "history.html",
        predictions=predictions,
        selected_crop=crop_filter
    )


@app.route("/history/delete/<int:pred_id>", methods=["POST"])
@login_required
def delete_prediction(pred_id):
    """Deletes an authorized prediction entry."""
    prediction = Prediction.query.filter_by(id=pred_id, user_id=session["user_id"]).first_or_404()
    try:
        db.session.delete(prediction)
        db.session.commit()
        flash("Prediction entry successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error("Error deleting prediction %d: %s", pred_id, e)
        flash("Failed to delete record.", "danger")
    return redirect(url_for("history"))


# -------------------------------------------------------------------------
# Specialized Meteorological & Satellite Pages
# -------------------------------------------------------------------------
@app.route("/weather")
def weather():
    """Interactive Weather Dashboard with diurnal forecast and agricultural advisories."""
    query = request.args.get("location", "Ludhiana").strip()
    weather_data = WeatherService.get_weather(query)
    return render_template("weather.html", weather=weather_data, current_location=query)


@app.route("/satellite")
def satellite():
    """Satellite Vegetation Health Dashboard featuring Sentinel-2 telemetry."""
    query = request.args.get("location", "Ludhiana").strip()
    satellite_data = SatelliteService.get_satellite_health(query)
    return render_template("satellite.html", satellite=satellite_data, current_location=query)


# -------------------------------------------------------------------------
# JSON REST API Endpoints
# -------------------------------------------------------------------------
@app.route("/api/predict", methods=["POST"])
def api_predict():
    """REST endpoint for automated prediction queries."""
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({"success": False, "error": "No JSON payload provided."}), 400

    try:
        result = CropYieldPredictor.predict(data)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/weather")
def api_weather():
    """REST endpoint for weather data."""
    location = request.args.get("location", "Ludhiana")
    data = WeatherService.get_weather(location)
    return jsonify(data)


@app.route("/api/satellite")
def api_satellite():
    """REST endpoint for satellite telemetry."""
    location = request.args.get("location", "Ludhiana")
    data = SatelliteService.get_satellite_health(location)
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
