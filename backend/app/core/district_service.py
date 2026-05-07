"""
FloodSense AI — District Data Service
Historical vulnerability scores, elevation, terrain type, and 2022 flood impact data.
"""

from dataclasses import dataclass

@dataclass
class DistrictInfo:
    name: str
    name_ur: str
    province: str
    avg_elevation_m: float
    terrain_type: str
    terrain_type_ur: str
    vulnerability_score: float   # 0–1, higher = more vulnerable
    population_thousands: int
    lat: float
    lon: float
    rivers: list[str]
    flood_history_events: int    # documented events since 2000
    casualties_2022: int         # 2022 super-floods
    displaced_2022: int          # thousands displaced
    ndma_risk_zone: str          # A/B/C


DISTRICTS: dict[str, DistrictInfo] = {
    "buner": DistrictInfo(
        name="Buner", name_ur="بونیر",
        province="KPK",
        avg_elevation_m=1082,
        terrain_type="Hilly", terrain_type_ur="پہاڑی",
        vulnerability_score=0.78,
        population_thousands=900,
        lat=34.55, lon=72.50,
        rivers=["Barandu River", "Khindi Khwar"],
        flood_history_events=14,
        casualties_2022=38, displaced_2022=45,
        ndma_risk_zone="A",
    ),
    "swat": DistrictInfo(
        name="Swat", name_ur="سوات",
        province="KPK",
        avg_elevation_m=980,
        terrain_type="Valley", terrain_type_ur="وادی",
        vulnerability_score=0.85,
        population_thousands=2300,
        lat=35.22, lon=72.42,
        rivers=["Swat River", "Ushu River"],
        flood_history_events=22,
        casualties_2022=95, displaced_2022=210,
        ndma_risk_zone="A",
    ),
    "nowshera": DistrictInfo(
        name="Nowshera", name_ur="نوشہرہ",
        province="KPK",
        avg_elevation_m=285,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.92,
        population_thousands=1600,
        lat=34.01, lon=71.97,
        rivers=["Kabul River", "Swat River"],
        flood_history_events=19,
        casualties_2022=47, displaced_2022=120,
        ndma_risk_zone="A",
    ),
    "charsadda": DistrictInfo(
        name="Charsadda", name_ur="چارسدہ",
        province="KPK",
        avg_elevation_m=276,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.88,
        population_thousands=1500,
        lat=34.15, lon=71.73,
        rivers=["Swat River", "Jindi River"],
        flood_history_events=17,
        casualties_2022=31, displaced_2022=95,
        ndma_risk_zone="A",
    ),
    "peshawar": DistrictInfo(
        name="Peshawar", name_ur="پشاور",
        province="KPK",
        avg_elevation_m=327,
        terrain_type="Urban Plains", terrain_type_ur="شہری میدانی",
        vulnerability_score=0.65,
        population_thousands=4300,
        lat=34.01, lon=71.57,
        rivers=["Kabul River", "Bara River"],
        flood_history_events=10,
        casualties_2022=12, displaced_2022=30,
        ndma_risk_zone="B",
    ),
    "mardan": DistrictInfo(
        name="Mardan", name_ur="مردان",
        province="KPK",
        avg_elevation_m=283,
        terrain_type="Semi-Plains", terrain_type_ur="نیم میدانی",
        vulnerability_score=0.72,
        population_thousands=2400,
        lat=34.20, lon=72.05,
        rivers=["Kalpani River"],
        flood_history_events=11,
        casualties_2022=18, displaced_2022=55,
        ndma_risk_zone="B",
    ),
    "dera ismail khan": DistrictInfo(
        name="Dera Ismail Khan", name_ur="ڈیرہ اسماعیل خان",
        province="KPK",
        avg_elevation_m=172,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.89,
        population_thousands=1800,
        lat=31.83, lon=70.90,
        rivers=["Indus River", "Gomal River"],
        flood_history_events=21,
        casualties_2022=58, displaced_2022=140,
        ndma_risk_zone="A",
    ),
    "dera ghazi khan": DistrictInfo(
        name="Dera Ghazi Khan", name_ur="ڈیرہ غازی خان",
        province="Punjab",
        avg_elevation_m=145,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.91,
        population_thousands=3200,
        lat=30.05, lon=70.63,
        rivers=["Indus River", "Chenab River"],
        flood_history_events=25,
        casualties_2022=112, displaced_2022=320,
        ndma_risk_zone="A",
    ),
    "rajanpur": DistrictInfo(
        name="Rajanpur", name_ur="راجن پور",
        province="Punjab",
        avg_elevation_m=132,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.93,
        population_thousands=2200,
        lat=29.10, lon=70.33,
        rivers=["Indus River"],
        flood_history_events=28,
        casualties_2022=87, displaced_2022=280,
        ndma_risk_zone="A",
    ),
    "muzaffargarh": DistrictInfo(
        name="Muzaffargarh", name_ur="مظفرگڑھ",
        province="Punjab",
        avg_elevation_m=128,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.90,
        population_thousands=4200,
        lat=30.07, lon=71.19,
        rivers=["Chenab River", "Indus River"],
        flood_history_events=23,
        casualties_2022=74, displaced_2022=250,
        ndma_risk_zone="A",
    ),
    "jacobabad": DistrictInfo(
        name="Jacobabad", name_ur="جیکب آباد",
        province="Sindh",
        avg_elevation_m=55,
        terrain_type="Low Plains", terrain_type_ur="نچلے میدانی",
        vulnerability_score=0.95,
        population_thousands=1200,
        lat=28.28, lon=68.43,
        rivers=["Indus River"],
        flood_history_events=30,
        casualties_2022=145, displaced_2022=380,
        ndma_risk_zone="A",
    ),
    "larkana": DistrictInfo(
        name="Larkana", name_ur="لاڑکانہ",
        province="Sindh",
        avg_elevation_m=48,
        terrain_type="Low Plains", terrain_type_ur="نچلے میدانی",
        vulnerability_score=0.87,
        population_thousands=2000,
        lat=27.55, lon=68.22,
        rivers=["Indus River"],
        flood_history_events=18,
        casualties_2022=63, displaced_2022=195,
        ndma_risk_zone="A",
    ),
    "sukkur": DistrictInfo(
        name="Sukkur", name_ur="سکھر",
        province="Sindh",
        avg_elevation_m=66,
        terrain_type="Plains", terrain_type_ur="میدانی",
        vulnerability_score=0.82,
        population_thousands=1600,
        lat=27.70, lon=68.86,
        rivers=["Indus River"],
        flood_history_events=16,
        casualties_2022=44, displaced_2022=120,
        ndma_risk_zone="A",
    ),
    "abbottabad": DistrictInfo(
        name="Abbottabad", name_ur="ایبٹ آباد",
        province="KPK",
        avg_elevation_m=1260,
        terrain_type="Hilly", terrain_type_ur="پہاڑی",
        vulnerability_score=0.55,
        population_thousands=1300,
        lat=34.15, lon=73.22,
        rivers=["Dor River"],
        flood_history_events=8,
        casualties_2022=9, displaced_2022=18,
        ndma_risk_zone="B",
    ),
    "mansehra": DistrictInfo(
        name="Mansehra", name_ur="مانسہرہ",
        province="KPK",
        avg_elevation_m=1070,
        terrain_type="Hilly", terrain_type_ur="پہاڑی",
        vulnerability_score=0.68,
        population_thousands=1500,
        lat=34.33, lon=73.20,
        rivers=["Kunhar River", "Siran River"],
        flood_history_events=13,
        casualties_2022=22, displaced_2022=60,
        ndma_risk_zone="B",
    ),
}


def get_district(name: str) -> DistrictInfo | None:
    return DISTRICTS.get(name.strip().lower())


def get_all_districts() -> list[dict]:
    result = []
    for key, d in DISTRICTS.items():
        result.append({
            "id": key,
            "name": d.name,
            "name_ur": d.name_ur,
            "province": d.province,
            "avg_elevation_m": d.avg_elevation_m,
            "terrain_type": d.terrain_type,
            "terrain_type_ur": d.terrain_type_ur,
            "vulnerability_score": d.vulnerability_score,
            "population_thousands": d.population_thousands,
            "lat": d.lat,
            "lon": d.lon,
            "rivers": d.rivers,
            "flood_history_events": d.flood_history_events,
            "casualties_2022": d.casualties_2022,
            "displaced_2022": d.displaced_2022,
            "ndma_risk_zone": d.ndma_risk_zone,
        })
    return sorted(result, key=lambda x: x["vulnerability_score"], reverse=True)


def get_elevation_lookup() -> dict[str, float]:
    return {k: v.avg_elevation_m for k, v in DISTRICTS.items()}