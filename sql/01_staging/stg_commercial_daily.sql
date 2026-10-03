-- Commercial fact from Snowflake: cleaned and typed, one contract for every mart.
CREATE OR REPLACE VIEW `seo_platform.stg_commercial_daily` AS
SELECT
  site_id,
  DATE(date)           AS date,
  LOWER(TRIM(channel)) AS channel,
  clicks, signups, new_customers, active_customers,
  transactions, payments_eur, refunds_eur,
  gross_revenue_eur, promo_cost_eur, net_revenue_eur
FROM `seo_platform.raw_snowflake_commercial_daily`
WHERE site_id IS NOT NULL;
