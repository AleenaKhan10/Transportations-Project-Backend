CREATE OR REPLACE VIEW `agy-intelligence-hub.diamond.alerts` AS
WITH ranked AS (
  SELECT 
    * EXCEPT (samsara_driver_set_point, samsara_reefer_mode, reefer_mode, reefer_mode_id, samsara_temp_time),
    COALESCE(samsara_temp_time, ditat_temp_time) AS samsara_temp_time,
    CASE 
      WHEN reefer_mode = 'On' THEN 'On'
      ELSE
        CASE 
          WHEN samsara_reefer_mode != 'Dry Load' THEN 'On'
          ELSE 'Off'
        END
    END AS reefer_mode,
    CASE 
      WHEN reefer_mode = 'On' THEN 2
      ELSE
        CASE 
          WHEN samsara_reefer_mode != 'Dry Load' THEN 2
          ELSE 0
        END
    END AS reefer_mode_id,
    ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY COALESCE(samsara_temp_time, ditat_temp_time) DESC) AS rn
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
  -- WHERE samsara_temp IS NOT NULL
),
classified AS (
  SELECT 
    trailer_id, 
    trip_id, 
    leg_id, 
    truck_id, 
    status, 
    reefer_mode, 
    required_reefer_mode,
    priority_id, 
    priority, 
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
          ELSE 'Ignore'
        END
      ELSE 'Ignore'
    END AS alert_type,
    CASE 
      WHEN required_reefer_mode_id = 0 AND reefer_mode_id != 0 THEN 'Reefer is ON'
    END AS remarks,
  FROM ranked
  WHERE rn = 1 
)
SELECT * FROM classified
