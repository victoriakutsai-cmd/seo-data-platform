"""
Run the whole BigQuery SQL model locally on SQLite - no GCP account needed.

The SQL in /sql is written in BigQuery Standard SQL. This runner loads the CSVs from /data into SQLite, translates the
handful of BigQuery-specific functions used in the model (DATE_TRUNC, DATE_SUB,
DATE_ADD, DATE_DIFF, LAST_DAY, FORMAT_DATE, SAFE_DIVIDE, GREATEST) and executes
staging + marts in order. Used for testing and for the demo database.

Usage:
    python scripts/run_local.py               # builds ./seo_platform.db
"""
from __future__ import annotations

import calendar
import glob
import os
import re
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB = os.path.join(ROOT, "seo_platform.db")


# --------------------------------------------------------------------------- #
# BigQuery date functions as SQLite UDFs (dates are ISO strings in SQLite)
# --------------------------------------------------------------------------- #
def _d(x) -> date | None:
    return None if x is None else datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))   # clamp like BigQuery


def udf_date_trunc(x, unit):
    d = _d(x)
    if d is None:
        return None
    if unit == "MONTH":
        return str(d.replace(day=1))
    if unit in ("ISOWEEK", "WEEK(MONDAY)"):
        return str(d - timedelta(days=d.weekday()))
    if unit == "YEAR":
        return str(d.replace(month=1, day=1))
    raise ValueError(unit)


def udf_date_add(x, n, unit):
    d = _d(x)
    if d is None:
        return None
    n = int(n)
    if unit == "DAY":
        return str(d + timedelta(days=n))
    if unit == "MONTH":
        return str(add_months(d, n))
    if unit == "YEAR":
        return str(add_months(d, 12 * n))
    raise ValueError(unit)


def udf_date_diff(a, b, unit):
    if a is None or b is None:
        return None
    assert unit == "DAY"
    return (_d(a) - _d(b)).days


def udf_last_day(x):
    d = _d(x)
    return None if d is None else str(d.replace(day=calendar.monthrange(d.year, d.month)[1]))


def udf_format_date(fmt, x):
    d = _d(x)
    return None if d is None else d.strftime(fmt).lstrip("0")


def udf_safe_divide(a, b):
    if a is None or b is None or b == 0:
        return None
    return float(a) / float(b)


# --------------------------------------------------------------------------- #
# Minimal BigQuery -> SQLite translation
# --------------------------------------------------------------------------- #
def _split_args(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _rewrite_calls(sql: str, name: str, fn) -> str:
    pat = re.compile(rf"\b{name}\s*\(", re.I)
    while True:
        m = pat.search(sql)
        if not m:
            return sql
        i, depth = m.end(), 1
        while depth:
            depth += {"(": 1, ")": -1}.get(sql[i], 0)
            i += 1
        inner = sql[m.end(): i - 1]
        sql = sql[: m.start()] + fn(_split_args(inner)) + sql[i:]


def _interval(arg: str):
    m = re.match(r"INTERVAL\s+(-?\d+)\s+(\w+)", arg, re.I)
    return int(m.group(1)), m.group(2).upper()


def translate(sql: str) -> str:
    sql = re.sub(r"`seo_platform\.(\w+)`", r"\1", sql)
    sql = re.sub(r"CREATE OR REPLACE VIEW (\w+) AS",
                 r"DROP VIEW IF EXISTS \1; CREATE VIEW \1 AS", sql)
    sql = re.sub(r"CREATE OR REPLACE TABLE (\w+)\s*\n(?:(?:PARTITION|CLUSTER) BY[^\n]*\n)*AS",
                 r"DROP TABLE IF EXISTS \1; CREATE TABLE \1 AS", sql)
    sql = _rewrite_calls(sql, "DATE_TRUNC", lambda a: f"BQ_DATE_TRUNC({a[0]}, '{a[1].upper()}')")
    sql = _rewrite_calls(sql, "DATE_SUB",
                         lambda a: "BQ_DATE_ADD({}, {}, '{}')".format(a[0], -_interval(a[1])[0], _interval(a[1])[1]))
    sql = _rewrite_calls(sql, "DATE_ADD",
                         lambda a: "BQ_DATE_ADD({}, {}, '{}')".format(a[0], *_interval(a[1])))
    sql = _rewrite_calls(sql, "DATE_DIFF", lambda a: f"BQ_DATE_DIFF({a[0]}, {a[1]}, '{a[2].upper()}')")
    sql = re.sub(r"\bGREATEST\s*\(", "MAX(", sql)
    sql = re.sub(r"\bLEAST\s*\(", "MIN(", sql)
    return sql


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.create_function("BQ_DATE_TRUNC", 2, udf_date_trunc, deterministic=True)
    con.create_function("BQ_DATE_ADD", 3, udf_date_add, deterministic=True)
    con.create_function("BQ_DATE_DIFF", 3, udf_date_diff, deterministic=True)
    con.create_function("LAST_DAY", 1, udf_last_day, deterministic=True)
    con.create_function("FORMAT_DATE", 2, udf_format_date, deterministic=True)
    con.create_function("SAFE_DIVIDE", 2, udf_safe_divide, deterministic=True)
    # CONCAT is built into SQLite only from 3.44; register it so older builds work too
    con.create_function("CONCAT", -1, lambda *a: None if None in a else "".join(str(x) for x in a), deterministic=True)
    return con


def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = connect()

    print("Loading raw CSVs ...")
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "*.csv"))):
        name = os.path.splitext(os.path.basename(path))[0]
        pd.read_csv(path).to_sql(name, con, index=False)
        print(f"  {name}")

    for layer in ("01_staging", "02_marts"):
        for path in sorted(glob.glob(os.path.join(ROOT, "sql", layer, "*.sql"))):
            print(f"Running {layer}/{os.path.basename(path)}")
            con.executescript(translate(open(path, encoding="utf-8").read()))

    print("\nRow counts:")
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mart_%' ORDER BY name"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:35s} {n:>9,d}")
    con.close()
    print(f"\nDone -> {os.path.relpath(DB)}")


if __name__ == "__main__":
    main()
