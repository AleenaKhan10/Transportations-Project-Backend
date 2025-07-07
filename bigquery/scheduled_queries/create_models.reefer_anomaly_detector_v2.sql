-- This is the final, comprehensive script to train the anomaly detection model.
-- It uses the correct MODEL_TYPE ('ARIMA_PLUS_XREG') and includes ALL relevant
-- features from the enhanced feature view for maximum model accuracy.

CREATE OR REPLACE MODEL `agy-intelligence-hub.models.reefer_anomaly_detector_v2`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS_XREG',
  TIME_SERIES_TIMESTAMP_COL='samsara_temp_time',
  TIME_SERIES_DATA_COL='samsara_temp',
  TIME_SERIES_ID_COL='trailer_id',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='AUTO_FREQUENCY'
) AS
SELECT
  -- 1. Core Time Series Columns (defined in OPTIONS)
  features.samsara_temp_time,
  features.trailer_id,
  features.samsara_temp,

  -- 2. All Other Columns are Automatically Used as Features (XREGs)

  -- Contextual Features (Categorical)
  features.status,
  features.reefer_mode,
  features.priority,

  -- Contextual Features (Numeric)
  features.required_temp,
  features.is_active_trip,
  features.hour_of_day,
  features.day_of_week,
  features.temp_deviation,
  features.temp_deviation_from_driver_set,
  features.setpoint_deviation_from_required,
  
  -- Engineered Trend & Volatility Features (with NULL handling)
  -- We must impute NULLs for window functions at the start of a series.
  -- Using 0 is a safe default.
  IFNULL(features.temp_volatility_10min, 0) AS temp_volatility_10min,
  IFNULL(features.temp_change_vs_10min_avg, 0) AS temp_change_vs_10min_avg,
  IFNULL(features.deviation_acceleration_pct, 0) AS deviation_acceleration_pct
  
FROM
  -- Using the definitive feature view
  `agy-intelligence-hub.golden.bqml_feature_view` AS features
LEFT JOIN
  `agy-intelligence-hub.golden.alert_feedback` AS feedback
  ON features.alert_id = feedback.alert_id
WHERE
  -- Define the training window
  features.samsara_temp_time 
    BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY) 
    AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  
  -- Exclude data points flagged as false positives by the operations team
  AND (feedback.alert_id IS NULL OR feedback.feedback_code NOT LIKE 'FALSE_POSITIVE%')
  
  -- Train only on data where the reefer was in an active, monitored state
  AND features.is_active_trip = 1;
