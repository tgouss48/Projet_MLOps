PYTHON ?= python3
VENV   ?= .venv
BIN     = $(VENV)/bin

.PHONY: setup test clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

test:
	$(BIN)/pytest -q

clean:
	rm -rf .pytest_cache
