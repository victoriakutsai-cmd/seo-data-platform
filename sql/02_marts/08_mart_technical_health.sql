-- Technical health per site x week: Core Web Vitals, indexation, errors, uptime,
-- combined into one 0-100 score so a portfolio of sites can be ranked at a glance.
--   score = 30 x CWV pass (mobile)            -- 1 if LCP, INP and CLS are all "good"
--         + 30 x indexation rate              -- indexed / submitted pages
--         + 25 x error score                  -- 1 at 0 errors per 1k pages, 0 at 20+
--         + 15 x uptime score                 -- 1 at 100%, 0 at 99.0% or lower
CREATE OR REPLACE TABLE `seo_platform.mart_technical_health`
CLUSTER BY site_id
AS
WITH cwv AS (
  SELECT site_id, check_date, lcp_ms, inp_ms, cls, performance_score, cwv_pass
  FROM `seo_platform.stg_cwv_weekly`
  WHERE strategy = 'mobile'
)
SELECT
  s.site_id, s.brand, s.vertical, s.geo, s.market,
  a.check_date,
  c.lcp_ms, c.inp_ms, c.cls, c.performance_score, c.cwv_pass,
  a.pages_submitted, a.pages_indexed, a.indexation_rate,
  a.errors_4xx, a.errors_5xx, a.broken_internal_links, a.errors_per_1k_pages, a.uptime_pct,
  ROUND(
      30 * COALESCE(c.cwv_pass, 0)
    + 30 * COALESCE(a.indexation_rate, 0)
    + 25 * GREATEST(0, 1 - a.errors_per_1k_pages / 20)
    + 15 * GREATEST(0, LEAST(1, (a.uptime_pct - 99.0) / 1.0))
  , 1)                                                               AS tech_health_score
FROM `seo_platform.stg_site_audit_weekly` a
JOIN `seo_platform.dim_site` s ON s.site_id = a.site_id
LEFT JOIN cwv c ON c.site_id = a.site_id AND c.check_date = a.check_date;
