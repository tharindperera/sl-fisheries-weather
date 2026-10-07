import csv
import os
from dataclasses import dataclass
from typing import List

@dataclass
class Site:
    site_id: str
    name: str
    site_kind: str
    admin_district: str
    fisheries_district: str
    coastal_sector: str
    lat_land: float
    lon_land: float
    lat_sea: float
    lon_sea: float
    coordinate_source_url: str
    checked_date: str
    verification_status: str
    registry_version: str

def load_registry() -> List[Site]:
    registry_path = os.path.join(os.path.dirname(__file__), "registry.csv")
    sites = []
    with open(registry_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sites.append(Site(
                site_id=row["site_id"],
                name=row["name"],
                site_kind=row["site_kind"],
                admin_district=row["admin_district"],
                fisheries_district=row["fisheries_district"],
                coastal_sector=row["coastal_sector"],
                lat_land=float(row["lat_land"]),
                lon_land=float(row["lon_land"]),
                lat_sea=float(row["lat_sea"]),
                lon_sea=float(row["lon_sea"]),
                coordinate_source_url=row["coordinate_source_url"],
                checked_date=row["checked_date"],
                verification_status=row["verification_status"],
                registry_version=row["registry_version"]
            ))
    return sites
