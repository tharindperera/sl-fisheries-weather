import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

def write_parquet(df: pd.DataFrame, out_path: str, partition_cols: list = None):
    # Ensure stable schema
    table = pa.Table.from_pandas(df)
    
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort primary keys
    if "site_id" in df.columns and "date_local" in df.columns:
        df = df.sort_values(["site_id", "date_local"])
        
    if partition_cols:
        pq.write_to_dataset(table, root_path=out_path, partition_cols=partition_cols)
    else:
        pq.write_table(table, out_path)
