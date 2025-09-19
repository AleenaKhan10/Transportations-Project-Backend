CREATE OR REPLACE TABLE FUNCTION `agy-intelligence-hub.diamond.get_master_grouped_subtrip_level`(since_value INT64, since_unit STRING, if_has_atleast_one_alert BOOL) AS
WITH filtered AS (
  SELECT * FROM `diamond.get_master_with_alerts_v2`(FALSE)
  WHERE 
    samsara_temp_time >= CASE since_unit
      WHEN 'MICROSECOND' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value MICROSECOND)
      WHEN 'MILLISECOND' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value MILLISECOND)
      WHEN 'SECOND' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value SECOND)
      WHEN 'MINUTE' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value MINUTE)
      WHEN 'HOUR' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value HOUR)
      WHEN 'DAY' THEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value DAY)
      ELSE TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL since_value HOUR) -- Default to HOUR
    END
),
ddp_cache AS (
  SELECT DISTINCT
   * EXCEPT (ingestedAt, raw_data)
  FROM `bronze.weather_cache`
  QUALIFY row_number() over (
    PARTITION BY 
      CAST(ROUND(latitude, 2) AS STRING), 
      CAST(ROUND(longitude, 2) AS STRING), 
      TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), 60*60) * 60*60) 
    ORDER BY ingestedAt DESC
  ) = 1
),
weather_info_added AS (
  SELECT DISTINCT
    a.*,
    b.* EXCEPT (latitude, longitude),
    TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(a.samsara_temp_time), 60*60) * 60*60) AS window_60min
  FROM filtered a
  LEFT JOIN ddp_cache b
    ON ROUND(a.latitude, 2) = ROUND(b.latitude, 2)
    AND ROUND(a.longitude, 2) = ROUND(b.longitude, 2)
    AND a.samsara_temp_time 
      BETWEEN TIMESTAMP_SECONDS(UNIX_SECONDS(b.timestamp) - 30*60) 
      AND TIMESTAMP_SECONDS(UNIX_SECONDS(b.timestamp) + 30*60)
),
alerts_in_group AS (
  SELECT
   *,
   COUNTIF(alert_type IS NOT NULL) OVER(PARTITION BY 
    trailer_id,
    leg_id,
    trip_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
  ) > 0 AS has_any_alert
  FROM weather_info_added
),
grouped AS (
  SELECT
    trailer_id,
    trip_id,
    leg_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority,
    ANY_VALUE(has_any_alert) AS has_any_alert,
    ARRAY_AGG(STRUCT(
      reefer_mode_id,
      reefer_mode,
      required_temp,
      driver_set_temp,
      samsara_temp,
      samsara_temp_time,
      alert_type,
      latitude,
      longitude,
      location,
      region,
      temperature,
      description,
      wind_mph,
      remarks
    ) ORDER BY samsara_temp_time DESC) as t,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
  FROM
    alerts_in_group
  GROUP BY
    trailer_id,
    leg_id,
    trip_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
)
SELECT * FROM grouped
WHERE 
  CASE if_has_atleast_one_alert
    WHEN TRUE THEN has_any_alert
    ELSE TRUE
  END
ORDER BY 1, 2, 3 ,4, 5