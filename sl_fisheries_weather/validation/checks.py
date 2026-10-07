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
        # Do not assert len(time_arr) == expected_days here, because we allow shorter prefixes.
        
        # Check continuity and exact start date
        # It's possible the API returns less than expected_days.
        if len(time_arr) == 0:
            raise ValueError("Empty time array")
        
        if time_arr[0] != expected_start:
            raise ValueError(f"Date sequence mismatch. Expected start {expected_start}, got {time_arr[0]}")
        
        # First pass: find the minimum last_non_null across all variables
        valid_prefix_len = len(time_arr)
        
        for var in expected_vars:
            if var not in daily:
                raise ValueError(f"Missing variable {var}")
            arr = daily[var]
            
            last_non_null = -1
            for i, val in enumerate(arr):
                if val is not None and not math.isnan(val):
                    last_non_null = i
                    
            if last_non_null + 1 < valid_prefix_len:
                valid_prefix_len = last_non_null + 1
                
        # Now validate everything up to valid_prefix_len
        for var in expected_vars:
            arr = daily[var]
            for i in range(valid_prefix_len):
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
        
        # Truncate arrays to valid_prefix_len
        daily["time"] = time_arr[:valid_prefix_len]
        for k in list(daily.keys()):
            if k != "time":
                daily[k] = daily[k][:valid_prefix_len]
        # Check units
        if expected_units and "daily_units" in res:
            units = res["daily_units"]
            for var, expected_unit in expected_units.items():
                if var in units and units[var].lower() != expected_unit.lower():
                    raise ValueError(f"Unit mismatch for {var}: expected {expected_unit}, got {units[var]}")

    return results
