-- Monthly per site, wide format - the automated version of the "MONTHLY" tab:
-- new customers by channel, organic target & achievement, net revenue, GSC,
-- month-over-month (MoM) and same-month-last-year (YoY) change.
CREATE OR REPLACE TABLE `seo_platform.mart_site_monthly`
CLUSTER BY site_id
AS
WITH m AS (
  SELECT
    site_id, brand, vertical, geo, market,
    DATE_TRUNC(date, MONTH) AS month,
    COUNT(DISTINCT date)    AS days_with_data,
    SUM(CASE WHEN channel = 'organic'   THEN clicks          ELSE 0 END) AS organic_clicks,
    SUM(CASE WHEN channel = 'organic'   THEN signups         ELSE 0 END) AS organic_signups,
    SUM(CASE WHEN channel = 'organic'   THEN new_customers   ELSE 0 END) AS organic_new_customers,
    SUM(CASE WHEN channel = 'direct'    THEN new_customers   ELSE 0 END) AS direct_new_customers,
    SUM(CASE WHEN channel = 'paid'      THEN new_customers   ELSE 0 END) AS paid_new_customers,
    SUM(CASE WHEN channel = 'referral'  THEN new_customers   ELSE 0 END) AS referral_new_customers,
    SUM(CASE WHEN channel = 'social'    THEN new_customers   ELSE 0 END) AS social_new_customers,
    SUM(new_customers)                                                   AS total_new_customers,
    SUM(CASE WHEN channel = 'organic'   THEN net_revenue_eur ELSE 0 END) AS organic_net_revenue_eur,
    SUM(net_revenue_eur)                                                 AS total_net_revenue_eur,
    SUM(gsc_clicks)                                                      AS gsc_clicks,
    SUM(gsc_impressions)                                                 AS gsc_impressions,
    SUM(gsc_brand_clicks)                                                AS gsc_brand_clicks,
    SUM(gsc_brand_impressions)                                           AS gsc_brand_impressions,
    SUM(gsc_nonbrand_clicks)                                             AS gsc_nonbrand_clicks,
    SUM(gsc_nonbrand_impressions)                                        AS gsc_nonbrand_impressions
  FROM `seo_platform.mart_site_daily`
  GROUP BY site_id, brand, vertical, geo, market, DATE_TRUNC(date, MONTH)
)
SELECT
  cur.*,
  SAFE_DIVIDE(cur.organic_signups, cur.organic_clicks)                 AS organic_click_to_signup,
  SAFE_DIVIDE(cur.organic_new_customers, cur.organic_signups)          AS organic_signup_to_customer,
  -- brand vs non-brand search
  SAFE_DIVIDE(cur.gsc_brand_clicks, cur.gsc_brand_impressions)         AS brand_ctr,
  SAFE_DIVIDE(cur.gsc_nonbrand_clicks, cur.gsc_nonbrand_impressions)   AS nonbrand_ctr,
  SAFE_DIVIDE(cur.gsc_nonbrand_clicks, cur.gsc_clicks)                 AS nonbrand_share,
  cur.gsc_nonbrand_clicks * s.avg_cpc_eur                              AS nonbrand_traffic_value_eur,
  SAFE_DIVIDE(cur.gsc_nonbrand_clicks - prev.gsc_nonbrand_clicks, prev.gsc_nonbrand_clicks) AS nonbrand_clicks_mom,
  SAFE_DIVIDE(cur.gsc_brand_clicks - prev.gsc_brand_clicks, prev.gsc_brand_clicks)          AS brand_clicks_mom,
  t.new_customers_target_organic,
  SAFE_DIVIDE(cur.organic_new_customers, t.new_customers_target_organic)       AS customers_target_achievement,
  t.net_revenue_target_organic_eur,
  SAFE_DIVIDE(cur.organic_net_revenue_eur, t.net_revenue_target_organic_eur)   AS revenue_target_achievement,
  t.new_customers_target_total,
  SAFE_DIVIDE(cur.total_new_customers, t.new_customers_target_total)           AS total_customers_target_achievement,
  -- MoM: full month vs previous full month
  prev.organic_new_customers                                           AS organic_new_customers_prev_month,
  SAFE_DIVIDE(cur.organic_new_customers - prev.organic_new_customers, prev.organic_new_customers) AS organic_new_customers_mom,
  SAFE_DIVIDE(cur.total_net_revenue_eur - prev.total_net_revenue_eur, prev.total_net_revenue_eur) AS net_revenue_mom,
  -- YoY: same month last year
  ly.organic_new_customers                                             AS organic_new_customers_same_month_ly,
  SAFE_DIVIDE(cur.organic_new_customers - ly.organic_new_customers, ly.organic_new_customers)     AS organic_new_customers_yoy,
  SAFE_DIVIDE(cur.total_net_revenue_eur - ly.total_net_revenue_eur, ly.total_net_revenue_eur)     AS net_revenue_yoy
FROM m cur
LEFT JOIN m prev
  ON prev.site_id = cur.site_id AND prev.month = DATE_SUB(cur.month, INTERVAL 1 MONTH)
LEFT JOIN m ly
  ON ly.site_id = cur.site_id AND ly.month = DATE_SUB(cur.month, INTERVAL 1 YEAR)
JOIN `seo_platform.dim_site` s
  ON s.site_id = cur.site_id
LEFT JOIN (
  SELECT
    site_id, DATE(month) AS month,
    SUM(CASE WHEN channel = 'organic' THEN new_customers_target   ELSE 0 END) AS new_customers_target_organic,
    SUM(CASE WHEN channel = 'organic' THEN net_revenue_target_eur ELSE 0 END) AS net_revenue_target_organic_eur,
    SUM(new_customers_target)                                                 AS new_customers_target_total,
    SUM(net_revenue_target_eur)                                               AS net_revenue_target_total_eur
  FROM `seo_platform.raw_targets_monthly`
  GROUP BY site_id, DATE(month)
) t
  ON t.site_id = cur.site_id AND t.month = cur.month;
