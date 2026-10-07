def validate_response(data: dict, expected_locations: int, expected_days: int) -> list:
    if isinstance(data, dict) and "error" in data:
        raise ValueError(f"API Error: {data}")
    
    # Open-Meteo returns a list of dicts for multiple locations, or a single dict for one location.
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
            
        # Check that all arrays have the same length
        for key, arr in daily.items():
            if len(arr) != expected_days:
                raise ValueError(f"Length mismatch for {key}: {len(arr)} vs {expected_days}")
                
    return results
