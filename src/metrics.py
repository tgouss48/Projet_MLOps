# Metriques Prometheus exposees par l'API sur /metrics
from prometheus_client import Counter, Gauge, Histogram

# --- service ---
REQUETES = Counter("api_requests_total", "Nombre de requetes", ["route", "status"])
LATENCE = Histogram(
    "api_request_duration_seconds", "Duree des requetes", ["route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1, 2, 5),
)
ENTREES_INVALIDES = Counter("api_invalid_inputs_total", "Champs refuses par le contrat (422)", ["champ"])

# --- modele ---
MODELE_CHARGE = Gauge("model_loaded", "1 si un modele est charge")
MODELE_INFO = Gauge("model_info", "Version du modele servi", ["version", "algo"])
PREDICTIONS = Counter("predictions_total", "Nombre de predictions", ["alert"])
PROBA = Histogram(
    "peak_probability", "Probabilite de pic predite",
    buckets=(0.01, 0.06, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0),
)

# --- entrees recues (pour suivre si les donnees changent) ---
TEMPERATURE = Histogram("input_temperature_celsius", "Temperature recue", buckets=(5, 10, 15, 20, 25, 30, 35, 40))
CONSO = Histogram(
    "input_total_kw", "Consommation totale recue",
    buckets=(40000, 50000, 60000, 70000, 80000, 92000, 100000, 110000, 120000, 140000),
)
