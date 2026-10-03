-- Weekly technical audit with derived rates
CREATE OR REPLACE VIEW `seo_platform.stg_site_audit_weekly` AS
SELECT
  site_id,
  DATE(check_date)                                                    AS check_date,
  pages_submitted,
  pages_indexed,
  SAFE_DIVIDE(pages_indexed, pages_submitted)                         AS indexation_rate,
  errors_4xx,
  errors_5xx,
  broken_internal_links,
  SAFE_DIVIDE(errors_4xx + errors_5xx, pages_submitted) * 1000        AS errors_per_1k_pages,
  uptime_pct
FROM `seo_platform.raw_site_audit_weekly`;
