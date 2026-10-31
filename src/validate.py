# Lecture des donnees brutes et validation avec le schema
# Lancer avec : python src/validate.py
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pandera as pa
import yaml

from schema import RENAME, raw_schema


def load_raw(path):
    df = pd.read_csv(path)
    df = df.rename(columns=RENAME)
    df["datetime"] = pd.to_datetime(df["datetime"], format="%m/%d/%Y %H:%M")
    return df


def validate(df):
    # renvoie (ok, liste des erreurs)
    try:
        raw_schema.validate(df, lazy=True)
        return True, []
    except pa.errors.SchemaErrors as e:
        cases = e.failure_cases[["column", "check", "failure_case"]].fillna("table").astype(str)
        return False, cases.drop_duplicates(["column", "check"]).to_dict("records")


def main():
    params = yaml.safe_load(open("params.yaml"))["data"]
    # sans argument : donnees du pipeline, sinon un autre fichier (ex : demo d'un rejet)
    if len(sys.argv) < 2:
        raw, report_path = params["raw_zip"], "reports/data_validation.json"
    else:
        raw, report_path = sys.argv[1], "reports/data_validation_rejet.json"

    df = load_raw(raw)
    ok, errors = validate(df)

    report = {
        "source": raw,
        "md5": hashlib.md5(Path(raw).read_bytes()).hexdigest(),
        "n_rows": len(df),
        "start": str(df["datetime"].min()),
        "end": str(df["datetime"].max()),
        "valid": ok,
        "errors": errors,
    }
    Path("reports").mkdir(exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2))

    if not ok:
        print("donnees invalides, voir", report_path)
        for err in errors:
            print(" -", err["column"], ":", err["check"], "(ex:", err["failure_case"], ")")
        sys.exit(1)

    Path(params["clean_csv"]).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(params["clean_csv"], index=False)
    print("donnees valides :", len(df), "lignes")


if __name__ == "__main__":
    main()
