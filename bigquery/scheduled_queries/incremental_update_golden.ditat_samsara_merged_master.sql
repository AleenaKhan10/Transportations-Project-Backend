-- For now we're scheduling this query to run every 5 minutes. 
-- Later on, we may want to schedule it more or less frequently.
-- It efficiently updates the master table 
--   * with only the latest data 
--   * from the Ditat and Samsara sources 
--   * for the last 30 mins.
MERGE
  `agy-intelligence-hub.golden.ditat_samsara_merged_master` AS T
USING (
  -- The source query only looks at recent data (e.g., last 30 mins)
  -- to find new records and update existing ones.
  WITH
    all_trips AS (
    SELECT
      trailer_id,
      trip_id,
      leg_id,
      driver_id,
      truck_id,
      status_id,
      status,
      priority_id,
      priority,
      reefer_mode_id,
      reefer_mode,
      required_reefer_mode_id,
      required_reefer_mode,
      max_allowed_deviation,
      required_temp,
      driver_set_temp,
      actual_temp,
      temp_updated_on,
      trip_start_time,
      trip_end_time,
      leg_start_time,
      leg_end_time,
      sub_leg_start_time,
      sub_leg_end_time
    FROM
      `agy-intelligence-hub.golden.ditat_grouped_subtrip_level`
      -- Process data from the last 30 mins to catch any new or delayed records.
    WHERE
      temp_updated_on >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE) 
  ),
  closest_samsara_readings AS (
    SELECT
      d.*,
      CASE 
        WHEN s.actualReeferMode IS NULL THEN 'Dry Load'
        ELSE s.actualReeferMode
        END AS samsara_reefer_mode,
      CASE 
        WHEN s.actualReeferModeTime IS NULL THEN s.ambientTemperatureTime
        ELSE s.actualReeferModeTime
        END AS samsara_reefer_mode_time,
      CASE 
        WHEN s.driverSetPointInF IS NULL THEN 99
        ELSE s.driverSetPointInF
        END AS samsara_driver_set_point,
      CASE 
        WHEN s.driverSetPointTime IS NULL THEN s.ambientTemperatureTime
        ELSE s.driverSetPointTime
        END AS samsara_driver_set_point_time,
      s.ambientTemperatureInF AS samsara_temp,
      s.ambientTemperatureTime AS samsara_temp_time,
      ROW_NUMBER() OVER (PARTITION BY d.trailer_id, d.trip_id, d.temp_updated_on ORDER BY ABS(DATETIME_DIFF(s.ambientTemperatureTime, d.temp_updated_on, SECOND)) ) AS rn
    FROM
      all_trips d
    LEFT JOIN
      `silver.samsara_cleaned_view` s
    ON
      d.trailer_id = s.trailerName
      AND s.ambientTemperatureTime BETWEEN DATETIME_SUB(d.temp_updated_on, INTERVAL 30 MINUTE)
      AND DATETIME_ADD(d.temp_updated_on, INTERVAL 30 MINUTE) 
  )
  SELECT
    trailer_id,
    trip_id,
    leg_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority_id,
    priority,
    reefer_mode_id,
    reefer_mode,
    required_reefer_mode_id,
    required_reefer_mode,
    max_allowed_deviation,
    required_temp,
    driver_set_temp,
    actual_temp AS ditat_temp,
    samsara_temp,
    samsara_temp_time,
    temp_updated_on AS ditat_temp_time,
    samsara_reefer_mode,
    samsara_reefer_mode_time,
    samsara_driver_set_point,
    samsara_driver_set_point_time,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
  FROM
    closest_samsara_readings
  WHERE
    rn = 1 
) AS S
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
