import os

# Base paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
STAGING_DIR = os.path.join(PROJECT_ROOT, "data", "staging")

# API Configuration
OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPENMETEO_MARINE_ARCHIVE_URL = "https://marine-api.open-meteo.com/v1/marine"

OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_MARINE_FORECAST_URL = "https://marine-api.open-meteo.com/v1/marine"

# Budgets
MAX_CALLS_PER_MINUTE = 100
MAX_CALLS_PER_HOUR = 1000
MAX_CALLS_PER_DAY = 5000
MAX_CALLS_PER_MONTH = 150000

# Constants
START_DATE = "2010-01-01"
TIMEZONE = "Asia/Colombo"

# Variables
ATMOSPHERE_DAILY = [
    "precipitation_sum", "precipitation_hours",
    "wind_speed_10m_max", "wind_speed_10m_mean", "wind_direction_10m_dominant",
    "temperature_2m_mean", "temperature_2m_max", "temperature_2m_min",
    "relative_humidity_2m_mean", "pressure_msl_mean"
]

MARINE_DAILY = [
    "wave_height_max", "wave_period_max", "wave_direction_dominant"
]

