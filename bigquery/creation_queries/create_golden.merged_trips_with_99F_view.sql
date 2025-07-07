CREATE OR REPLACE VIEW `agy-intelligence-hub.golden.merged_trips_with_99F`
SELECT 
  *
FROM
  `agy-intelligence-hub.golden.ditat_samsara_merged_master`
WHERE 
  required_temp = 99
  -- AND trip_end_time <= DATETIME_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
