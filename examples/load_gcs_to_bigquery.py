"""
Cloud Storage -> BigQuery: load yesterday's Snowflake export into the raw layer.

Example of an idempotent daily load: each run REPLACES one date partition
(table$YYYYMMDD), so reruns and backfills never create duplicates.

Illustrative example written for this repository; not executed here.
    python pipeline/load_gcs_to_bigquery.py --date 2026-09-29
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from google.cloud import bigquery

PROJECT = "my-gcp-project"
DATASET = "seo_platform"
BUCKET = "seo-platform-landing"

SOURCES = {
    # gcs folder   -> raw table
    "commercial": "raw_snowflake_commercial_daily",
}


def load_partition(client: bigquery.Client, folder: str, table: str, d: date) -> int:
    uri = f"gs://{BUCKET}/snowflake/{folder}/dt={d:%Y-%m-%d}/*.parquet"
    target = f"{PROJECT}.{DATASET}.{table}${d:%Y%m%d}"          # partition decorator
    job = client.load_table_from_uri(
        uri,
        target,
        job_config=bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    )
    job.result()
    return job.output_rows or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today() - timedelta(days=1)))
    d = date.fromisoformat(ap.parse_args().date)

    client = bigquery.Client(project=PROJECT)
    for folder, table in SOURCES.items():
        rows = load_partition(client, folder, table, d)
        if rows == 0:
            raise RuntimeError(f"{table}: 0 rows for {d} - source export missing?")
        print(f"{table:35s} {d}  {rows:,} rows")


if __name__ == "__main__":
    main()
