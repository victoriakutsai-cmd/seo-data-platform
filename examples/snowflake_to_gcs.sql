-- =============================================================================
-- Example: export a daily slice of a Snowflake table to Cloud Storage as Parquet.
-- Generic pattern based on the Snowflake docs (COPY INTO <location>).
-- Illustrative only: object names are placeholders and it is not executed here.
-- =============================================================================

-- One-time setup: storage integration + external stage on the GCS bucket
CREATE STORAGE INTEGRATION IF NOT EXISTS gcs_export
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'GCS'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('gcs://my-landing-bucket/snowflake/');

CREATE STAGE IF NOT EXISTS export_stage
  URL = 'gcs://my-landing-bucket/snowflake/'
  STORAGE_INTEGRATION = gcs_export
  FILE_FORMAT = (TYPE = PARQUET);

-- Daily slice into a date-partitioned folder (dt=YYYY-MM-DD), so the BigQuery
-- load can replace exactly one partition and reruns stay idempotent.
SET d = TO_CHAR(DATEADD(day, -1, CURRENT_DATE()), 'YYYY-MM-DD');

COPY INTO @export_stage/commercial/
  FROM (
    SELECT site_id, date, channel, clicks, signups, new_customers, active_customers,
           transactions, payments_eur, refunds_eur, gross_revenue_eur,
           promo_cost_eur, net_revenue_eur
    FROM analytics.commercial_daily
    WHERE date = $d
  )
  PARTITION BY ('dt=' || TO_CHAR(date, 'YYYY-MM-DD'))
  HEADER = TRUE;
