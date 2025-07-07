CREATE VIEW IF NOT EXISTS `agy-intelligence-hub.golden.driver_setpoint_violations` AS
SELECT * FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
WHERE driver_set_temp != samsara_temp
  AND samsara_temp != 99
