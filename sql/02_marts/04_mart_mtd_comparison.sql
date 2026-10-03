-- MTD vs the SAME PERIOD of the previous month.
--
-- Each source has its own "latest complete day":
--   * commercial (Snowflake) usually D-1
--   * Search Console usually D-3 (data lag)
-- Comparing 1-29 Sep (commercial) with 1-29 Aug is fair; comparing GSC 1-29 Sep
-- when GSC only has data up to the 27th is not. So every source gets its own
-- window and a human-readable label ("1 Sep - 27 Sep 2026 vs 1 Aug - 27 Aug 2026")
-- that is shown on the report, so readers always know which dates are compared.
--
-- DATE_SUB(date, INTERVAL 1 MONTH) clamps to month end (31 Mar -> 28/29 Feb),
-- so the previous-month window never spills into the current month.
--
-- Edge case: on the first days of a month commercial data is already in the new
-- month while GSC still ends in the previous one (e.g. commercial to 2 Oct,
-- GSC to 30 Sep). The two sources then compare different months: commercial
-- 1-2 Oct vs 1-2 Sep, GSC 1-30 Sep vs 1-30 Aug. This is intended (each source
-- shows its latest complete MTD) and the period labels make it explicit.
CREATE OR REPLACE TABLE `seo_platform.mart_mtd_comparison`
AS
WITH windows AS (
  SELECT 'commercial' AS source, MAX(date) AS cur_end FROM `seo_platform.stg_commercial_daily`
  UNION ALL
  SELECT 'gsc'        AS source, MAX(date) AS cur_end FROM `seo_platform.stg_gsc_site_daily`
),
w AS (
  SELECT
    source,
    DATE_TRUNC(cur_end, MONTH)                             AS cur_start,
    cur_end,
    DATE_SUB(DATE_TRUNC(cur_end, MONTH), INTERVAL 1 MONTH) AS prev_start,
    DATE_SUB(cur_end, INTERVAL 1 MONTH)                    AS prev_end
  FROM windows
),
labels AS (
  SELECT
    source, cur_start, cur_end, prev_start, prev_end,
    CONCAT(FORMAT_DATE('%d %b', cur_start), ' - ', FORMAT_DATE('%d %b %Y', cur_end),
           ' vs ',
           FORMAT_DATE('%d %b', prev_start), ' - ', FORMAT_DATE('%d %b %Y', prev_end)) AS period_label
  FROM w
),
commercial AS (
  SELECT
    d.site_id,
    SUM(CASE WHEN d.date BETWEEN l.cur_start  AND l.cur_end  AND d.channel = 'organic' THEN d.new_customers ELSE 0 END) AS organic_new_customers_mtd,
    SUM(CASE WHEN d.date BETWEEN l.prev_start AND l.prev_end AND d.channel = 'organic' THEN d.new_customers ELSE 0 END) AS organic_new_customers_prev_mtd,
    SUM(CASE WHEN d.date BETWEEN l.cur_start  AND l.cur_end  AND d.channel = 'organic' THEN d.signups ELSE 0 END)       AS organic_signups_mtd,
    SUM(CASE WHEN d.date BETWEEN l.prev_start AND l.prev_end AND d.channel = 'organic' THEN d.signups ELSE 0 END)       AS organic_signups_prev_mtd,
    SUM(CASE WHEN d.date BETWEEN l.cur_start  AND l.cur_end  THEN d.new_customers ELSE 0 END)    AS total_new_customers_mtd,
    SUM(CASE WHEN d.date BETWEEN l.prev_start AND l.prev_end THEN d.new_customers ELSE 0 END)    AS total_new_customers_prev_mtd,
    SUM(CASE WHEN d.date BETWEEN l.cur_start  AND l.cur_end  THEN d.net_revenue_eur ELSE 0 END)  AS net_revenue_mtd,
    SUM(CASE WHEN d.date BETWEEN l.prev_start AND l.prev_end THEN d.net_revenue_eur ELSE 0 END)  AS net_revenue_prev_mtd,
    SUM(CASE WHEN d.date BETWEEN l.cur_start  AND l.cur_end  THEN d.transactions ELSE 0 END)     AS transactions_mtd,
    SUM(CASE WHEN d.date BETWEEN l.prev_start AND l.prev_end THEN d.transactions ELSE 0 END)     AS transactions_prev_mtd
  FROM `seo_platform.mart_site_daily` d
  CROSS JOIN labels l
  WHERE l.source = 'commercial'
    AND d.date BETWEEN l.prev_start AND l.cur_end
  GROUP BY d.site_id
),
gsc AS (
  SELECT
    g.site_id,
    SUM(CASE WHEN g.date BETWEEN l.cur_start  AND l.cur_end  THEN g.clicks ELSE 0 END)      AS gsc_clicks_mtd,
    SUM(CASE WHEN g.date BETWEEN l.prev_start AND l.prev_end THEN g.clicks ELSE 0 END)      AS gsc_clicks_prev_mtd,
    SUM(CASE WHEN g.date BETWEEN l.cur_start  AND l.cur_end  THEN g.impressions ELSE 0 END) AS gsc_impressions_mtd,
    SUM(CASE WHEN g.date BETWEEN l.prev_start AND l.prev_end THEN g.impressions ELSE 0 END) AS gsc_impressions_prev_mtd,
    SUM(CASE WHEN g.date BETWEEN l.cur_start  AND l.cur_end  THEN g.brand_clicks ELSE 0 END)    AS gsc_brand_clicks_mtd,
    SUM(CASE WHEN g.date BETWEEN l.prev_start AND l.prev_end THEN g.brand_clicks ELSE 0 END)    AS gsc_brand_clicks_prev_mtd,
    SUM(CASE WHEN g.date BETWEEN l.cur_start  AND l.cur_end  THEN g.nonbrand_clicks ELSE 0 END) AS gsc_nonbrand_clicks_mtd,
    SUM(CASE WHEN g.date BETWEEN l.prev_start AND l.prev_end THEN g.nonbrand_clicks ELSE 0 END) AS gsc_nonbrand_clicks_prev_mtd
  FROM `seo_platform.stg_gsc_site_daily` g
  CROSS JOIN labels l
  WHERE l.source = 'gsc'
    AND g.date BETWEEN l.prev_start AND l.cur_end
  GROUP BY g.site_id
)
SELECT
  s.site_id, s.brand, s.vertical, s.geo, s.market,
  lc.cur_end                                                          AS commercial_data_until,
  lc.period_label                                                     AS commercial_period,
  c.organic_new_customers_mtd, c.organic_new_customers_prev_mtd,
  SAFE_DIVIDE(c.organic_new_customers_mtd - c.organic_new_customers_prev_mtd, c.organic_new_customers_prev_mtd) AS organic_new_customers_vs_prev,
  c.organic_signups_mtd, c.organic_signups_prev_mtd,
  SAFE_DIVIDE(c.organic_signups_mtd - c.organic_signups_prev_mtd, c.organic_signups_prev_mtd)                   AS organic_signups_vs_prev,
  c.total_new_customers_mtd, c.total_new_customers_prev_mtd,
  SAFE_DIVIDE(c.total_new_customers_mtd - c.total_new_customers_prev_mtd, c.total_new_customers_prev_mtd)       AS total_new_customers_vs_prev,
  c.net_revenue_mtd, c.net_revenue_prev_mtd,
  SAFE_DIVIDE(c.net_revenue_mtd - c.net_revenue_prev_mtd, c.net_revenue_prev_mtd)                               AS net_revenue_vs_prev,
  c.transactions_mtd, c.transactions_prev_mtd,
  SAFE_DIVIDE(c.transactions_mtd - c.transactions_prev_mtd, c.transactions_prev_mtd)                            AS transactions_vs_prev,
  lg.cur_end                                                          AS gsc_data_until,
  lg.period_label                                                     AS gsc_period,
  g.gsc_clicks_mtd, g.gsc_clicks_prev_mtd,
  SAFE_DIVIDE(g.gsc_clicks_mtd - g.gsc_clicks_prev_mtd, g.gsc_clicks_prev_mtd)                                  AS gsc_clicks_vs_prev,
  g.gsc_impressions_mtd, g.gsc_impressions_prev_mtd,
  SAFE_DIVIDE(g.gsc_impressions_mtd - g.gsc_impressions_prev_mtd, g.gsc_impressions_prev_mtd)                   AS gsc_impressions_vs_prev,
  g.gsc_brand_clicks_mtd, g.gsc_brand_clicks_prev_mtd,
  SAFE_DIVIDE(g.gsc_brand_clicks_mtd - g.gsc_brand_clicks_prev_mtd, g.gsc_brand_clicks_prev_mtd)                AS gsc_brand_clicks_vs_prev,
  g.gsc_nonbrand_clicks_mtd, g.gsc_nonbrand_clicks_prev_mtd,
  SAFE_DIVIDE(g.gsc_nonbrand_clicks_mtd - g.gsc_nonbrand_clicks_prev_mtd, g.gsc_nonbrand_clicks_prev_mtd)       AS gsc_nonbrand_clicks_vs_prev
FROM `seo_platform.dim_site` s
CROSS JOIN (SELECT * FROM labels WHERE source = 'commercial') lc
CROSS JOIN (SELECT * FROM labels WHERE source = 'gsc') lg
LEFT JOIN commercial c ON c.site_id = s.site_id
LEFT JOIN gsc g        ON g.site_id = s.site_id;
