-- Target pacing for the current month (month of the latest commercial day),
-- per site x channel. Roll up with SUM for brand, market or portfolio totals,
-- then recompute the ratios from the sums.
CREATE OR REPLACE TABLE `seo_platform.mart_target_pacing`
AS
WITH p AS (
  SELECT
    MAX(date)                     AS report_date,
    DATE_TRUNC(MAX(date), MONTH)  AS month_start,
    LAST_DAY(MAX(date))           AS month_end
  FROM `seo_platform.stg_commercial_daily`
),
cal AS (
  SELECT
    report_date, month_start, month_end,
    DATE_DIFF(report_date, month_start, DAY) + 1  AS days_elapsed,
    DATE_DIFF(month_end,   month_start, DAY) + 1  AS days_in_month
  FROM p
),
mtd AS (
  SELECT d.site_id, d.channel,
         SUM(d.new_customers)   AS new_customers_mtd,
         SUM(d.net_revenue_eur) AS net_revenue_mtd
  FROM `seo_platform.mart_site_daily` d
  CROSS JOIN cal
  WHERE d.date BETWEEN cal.month_start AND cal.report_date
  GROUP BY d.site_id, d.channel
),
base AS (
  SELECT
    s.site_id, s.brand, s.vertical, s.geo, s.market, t.channel,
    cal.report_date, cal.month_start, cal.days_elapsed, cal.days_in_month,
    cal.days_in_month - cal.days_elapsed           AS days_left,
    COALESCE(m.new_customers_mtd, 0)               AS new_customers_mtd,
    t.new_customers_target                         AS customers_target,
    COALESCE(m.net_revenue_mtd, 0)                 AS net_revenue_mtd,
    t.net_revenue_target_eur                       AS revenue_target_eur
  FROM `seo_platform.raw_targets_monthly` t
  CROSS JOIN cal
  JOIN `seo_platform.dim_site` s ON s.site_id = t.site_id
  LEFT JOIN mtd m ON m.site_id = t.site_id AND m.channel = t.channel
  WHERE DATE(t.month) = cal.month_start
)
SELECT
  base.*,
  -- new customers
  SAFE_DIVIDE(new_customers_mtd, customers_target)                                  AS customers_achieved_pct,
  GREATEST(customers_target - new_customers_mtd, 0)                                 AS customers_remaining,
  SAFE_DIVIDE(GREATEST(customers_target - new_customers_mtd, 0), customers_target)  AS customers_remaining_pct,
  SAFE_DIVIDE(new_customers_mtd, days_elapsed)                                      AS customers_run_rate_per_day,
  SAFE_DIVIDE(new_customers_mtd, days_elapsed) * days_in_month                      AS customers_run_rate_forecast,
  SAFE_DIVIDE(SAFE_DIVIDE(new_customers_mtd, days_elapsed) * days_in_month, customers_target) AS customers_forecast_vs_target,
  SAFE_DIVIDE(GREATEST(customers_target - new_customers_mtd, 0), days_left)         AS customers_needed_per_day,
  CASE
    WHEN customers_target IS NULL OR customers_target = 0 THEN 'No target'
    WHEN SAFE_DIVIDE(new_customers_mtd, days_elapsed) * days_in_month >= customers_target       THEN 'On track'
    WHEN SAFE_DIVIDE(new_customers_mtd, days_elapsed) * days_in_month >= 0.9 * customers_target THEN 'At risk'
    ELSE 'Behind'
  END                                                                               AS customers_status,
  -- net revenue
  SAFE_DIVIDE(net_revenue_mtd, revenue_target_eur)                                  AS revenue_achieved_pct,
  GREATEST(revenue_target_eur - net_revenue_mtd, 0)                                 AS revenue_remaining_eur,
  SAFE_DIVIDE(net_revenue_mtd, days_elapsed) * days_in_month                        AS revenue_run_rate_forecast_eur
FROM base;
