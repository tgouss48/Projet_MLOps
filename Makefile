PYTHON ?= python3
VENV   ?= .venv
BIN     = $(VENV)/bin
export PATH := $(abspath $(BIN)):$(PATH)

.PHONY: setup data pipeline demo-rejet demo-gate-refus mlflow-ui api demo-api test clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

data:
	dvc update data/raw/tetouan.zip.dvc

pipeline:
	dvc repro

demo-gate-refus:
	python src/demo_mauvais_modele.py
	-python src/quality_gate.py models_refus

mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

api:
	uvicorn app:app --app-dir src --port 8000

demo-api:
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_ete.json; echo
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_hiver.json; echo
	curl -s -X POST localhost:8000/predict -H 'content-type: application/json' -d @examples/mesure_invalide.json; echo

test:
	pytest -q

clean:
	rm -rf .pytest_cache

demo-rejet:
	-python src/validate.py tests/data/capteur_en_panne.csv
