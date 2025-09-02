CREATE OR REPLACE TABLE FUNCTION `agy-intelligence-hub.diamond.get_master_with_alerts_v2`(only_latest BOOL) AS
WITH base AS (
  SELECT
    *,
    required_temp + max_allowed_deviation AS upper_limit,
    required_temp - max_allowed_deviation AS lower_limit,
    ABS(samsara_temp - required_temp) AS abs_diff,

    TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 15*60) * 15*60) AS window_start_15m,
    TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 10*60) * 10*60) AS window_start_10m,

    row_number() over (
      PARTITION BY 
        trailer_id, 
        trip_id, 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 15*60) * 15*60)
      ORDER BY samsara_temp_time ASC
    ) AS rn_asc_15m,

    row_number() over (
      PARTITION BY 
        trailer_id, 
        trip_id, 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 15*60) * 15*60)
      ORDER BY samsara_temp_time DESC
    ) AS rn_desc_15m,

    row_number() over (
      PARTITION BY 
        trailer_id, 
        trip_id, 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 10*60) * 10*60)
      ORDER BY samsara_temp_time ASC
    ) AS rn_asc_10m,

    row_number() over (
      PARTITION BY 
        trailer_id, 
        trip_id, 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(samsara_temp_time), 10*60) * 10*60)
      ORDER BY samsara_temp_time DESC
    ) AS rn_desc_10m
  from `golden.ditat_samsara_merged_master_view`
),

curr_prev AS (
  SELECT
    *,

    -- Last (current) values in 15m window
    last_value(samsara_temp) over (
      PARTITION BY trailer_id, trip_id, window_start_15m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS curr_temp,
    
    last_value(samsara_temp_time) over (
      PARTITION BY trailer_id, trip_id, window_start_15m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS curr_temp_time,
    
    last_value(status) over (
      PARTITION BY trailer_id, trip_id, window_start_15m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS curr_status,
    
    -- First (previous) values in 15m window
    first_value(samsara_temp) over (
      PARTITION BY trailer_id, trip_id, window_start_15m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS prev_temp,
    
    first_value(samsara_temp_time) over (
      PARTITION BY trailer_id, trip_id, window_start_15m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS prev_temp_time,
    
    -- First (previous) values in 10m window for status
    first_value(status) over (
      PARTITION BY trailer_id, trip_id, window_start_10m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS prev_status,
    
    first_value(samsara_temp_time) over (
      PARTITION BY trailer_id, trip_id, window_start_10m 
      ORDER BY samsara_temp_time
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS prev_status_time
  from base
),

base_logic_applied AS (
  SELECT 
    * EXCEPT (
      samsara_driver_set_point, 
      samsara_reefer_mode, 
      reefer_mode, 
      reefer_mode_id, 
      samsara_temp_time, 
      driver_set_temp
    ),
    COALESCE(samsara_temp_time, ditat_temp_time) AS samsara_temp_time,
    CASE 
      WHEN samsara_driver_set_point IS NULL OR samsara_driver_set_point = 0 
        THEN NULL 
      ELSE samsara_driver_set_point 
    END AS driver_set_temp,
    CASE 
      WHEN samsara_reefer_mode = 'Off' THEN 0
      WHEN samsara_reefer_mode IN ('Continuous', 'Start/Stop') THEN 2
      ELSE CASE WHEN reefer_mode_id IN (1, 2) THEN 2 ELSE 0 END
    END AS reefer_mode_id,
    CASE 
      WHEN ABS(curr_temp - required_temp) < ABS(prev_temp - required_temp) THEN true
      ELSE false
    END AS getting_normal,
    CASE
      WHEN prev_status = 'Loading' 
        AND curr_status = 'EnrouteToDelivery' 
        THEN true
      ELSE false
    END AS was_loading
  from curr_prev
),

ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY trailer_id, trip_id 
      ORDER BY samsara_temp_time DESC
    ) AS rn
  FROM base_logic_applied
),

filtered AS (
  SELECT * except (rn)
  FROM ranked
  WHERE CASE WHEN only_latest THEN rn = 1 ELSE TRUE END
),

classified AS (
  SELECT 
    trailer_id, 
    trip_id, 
    leg_id, 
    driver_id, 
    truck_id, 
    status, 
    status_id, 
    priority, 
    priority_id, 
    CASE WHEN reefer_mode_id = 2 THEN 'On' ELSE 'Off' END AS reefer_mode, 
    reefer_mode_id,
    required_reefer_mode,
    reefer_remote_mode, 
    required_reefer_mode_id,
    max_allowed_deviation,
    driver_set_temp, 
    required_temp, 
    samsara_temp,
    samsara_temp_time,
    ABS(ROUND(required_temp - samsara_temp, 3)) AS temp_diff,
    was_loading,
    getting_normal,
    CASE 
      WHEN (
        (leg_id = 1 AND status_id = 3) OR 
        (leg_id > 1 AND status_id NOT IN (0, 4))
      ) AND samsara_temp IS NOT NULL THEN 
        CASE 
          WHEN required_reefer_mode_id = 0 THEN 'ℹ️ Dry Load'
          WHEN required_temp = 99 THEN '🔥 99°F Required Temp'
          WHEN required_temp != driver_set_temp 
            AND driver_set_temp IS NOT NULL
            AND reefer_remote_mode != 'Dead'
            THEN '⚠️ Driver Setpoint Mismatch'
          WHEN required_reefer_mode_id IN (1, 2) 
            AND reefer_mode_id = 0 
            AND ABS(samsara_temp - required_temp) > max_allowed_deviation 
            THEN '‼️ Attention / Issue ‼️'
          WHEN ABS(samsara_temp - required_temp) > max_allowed_deviation 
            AND NOT was_loading
            THEN '🚨 Temperature Out of Range'
          ELSE NULL
        END
      ELSE NULL
    END AS alert_type,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time,
    derived_reefer_status
  FROM filtered
),

sub_classified AS (
  SELECT
    *,
    CASE 
      WHEN alert_type = 'ℹ️ Dry Load' AND reefer_mode_id != 0 THEN 'Reefer is ON' 
      WHEN alert_type = '🚨 Temperature Out of Range' AND getting_normal THEN 'Getting Normal'
    END AS remarks 
  FROM classified
)
SELECT * FROM sub_classified