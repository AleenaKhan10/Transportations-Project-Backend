CREATE OR REPLACE VIEW `agy-intelligence-hub.diamond.alerts` AS
WITH ranked AS (
  SELECT 
    * EXCEPT (driver_set_temp, reefer_mode_id, reefer_mode, samsara_reefer_mode),
    CASE WHEN samsara_reefer_mode = 'Dry Load' THEN 0 ELSE 2 END AS samsara_reefer_mode_id,
    CASE WHEN samsara_reefer_mode = 'Dry Load' THEN 'Off' ELSE 'On' END AS samsara_reefer_mode,
    ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY samsara_temp_time DESC) AS rn
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
  WHERE samsara_temp IS NOT NULL
),
classified AS (
  SELECT 
    trailer_id, 
    trip_id, 
    leg_id, 
    truck_id, 
    status, 
    required_reefer_mode,
    samsara_reefer_mode,
    COALESCE(samsara_reefer_mode_time, samsara_temp_time),
    priority_id, 
    priority, 
    max_allowed_deviation, 
    required_temp, 
    samsara_driver_set_point,
    COALESCE(samsara_driver_set_point_time, samsara_temp_time),
    samsara_temp, 
    ABS(ROUND(required_temp - samsara_temp, 3)) AS temp_diff,
    samsara_temp_time AS samsara_temp_time,
    DATETIME(samsara_temp_time, 'America/Chicago') AS samsara_temp_time_cdt,
    CASE 
      WHEN required_reefer_mode_id = 0 THEN 'ℹ️ Dry Load'
      WHEN (leg_id = 1 AND status_id = 3) OR (leg_id > 1 AND status_id NOT IN (0, 4)) THEN 
        CASE 
          WHEN required_temp = 99 THEN '🔥 99°F Required Temp'
          WHEN required_temp != samsara_driver_set_point THEN '⚠️ Driver Setpoint Mismatch'
          WHEN required_reefer_mode_id = 2 AND samsara_reefer_mode_id = 0 THEN '‼️ Attention / Issue ‼️'
          WHEN ABS(samsara_temp - required_temp) > max_allowed_deviation THEN '🚨 Temperature Out of Range'
          ELSE 'Ignore'
        END
      ELSE 'Ignore'
    END AS alert_type,
    CASE 
      WHEN required_reefer_mode_id = 0 AND samsara_reefer_mode_id != 0 THEN 'Reefer is ON'
    END AS remarks,
  FROM ranked
  WHERE rn = 1 
)
SELECT * FROM classified
