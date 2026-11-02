PYTHON ?= python3
VENV   ?= .venv
BIN     = $(VENV)/bin
export PATH := $(abspath $(BIN)):$(PATH)

.PHONY: setup data pipeline demo-rejet mlflow-ui test clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

data:
	dvc update data/raw/tetouan.zip.dvc

pipeline:
	dvc repro

mlflow-ui:
	mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

test:
	pytest -q

clean:
	rm -rf .pytest_cache

demo-rejet:
	-python src/validate.py tests/data/capteur_en_panne.csv
