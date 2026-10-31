# Schema des donnees : noms de colonnes et plages de valeurs acceptees
import pandas as pd
import pandera as pa
from pandera import Check, Column

# noms d'origine du CSV -> noms utilises dans le projet
RENAME = {
    "DateTime": "datetime",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Wind Speed": "wind_speed",
    "general diffuse flows": "general_diffuse_flows",
    "diffuse flows": "diffuse_flows",
    "Zone 1 Power Consumption": "zone1_kw",
    "Zone 2  Power Consumption": "zone2_kw",
    "Zone 3  Power Consumption": "zone3_kw",
}

WEATHER_COLS = ["temperature", "humidity", "wind_speed", "general_diffuse_flows", "diffuse_flows"]
ZONE_COLS = ["zone1_kw", "zone2_kw", "zone3_kw"]


def pas_regulier(df):
    # une mesure toutes les 10 minutes, sans trou ni doublon
    return bool((df["datetime"].diff().dropna() == pd.Timedelta(minutes=10)).all())


raw_schema = pa.DataFrameSchema(
    {
        "datetime": Column("datetime64[ns]", unique=True),
        "temperature": Column(float, Check.in_range(-5, 50)),
        "humidity": Column(float, Check.in_range(0, 100)),
        "wind_speed": Column(float, Check.in_range(0, 20)),
        "general_diffuse_flows": Column(float, Check.in_range(0, 1500)),
        "diffuse_flows": Column(float, Check.in_range(0, 1500)),
        "zone1_kw": Column(float, Check.in_range(0, 100000, include_min=False)),
        "zone2_kw": Column(float, Check.in_range(0, 100000, include_min=False)),
        "zone3_kw": Column(float, Check.in_range(0, 100000, include_min=False)),
    },
    checks=[Check(pas_regulier, error="pas de temps different de 10 min")],
    strict=True,
    coerce=False,
)
