#!/usr/bin/env bash
# Load the synthetic demo into BigQuery and build staging + marts.
# Works on the free BigQuery sandbox (no billing account needed).
#
#   bash scripts/load_demo_to_bigquery.sh <gcp-project-id> [location]
#
# Sandbox note: tables expire after 60 days and partitions older than 60 days are
# dropped, so in sandbox mode PARTITION BY clauses are removed automatically.
# Set SANDBOX=0 on a billed project to keep partitioning as defined in the DDL.
set -euo pipefail

PROJECT="${1:?usage: load_demo_to_bigquery.sh <project-id> [location]}"
LOCATION="${2:-EU}"
SANDBOX="${SANDBOX:-1}"
DATASET="seo_platform"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

run_sql () {
  local file="$1"
  if [[ "$SANDBOX" == "1" ]]; then
    sed -E '/^PARTITION BY/d' "$file"
  else
    cat "$file"
  fi | bq query --project_id="$PROJECT" --location="$LOCATION" --use_legacy_sql=false --quiet >/dev/null
  echo "  ok  ${file#$ROOT/}"
}

echo "1/4 dataset"
bq --location="$LOCATION" mk --dataset "$PROJECT:$DATASET" 2>/dev/null || echo "  dataset exists"

echo "2/4 raw tables"
run_sql "$ROOT/sql/00_raw/create_raw_tables.sql"

echo "3/4 loading CSVs"
for f in "$ROOT"/data/*.csv; do
  t="$(basename "$f" .csv)"
  bq load --project_id="$PROJECT" --location="$LOCATION" \
     --source_format=CSV --skip_leading_rows=1 --replace \
     "$DATASET.$t" "$f" >/dev/null
  echo "  ok  $t"
done

echo "4/4 staging + marts"
for f in "$ROOT"/sql/01_staging/*.sql "$ROOT"/sql/02_marts/*.sql; do
  run_sql "$f"
done

echo "Done. Open Looker Studio -> Add data -> BigQuery -> $PROJECT.$DATASET.mart_*"
