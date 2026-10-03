-- One row per site x day x channel: the full click -> sign-up -> new customer
-- funnel plus GA4 sessions and (for organic) Search Console clicks/impressions.
-- Replaces the manually filled "Daily" tab of every per-site report.
CREATE OR REPLACE TABLE `seo_platform.mart_site_daily`
PARTITION BY date
CLUSTER BY site_id, channel
AS
WITH commercial AS (
  SELECT
    site_id, date, channel,
    SUM(clicks)             AS clicks,
    SUM(signups)            AS signups,
    SUM(new_customers)      AS new_customers,
    SUM(transactions)       AS transactions,
    SUM(payments_eur)       AS payments_eur,
    SUM(gross_revenue_eur)  AS gross_revenue_eur,
    SUM(net_revenue_eur)    AS net_revenue_eur
  FROM `seo_platform.stg_commercial_daily`
  GROUP BY site_id, date, channel
),
ga4 AS (
  SELECT site_id, date, channel,
         SUM(sessions) AS sessions, SUM(engaged_sessions) AS engaged_sessions
  FROM `seo_platform.stg_ga4_channel_daily`
  GROUP BY site_id, date, channel
)
SELECT
  c.site_id,
  s.brand,
  s.vertical,
  s.geo,
  s.market,
  s.project,
  c.date,
  c.channel,
  c.clicks,
  c.signups,
  c.new_customers,
  c.transactions,
  c.payments_eur,
  c.gross_revenue_eur,
  c.net_revenue_eur,
  g.sessions,
  g.engaged_sessions,
  SAFE_DIVIDE(c.signups, c.clicks)         AS click_to_signup,
  SAFE_DIVIDE(c.new_customers, c.signups)  AS signup_to_customer,
  SAFE_DIVIDE(c.new_customers, c.clicks)   AS click_to_customer,
  CASE WHEN c.channel = 'organic' THEN gsc.clicks       END AS gsc_clicks,
  CASE WHEN c.channel = 'organic' THEN gsc.impressions  END AS gsc_impressions,
  CASE WHEN c.channel = 'organic' THEN gsc.ctr          END AS gsc_ctr,
  CASE WHEN c.channel = 'organic' THEN gsc.avg_position END AS gsc_avg_position,
  CASE WHEN c.channel = 'organic' THEN gsc.brand_clicks         END AS gsc_brand_clicks,
  CASE WHEN c.channel = 'organic' THEN gsc.brand_impressions    END AS gsc_brand_impressions,
  CASE WHEN c.channel = 'organic' THEN gsc.nonbrand_clicks      END AS gsc_nonbrand_clicks,
  CASE WHEN c.channel = 'organic' THEN gsc.nonbrand_impressions END AS gsc_nonbrand_impressions
FROM commercial c
JOIN `seo_platform.dim_site` s
  ON s.site_id = c.site_id
LEFT JOIN ga4 g
  ON g.site_id = c.site_id AND g.date = c.date AND g.channel = c.channel
LEFT JOIN `seo_platform.stg_gsc_site_daily` gsc
  ON gsc.site_id = c.site_id AND gsc.date = c.date;
