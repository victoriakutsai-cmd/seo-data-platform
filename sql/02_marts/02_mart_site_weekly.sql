-- Weekly (ISO weeks, Monday start) per site x channel, with week-over-week change.
-- days_in_week < 7 flags the current, still incomplete week.
CREATE OR REPLACE TABLE `seo_platform.mart_site_weekly`
CLUSTER BY site_id, channel
AS
WITH w AS (
  SELECT
    site_id, brand, vertical, geo, channel,
    DATE_TRUNC(date, ISOWEEK)  AS week_start,
    COUNT(DISTINCT date)       AS days_in_week,
    SUM(clicks)                AS clicks,
    SUM(signups)               AS signups,
    SUM(new_customers)         AS new_customers,
    SUM(net_revenue_eur)       AS net_revenue_eur,
    SUM(gsc_clicks)            AS gsc_clicks,
    SUM(gsc_impressions)       AS gsc_impressions
  FROM `seo_platform.mart_site_daily`
  GROUP BY site_id, brand, vertical, geo, channel, DATE_TRUNC(date, ISOWEEK)
)
SELECT
  cur.*,
  DATE_ADD(cur.week_start, INTERVAL 6 DAY)                 AS week_end,
  SAFE_DIVIDE(cur.signups, cur.clicks)                     AS click_to_signup,
  SAFE_DIVIDE(cur.new_customers, cur.signups)              AS signup_to_customer,
  SAFE_DIVIDE(cur.new_customers, cur.clicks)               AS click_to_customer,
  CASE WHEN cur.days_in_week = 7 THEN 1 ELSE 0 END         AS is_complete_week,
  prev.new_customers                                       AS new_customers_prev_week,
  -- WoW only for complete weeks: a 2-day week vs a 7-day week is not a trend
  CASE WHEN cur.days_in_week = 7
       THEN SAFE_DIVIDE(cur.new_customers - prev.new_customers, prev.new_customers) END       AS new_customers_wow,
  CASE WHEN cur.days_in_week = 7
       THEN SAFE_DIVIDE(cur.net_revenue_eur - prev.net_revenue_eur, prev.net_revenue_eur) END AS net_revenue_wow
FROM w cur
LEFT JOIN w prev
  ON prev.site_id = cur.site_id
 AND prev.channel = cur.channel
 AND prev.week_start = DATE_SUB(cur.week_start, INTERVAL 7 DAY);
