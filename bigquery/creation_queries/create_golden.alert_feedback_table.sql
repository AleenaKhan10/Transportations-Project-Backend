CREATE TABLE IF NOT EXISTS `agy-intelligence-hub.golden.alert_feedback`
(
  alert_id STRING OPTIONS(description="Unique hash of the trailer and anomaly timestamp to identify the alert."),
  trailer_id STRING,
  trip_id STRING,
  anomaly_timestamp TIMESTAMP,
  feedback_timestamp TIMESTAMP,
  feedback_user STRING,
  feedback_code STRING OPTIONS(description="Standardized code: 'FALSE_POSITIVE_DEFROST', 'KNOWN_SENSOR_ISSUE', 'CONFIRMED_REAL', etc."),
  notes STRING
);