CREATE TABLE IF NOT EXISTS `agy-intelligence-hub.golden.ditat_samsara_merged_master` AS
WITH all_trips AS (
  -- Select all trips from source, without any restrictive time filter
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
),
closest_samsara_readings AS (
    -- Find the closest Samsara reading for each Ditat temperature record
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
    -- The join condition remains the same
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
  rn = 1; -- Only keep the closest Samsara reading for each Ditat record
