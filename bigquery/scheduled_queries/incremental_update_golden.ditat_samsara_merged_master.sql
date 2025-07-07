-- For now we're scheduling this query to run every 15 minutes. 
-- Later on, we may want to schedule it more or less frequently.
-- It efficiently updates the master table 
--   * with only the latest data 
--   * from the Ditat and Samsara sources 
--   * for the last 2 hours.
MERGE
  `agy-intelligence-hub.golden.ditat_samsara_merged_master` AS T
USING
  (
    -- The source query now only looks at recent data (e.g., last 2 hours)
    -- to find new records and update existing ones.
  WITH
    recent_trips AS (
    SELECT
      trailer_id,
      trip_id,
      driver_id,
      truck_id,
      status_id,
      status,
      priority_id,
      priority,
      reefer_mode_id,
      reefer_mode,
      max_allowed_deviation,
      required_temp,
      driver_set_temp,
      actual_temp,
      temp_updated_on,
      trip_start_time,
      trip_end_time,
      sub_trip_start_time,
      sub_trip_end_time
    FROM
      `agy-intelligence-hub.golden.ditat_sub-trip_level_time_and_temp`
      -- Process data from the last 2 hours to catch any new or delayed records.
    WHERE
      temp_updated_on >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR) ),
    closest_samsara_readings AS (
    SELECT
      d.*,
      s.ambientTemperatureInF AS samsara_temp,
      s.ambientTemperatureTime AS samsara_temp_time,
      ROW_NUMBER() OVER (PARTITION BY d.trailer_id, d.trip_id, d.temp_updated_on ORDER BY ABS(DATETIME_DIFF(s.ambientTemperatureTime, d.temp_updated_on, SECOND)) ) AS rn
    FROM
      recent_trips d
    LEFT JOIN
      `silver.samsara_cleaned_view` s
    ON
      d.trailer_id = s.trailerName
      AND s.ambientTemperatureTime BETWEEN DATETIME_SUB(d.temp_updated_on, INTERVAL 30 MINUTE)
      AND DATETIME_ADD(d.temp_updated_on, INTERVAL 30 MINUTE) )
  SELECT
    trailer_id,
    trip_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority_id,
    priority,
    reefer_mode_id,
    reefer_mode,
    max_allowed_deviation,
    required_temp,
    driver_set_temp,
    actual_temp AS ditat_temp,
    samsara_temp,
    samsara_temp_time,
    temp_updated_on AS ditat_temp_time,
    trip_start_time,
    trip_end_time,
    sub_trip_start_time,
    sub_trip_end_time
  FROM
    closest_samsara_readings
  WHERE
    rn = 1 ) AS S
ON
  T.trailer_id = S.trailer_id
  AND T.trip_id = S.trip_id
  AND T.ditat_temp_time = S.ditat_temp_time -- Use a unique key to match rows
  WHEN NOT MATCHED THEN INSERT ROW
  WHEN MATCHED
  THEN
  -- This handles cases where a late-arriving Samsara reading might update a row
UPDATE
SET
  T.samsara_temp = S.samsara_temp,
  T.samsara_temp_time = S.samsara_temp_time;
