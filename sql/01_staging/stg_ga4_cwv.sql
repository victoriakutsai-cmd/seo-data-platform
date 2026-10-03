-- GA4: map default channel groups to the channel names used in commercial data,
-- so sessions can sit next to clicks / sign-ups / new customers in one row.
CREATE OR REPLACE VIEW `seo_platform.stg_ga4_channel_daily` AS
SELECT
  site_id,
  DATE(date) AS date,
  CASE session_default_channel_group
    WHEN 'Organic Search' THEN 'organic'
    WHEN 'Direct'         THEN 'direct'
    WHEN 'Paid Other'     THEN 'paid'
    WHEN 'Paid Search'    THEN 'paid'
    WHEN 'Display'        THEN 'paid'
    WHEN 'Referral'       THEN 'referral'
    WHEN 'Affiliates'     THEN 'referral'
    WHEN 'Organic Social' THEN 'social'
    WHEN 'Paid Social'    THEN 'social'
    ELSE 'other'
  END AS channel,
  sessions,
  engaged_sessions,
  sign_up_events
FROM `seo_platform.raw_ga4_channel_daily`;

-- PageSpeed Insights: Core Web Vitals with Google's "good" thresholds
CREATE OR REPLACE VIEW `seo_platform.stg_cwv_weekly` AS
SELECT
  site_id,
  DATE(check_date) AS check_date,
  strategy,
  lcp_ms,
  inp_ms,
  cls,
  performance_score,
  CASE WHEN lcp_ms <= 2500 THEN 1 ELSE 0 END AS lcp_good,
  CASE WHEN inp_ms <= 200  THEN 1 ELSE 0 END AS inp_good,
  CASE WHEN cls    <= 0.1  THEN 1 ELSE 0 END AS cls_good,
  CASE WHEN lcp_ms <= 2500 AND inp_ms <= 200 AND cls <= 0.1 THEN 1 ELSE 0 END AS cwv_pass
FROM `seo_platform.raw_psi_cwv_weekly`;
