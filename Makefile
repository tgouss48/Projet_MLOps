PYTHON ?= python3
VENV   ?= .venv
BIN     = $(VENV)/bin
export PATH := $(abspath $(BIN)):$(PATH)

.PHONY: all setup mlflow data pipeline drift up down logs smoke simu-stable simu-capteur simu-ete demo-rejet demo-gate-refus api demo-api lint test clean

# tout depuis zero : environnement, serveur MLflow, donnees, pipeline, API
all: setup mlflow data pipeline up

setdrift:
	dvc repro drift
	cat reports/drift.md

up:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

mlflow:
	docker compose up -d --wait mlflow

data:
	dvc update data/raw/tetouan.zip.dvc

pipeline:
	dvc repro

demo-gate-refus:
	python src/demo_mauvais_modele.py
	-python src/quality_gate.py models_refus

up:
	docker compose up -d --build --wait

smoke:
	python scripts/smoke_test.py

simu-stable:
	python scripts/simulate_traffic.py stable --duree 150

simu-capteur:
	python scripts/simulate_traffic.py capteur --duree 150

simu-ete:
	python scripts/simulate_traffic.py ete --duree 140 --rps 40

down:
	docker compose down

logs:
	docker compose logs -f api

api:
	uvicorn app:app --app-dir src --port 8000

demo-api:
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_ete.json; echo
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_hiver.json; echo
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_invalide.json; echo

lint:
	ruff check src tests scripts

test:
	pytest -q

clean:
	rm -rf .pytest_cache

demo-rejet:
	-python src/validate.py tests/data/capteur_en_panne.csv
