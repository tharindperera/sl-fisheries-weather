import math
from datetime import datetime, timedelta

def validate_response(data: dict, expected_locations: int, expected_days: int, expected_start: str, expected_vars: list, expected_units: dict = None) -> list:
    if isinstance(data, dict) and "error" in data:
        raise ValueError(f"API Error: {data}")
    
    results = data if isinstance(data, list) else [data]
    if len(results) != expected_locations:
        raise ValueError(f"Expected {expected_locations} locations, got {len(results)}")
    
    for res in results:
        if "daily" not in res:
            raise ValueError("Response missing 'daily' object")
            
        daily = res["daily"]
        if "time" not in daily:
            raise ValueError("Response missing 'time' array in 'daily'")
            
        time_arr = daily["time"]
        if len(time_arr) != expected_days:
            raise ValueError(f"Expected {expected_days} days of data, got {len(time_arr)}")
            
        # Check continuity and exact start date
        expected_dates = [(datetime.strptime(expected_start, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(expected_days)]
        if time_arr != expected_dates:
            raise ValueError(f"Date sequence mismatch. Expected start {expected_start} for {expected_days} days.")
        
        for var in expected_vars:
            if var not in daily:
                raise ValueError(f"Missing variable {var}")
            arr = daily[var]
            if len(arr) != expected_days:
                raise ValueError(f"Length mismatch for {var}: {len(arr)} vs {expected_days}")
            
            # Check for invalid internal nulls. Trailing unreleased tails might be null, but interior ones are bad.
            # We will allow trailing nulls, but reject interior nulls.
            # Find the last non-null index
            last_non_null = -1
            for i, val in enumerate(arr):
                if val is not None and not math.isnan(val):
                    last_non_null = i
            
            for i in range(last_non_null + 1):
                val = arr[i]
                if val is None or math.isnan(val):
                    raise ValueError(f"Internal null detected in {var} at index {i}")
                
                # Physical bound checks
                if "temperature" in var and (val < -50 or val > 60):
                    raise ValueError(f"Temperature {val} out of bounds")
                if "relative_humidity" in var and (val < 0 or val > 100):
                    raise ValueError(f"Humidity {val} out of bounds")
                if "precipitation" in var and val < 0:
                    raise ValueError(f"Precipitation {val} cannot be negative")
                if "wind_speed" in var and val < 0:
                    raise ValueError(f"Wind speed {val} cannot be negative")
                if "wind_direction" in var and (val < 0 or val > 360):
                    raise ValueError(f"Wind direction {val} out of bounds")
                if "wave_height" in var and val < 0:
                    raise ValueError(f"Wave height {val} cannot be negative")
                if "wave_period" in var and val < 0:
                    raise ValueError(f"Wave period {val} cannot be negative")
                    
        # Check units
        if expected_units and "daily_units" in res:
            units = res["daily_units"]
            for var, expected_unit in expected_units.items():
                if var in units and units[var].lower() != expected_unit.lower():
                    raise ValueError(f"Unit mismatch for {var}: expected {expected_unit}, got {units[var]}")

    return results
