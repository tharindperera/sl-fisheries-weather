import pyarrow as pa

WEATHER_SCHEMA = pa.schema([
    ("site_id", pa.string()),
    ("date_local", pa.string()),
    ("model", pa.string()),
    ("snapshot_id", pa.string()),
    ("precipitation_sum", pa.float64()),
    ("precipitation_hours", pa.float64()),
    ("wind_speed_10m_max", pa.float64()),
    ("wind_speed_10m_mean", pa.float64()),
    ("wind_direction_10m_dominant", pa.float64()),
    ("temperature_2m_mean", pa.float64()),
    ("temperature_2m_max", pa.float64()),
    ("temperature_2m_min", pa.float64()),
    ("relative_humidity_2m_mean", pa.float64()),
    ("pressure_msl_mean", pa.float64())
])

MARINE_SCHEMA = pa.schema([
    ("site_id", pa.string()),
    ("date_local", pa.string()),
    ("model", pa.string()),
    ("snapshot_id", pa.string()),
    ("wave_height_max", pa.float64()),
    ("wave_period_max", pa.float64()),
    ("wave_direction_dominant", pa.float64())
])
