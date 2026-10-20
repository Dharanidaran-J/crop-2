-- AgriPredict AI - MySQL Database Schema
-- Database Name: agripredict_db

CREATE DATABASE IF NOT EXISTS agripredict_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE agripredict_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    crop_type VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    district VARCHAR(100) DEFAULT NULL,
    land_area DECIMAL(10, 2) NOT NULL COMMENT 'Cultivated land area in hectares',
    season VARCHAR(50) NOT NULL,
    soil_type VARCHAR(50) NOT NULL,
    avg_temp DECIMAL(5, 2) NOT NULL COMMENT 'Temperature in Celsius',
    rainfall DECIMAL(7, 2) NOT NULL COMMENT 'Rainfall in mm',
    humidity DECIMAL(5, 2) NOT NULL COMMENT 'Relative humidity in %',
    soil_moisture DECIMAL(5, 2) DEFAULT NULL COMMENT 'Soil moisture in %',
    ndvi DECIMAL(4, 3) DEFAULT NULL COMMENT 'Normalized Difference Vegetation Index (0.0 to 1.0)',
    predicted_yield DECIMAL(10, 2) NOT NULL COMMENT 'Predicted yield in tonnes per hectare',
    estimated_total_production DECIMAL(12, 2) NOT NULL COMMENT 'Total production in tonnes (yield * area)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_prediction FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes for optimized querying
CREATE INDEX idx_user_id ON predictions(user_id);
CREATE INDEX idx_crop_type ON predictions(crop_type);
CREATE INDEX idx_created_at ON predictions(created_at);
