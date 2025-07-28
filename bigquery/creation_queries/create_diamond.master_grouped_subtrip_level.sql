CREATE OR REPLACE VIEW `agy-intelligence-hub.diamond.master_grouped_subtrip_level` AS
WITH grouped AS (
  SELECT
    trailer_id,
    trip_id,
    leg_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority,
    ARRAY_AGG(STRUCT(
      reefer_mode_id,
      reefer_mode,
      required_temp,
      driver_set_temp,
      samsara_temp,
      samsara_temp_time,
      alert_type,
      remarks
    ) ORDER BY samsara_temp_time) as t,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
  FROM
    `agy-intelligence-hub.diamond.get_master_with_alerts`(FALSE)
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
ORDER BY 1, 2, 3 ,4, 5