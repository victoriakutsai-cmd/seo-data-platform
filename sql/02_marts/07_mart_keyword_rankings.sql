-- Priority & brand keyword rankings (from Search Console, not scraping):
-- monthly average position, change vs previous month, Top-10 flag,
-- and the latest available position.
CREATE OR REPLACE TABLE `seo_platform.mart_keyword_rankings`
CLUSTER BY site_id, keyword_group
AS
WITH monthly AS (
  SELECT
    site_id, query, keyword_group,
    DATE_TRUNC(date, MONTH)                                        AS month,
    SAFE_DIVIDE(SUM(avg_position * impressions), SUM(impressions)) AS avg_position,
    SUM(impressions)                                               AS impressions,
    SUM(clicks)                                                    AS clicks
  FROM `seo_platform.stg_gsc_keyword_daily`
  GROUP BY site_id, query, keyword_group, DATE_TRUNC(date, MONTH)
),
latest AS (
  SELECT k.site_id, k.query, k.avg_position AS latest_position, k.date AS latest_date
  FROM `seo_platform.stg_gsc_keyword_daily` k
  JOIN (SELECT MAX(date) AS d FROM `seo_platform.stg_gsc_keyword_daily`) mx
    ON k.date = mx.d
)
SELECT
  s.brand, s.vertical, s.geo,
  m.*,
  LAG(m.avg_position) OVER (PARTITION BY m.site_id, m.query ORDER BY m.month)          AS avg_position_prev_month,
  -- positive = moved UP (closer to #1)
  LAG(m.avg_position) OVER (PARTITION BY m.site_id, m.query ORDER BY m.month) - m.avg_position AS position_change,
  CASE WHEN m.avg_position <= 10 THEN 1 ELSE 0 END                                     AS is_top10,
  l.latest_position,
  l.latest_date
FROM monthly m
JOIN `seo_platform.dim_site` s ON s.site_id = m.site_id
LEFT JOIN latest l ON l.site_id = m.site_id AND l.query = m.query;
