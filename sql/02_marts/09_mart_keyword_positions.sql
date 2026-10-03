-- Keyword position distribution per site x month x keyword group, from the
-- last rank-tracker check of each month: how many tracked keywords sit in
-- positions 1-3, 4-10, 11-20, 21-100 or are not ranking.
CREATE OR REPLACE TABLE `seo_platform.mart_keyword_positions`
CLUSTER BY site_id, keyword_group
AS
WITH last_check AS (
  SELECT DATE_TRUNC(check_date, MONTH) AS month, MAX(check_date) AS check_date
  FROM `seo_platform.raw_rank_tracker_weekly`
  GROUP BY DATE_TRUNC(check_date, MONTH)
)
SELECT
  s.site_id, s.brand, s.vertical, s.geo,
  l.month,
  r.keyword_group,
  COUNT(*)                                                               AS keywords_tracked,
  SUM(CASE WHEN r.position BETWEEN 1  AND 3   THEN 1 ELSE 0 END)         AS pos_1_3,
  SUM(CASE WHEN r.position BETWEEN 4  AND 10  THEN 1 ELSE 0 END)         AS pos_4_10,
  SUM(CASE WHEN r.position BETWEEN 11 AND 20  THEN 1 ELSE 0 END)         AS pos_11_20,
  SUM(CASE WHEN r.position BETWEEN 21 AND 100 THEN 1 ELSE 0 END)         AS pos_21_100,
  SUM(CASE WHEN r.position IS NULL            THEN 1 ELSE 0 END)         AS not_ranking,
  SAFE_DIVIDE(SUM(CASE WHEN r.position <= 10 THEN 1 ELSE 0 END), COUNT(*)) AS top10_share,
  AVG(r.position)                                                        AS avg_position_ranking
FROM `seo_platform.raw_rank_tracker_weekly` r
JOIN last_check l ON l.check_date = r.check_date
JOIN `seo_platform.dim_site` s ON s.site_id = r.site_id
GROUP BY s.site_id, s.brand, s.vertical, s.geo, l.month, r.keyword_group;
