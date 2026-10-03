-- Search Console: one row per site x day, total plus brand / non-brand split.
-- GSC bulk export stores a zero-based SUM of positions, so
-- average position = sum_position / impressions + 1.
CREATE OR REPLACE VIEW `seo_platform.stg_gsc_site_daily` AS
SELECT
  site_id,
  DATE(data_date)                                                             AS date,
  SUM(clicks)                                                                 AS clicks,
  SUM(impressions)                                                            AS impressions,
  SAFE_DIVIDE(SUM(clicks), SUM(impressions))                                  AS ctr,
  SAFE_DIVIDE(SUM(sum_position), SUM(impressions)) + 1                        AS avg_position,
  SUM(CASE WHEN query_group = 'brand'     THEN clicks      ELSE 0 END)        AS brand_clicks,
  SUM(CASE WHEN query_group = 'brand'     THEN impressions ELSE 0 END)        AS brand_impressions,
  SUM(CASE WHEN query_group = 'non_brand' THEN clicks      ELSE 0 END)        AS nonbrand_clicks,
  SUM(CASE WHEN query_group = 'non_brand' THEN impressions ELSE 0 END)        AS nonbrand_impressions,
  SAFE_DIVIDE(SUM(CASE WHEN query_group = 'non_brand' THEN sum_position ELSE 0 END),
              SUM(CASE WHEN query_group = 'non_brand' THEN impressions  ELSE 0 END)) + 1 AS nonbrand_avg_position
FROM `seo_platform.raw_gsc_site_daily`
WHERE search_type = 'web'
GROUP BY site_id, DATE(data_date);

-- Search Console: priority & brand keywords
CREATE OR REPLACE VIEW `seo_platform.stg_gsc_keyword_daily` AS
SELECT
  site_id,
  DATE(data_date)        AS date,
  LOWER(TRIM(query))     AS query,
  keyword_group,
  impressions,
  clicks,
  avg_position
FROM `seo_platform.raw_gsc_keyword_daily`;
