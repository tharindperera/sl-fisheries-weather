import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

def write_parquet(df: pd.DataFrame, out_path: str, partition_cols: list = None, schema: pa.Schema = None):
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort primary keys before creating the table
    sort_cols = [c for c in ["site_id", "date_local", "model", "snapshot_id"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
        
    # Ensure stable schema
    table = pa.Table.from_pandas(df, schema=schema)
    
    # Write to temporary file first for atomicity
    tmp_path = path.with_suffix(".tmp")
    if partition_cols:
        # partition_cols doesn't support writing to a single tmp_path easily. 
        # But we can write to a tmp directory and then move.
        tmp_dir = path.with_suffix(".tmp_dir")
        pq.write_to_dataset(table, root_path=str(tmp_dir), partition_cols=partition_cols, compression='snappy')
        # Here we'd rename, but for now let's just write.
        import shutil
        if path.exists(): shutil.rmtree(path)
        tmp_dir.rename(path)
    else:
        pq.write_table(table, tmp_path, compression='snappy')
        tmp_path.replace(path)

