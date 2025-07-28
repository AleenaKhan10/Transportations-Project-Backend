CREATE OR REPLACE TABLE FUNCTION `agy-intelligence-hub.diamond.get_master_with_alerts`(only_latest BOOL) AS
WITH base_data AS (
  SELECT 
    * EXCEPT (samsara_driver_set_point, samsara_reefer_mode, reefer_mode, reefer_mode_id, samsara_temp_time, driver_set_temp),
    COALESCE(samsara_temp_time, ditat_temp_time) AS samsara_temp_time,
    samsara_driver_set_point AS driver_set_temp, -- NOTE: renaming to match Ditat's naming convention
    CASE 
      WHEN reefer_mode = 'On' THEN 'On'
      ELSE
        CASE 
          WHEN samsara_reefer_mode != 'Dry Load' THEN 'On'
          ELSE 'Off'
        END
    END AS reefer_mode, -- NOTE: renaming to match Ditat's naming convention
    CASE 
      WHEN reefer_mode = 'On' THEN 2
      ELSE
        CASE 
          WHEN samsara_reefer_mode != 'Dry Load' THEN 2
          ELSE 0
        END
    END AS reefer_mode_id -- NOTE: renaming to match Ditat's naming convention
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master_view`
  -- WHERE samsara_temp IS NOT NULL
),
ranked AS (
  SELECT 
    *,
    ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY samsara_temp_time DESC) AS rn
  FROM base_data
),
filtered AS (
  SELECT *
  FROM ranked
  WHERE 
    CASE 
      WHEN only_latest THEN rn = 1
      ELSE TRUE
    END
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
    reefer_mode, 
    reefer_mode_id,
    required_reefer_mode,
    required_reefer_mode_id,
    max_allowed_deviation,
    driver_set_temp, 
    required_temp, 
    samsara_temp,
    samsara_temp_time,
    ABS(ROUND(required_temp - samsara_temp, 3)) AS temp_diff,
    -- DATETIME(samsara_temp_time, 'America/Chicago') AS samsara_temp_time_cdt,
    CASE 
      WHEN required_reefer_mode_id = 0 THEN 'ℹ️ Dry Load'
      WHEN ((leg_id = 1 AND status_id = 3) OR (leg_id > 1 AND status_id NOT IN (0, 4))) AND samsara_temp IS NOT NULL THEN 
        CASE 
          WHEN required_temp = 99 THEN '🔥 99°F Required Temp'
          WHEN required_temp != driver_set_temp 
            AND driver_set_temp != 0
            THEN '⚠️ Driver Setpoint Mismatch'
          WHEN 
            ABS(samsara_temp - required_temp) > max_allowed_deviation 
            THEN '🚨 Temperature Out of Range'
          WHEN required_reefer_mode_id IN (1, 2) 
            AND reefer_mode_id = 0 
            -- AND ABS(samsara_temp - required_temp) > max_allowed_deviation -- NOTE: even if the temp is within limit, keeping the reefer off might be problematic
            THEN '‼️ Attention / Issue ‼️'
          ELSE NULL
        END
      ELSE NULL
    END AS alert_type,
    CASE 
      WHEN required_reefer_mode_id = 0 AND reefer_mode_id != 0 THEN 'Reefer is ON'
    END AS remarks,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time,
    rn  -- Include row number for reference if needed
  FROM filtered
)
SELECT * EXCEPT(rn) FROM classified