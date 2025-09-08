-- =================================================================================================
-- Merged Reefer Status View for Samsara
--
-- Purpose:
-- This view is designed to produce a clean and enriched dataset. It intelligently combines
-- temperature sensor readings from Samsara with their corresponding reefer (refrigerated trailer)
-- status, such as run mode and temperature setpoint.
--
-- Methodology:
-- Instead of relying on conventional joins, which can be inefficient and complex for this type of
-- time-series data, the query employs a "forward fill" technique. It begins by consolidating all
-- relevant events—temperature readings, changes in reefer mode, and setpoint adjustments—into a
-- single, chronologically ordered timeline. Following this, a window function is used to propagate
-- the last known reefer status forward onto each temperature reading. This approach results in a
-- view that is not only fast and accurate but also highly scalable.
-- =================================================================================================
 
-- CREATE OR REPLACE VIEW `agy-intelligence-hub.silver.samsara_cleaned_view` AS
 
-- Step 1: Deduplicate sensor readings
-- Remove duplicate records, keeping the most recently ingested version of each unique reading
WITH distinct_records AS (
  SELECT *
  FROM `agy-intelligence-hub.bronze.samsara_full`
  -- This ensure we only take records that actually have a temperature
  WHERE ambientTemperature IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY trailerName, sensorId, sensorName, installedGateway, externalIds, enabledForMobile, notes, licensePlate, trailerSerialNumber, ambientTemperatureTime
    ORDER BY ingestedAt DESC
  ) = 1
),
 
-- Step 2: Process sensor data
-- Convert temperature units, parse timestamps, extract JSON fields, and initialize status columns
samsara_processed AS (
  SELECT
    sensorId,
    sensorName,
    ambientTemperature, -- Original value in milli-degrees Celsius
    ROUND(((ambientTemperature / 1000))*(9/5) + 32, 2) AS ambientTemperatureInF,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', ambientTemperatureTime) AS ambientTemperatureTime,
    vehicleId,
    trailerId,
    REGEXP_EXTRACT(trailerName, 'RX[0-9]{5}E') AS trailerName,
    JSON_EXTRACT_SCALAR(tags, "$[0].id") AS tagId,
    JSON_EXTRACT_SCALAR(tags, "$[0].name") AS tagName,
    JSON_EXTRACT_SCALAR(installedGateway, "$.model") AS installedGatewayModel,
    JSON_EXTRACT_SCALAR(installedGateway, "$.serial") AS installedGatewaySerial,
    JSON_EXTRACT_SCALAR(externalIds, "$['samsara.serial']") AS installedGatewaySerialAlphaNum,
    JSON_EXTRACT_SCALAR(externalIds, "$['samsara.vin']") AS installedGatewayVIN,
    enabledForMobile,
    notes,
    licensePlate,
    ingestedAt,
    trailerSerialNumber,
    -- Initialize status columns for forward fill
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    -- Master timestamp for chronological ordering
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', ambientTemperatureTime) AS time_axis
  FROM distinct_records
),
 
-- Step 3: Extract reefer modes (backup source)
-- Reefer modes from gettrailerstatsfeed endpoint - less reliable source
reefer_modes_backup AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    reeferRunModeValue AS actualReeferModeBkp,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferRunModeTime) AS actualReeferModeBkpTime,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferRunModeTime) AS time_axis
  FROM `bronze.samsara_trailer_stats`
),
 
-- Extract Reefer modes (primary source)
-- Reefer modes from v1getassetsreefers endpoint - more reliable source
reefer_modes AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CASE
      WHEN CONTAINS_SUBSTR(JSON_EXTRACT_SCALAR(rmode_item, '$.status'), 'Continuous') THEN 'Continuous'
      WHEN CONTAINS_SUBSTR(JSON_EXTRACT_SCALAR(rmode_item, '$.status'), 'Start/Stop') THEN 'Start/Stop'
      WHEN JSON_EXTRACT_SCALAR(rmode_item, '$.status') = 'Off' THEN 'Off'
      WHEN REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(rmode_item, '$.status'), '^Active$') THEN 'Continuous'
      ELSE null
    END AS actualReeferMode,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(rmode_item, '$.changedAtMs') AS INT64)) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(rmode_item, '$.changedAtMs') AS INT64)) AS time_axis
  FROM
    `bronze.samsara_detailed_trailer_stats`,
    UNNEST(JSON_EXTRACT_ARRAY(powerStatus)) AS rmode_item
  QUALIFY ROW_NUMBER() OVER (PARTITION BY trailerName, actualReeferMode, actualReeferModeTime ORDER BY ingestedAt DESC) = 1
),
 
-- Step 4: Extract setpoint events (backup source)
-- Setpoints from gettrailerstatsfeed endpoint - less reliable source
setpoints_backup AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    reeferSetPointTemperatureMilliCZone1Value AS driverSetPointBkp,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferSetPointTemperatureMilliCZone1Time) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferSetPointTemperatureMilliCZone1Time) AS time_axis
  FROM `bronze.samsara_trailer_stats`
),
 
-- Extract setpoint events (primary source)
-- Setpoints from v1getassetsreefers endpoint - more reliable source
setpoints AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    CAST(JSON_EXTRACT_SCALAR(setpoint_item, '$.tempInMilliC') AS INT64) AS driverSetPoint,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(setpoint_item, '$.changedAtMs') AS INT64)) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(setpoint_item, '$.changedAtMs') AS INT64)) AS time_axis,
  FROM
    `bronze.samsara_detailed_trailer_stats`,
    UNNEST(JSON_EXTRACT_ARRAY(setPoint)) AS setpoint_item
  QUALIFY ROW_NUMBER() OVER (PARTITION BY name, driverSetPoint, driverSetPointTime ORDER BY ingestedAt DESC) = 1
),
 
-- Extract discharge air temp events
-- This is used to determine if the reefer remote is working
-- The logic is:
--   If discharge air and driver setpoint (primary source) haven't changed
--   over the last 15 minutes, then the reefer remote is dead
discharge_airs AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    CAST(JSON_EXTRACT_SCALAR(rair_item, '$.tempInMilliC') AS INT64) AS dischargeAirTemp,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(rair_item, '$.changedAtMs') AS INT64)) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    CAST(null AS STRING) AS locationName,
    null AS latitude,
    null AS longitude,
    null AS speedMilesPerHour,
    CAST(null AS TIMESTAMP) AS locationTime,
    TIMESTAMP_MILLIS(CAST(JSON_EXTRACT_SCALAR(rair_item, '$.changedAtMs') AS INT64)) AS time_axis,
  FROM
    `bronze.samsara_detailed_trailer_stats`,
    UNNEST(JSON_EXTRACT_ARRAY(dischargeAirTemperature)) AS rair_item
  QUALIFY ROW_NUMBER() OVER (PARTITION BY name, dischargeAirTemp, dischargeAirTempTime ORDER BY ingestedAt DESC) = 1
),
 
 --Extract GPS co-ordinates data for live location
location_data AS (
  SELECT DISTINCT
    null AS sensorId,
    CAST(null AS STRING) AS sensorName,
    null AS ambientTemperature,
    null AS ambientTemperatureInF,
    CAST(null AS TIMESTAMP) AS ambientTemperatureTime,
    CAST(null AS STRING) AS vehicleId,
    CAST(null AS STRING) AS trailerId,
    name AS trailerName,
    CAST(null AS STRING) AS tagId,
    CAST(null AS STRING) AS tagName,
    CAST(null AS STRING) AS installedGatewayModel,
    CAST(null AS STRING) AS installedGatewaySerial,
    CAST(null AS STRING) AS installedGatewaySerialAlphaNum,
    CAST(null AS STRING) AS installedGatewayVIN,
    CAST(null AS BOOL) AS enabledForMobile,
    CAST(null AS STRING) AS notes,
    CAST(null AS STRING) AS licensePlate,
    ingestedAt,
    CAST(null AS STRING) AS trailerSerialNumber,
    null AS dischargeAirTemp,
    CAST(null AS TIMESTAMP) AS dischargeAirTempTime,
    null AS driverSetPoint,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    null AS driverSetPointBkp,
    CAST(null AS TIMESTAMP) AS driverSetPointTimeBkp,
    CAST(null AS STRING) AS actualReeferMode,
    CAST(null AS TIMESTAMP) AS actualReeferModeTime,
    CAST(null AS STRING) AS actualReeferModeBkp,
    CAST(null AS TIMESTAMP) AS actualReeferModeTimeBkp,
    locationLocation AS locationName,
    locationLatitude AS latitude,
    locationLongitude AS longitude,
    locationSpeedmilesperhour AS speedMilesPerHour,
    TIMESTAMP_MILLIS(locationTimeMs) AS locationTime,
    TIMESTAMP_MILLIS(locationTimeMs) AS time_axis,
  FROM
    `bronze.samsara_detailed_locations`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY name, locationLocation, locationTimems ORDER BY ingestedAt DESC) = 1
),
 
-- Step 5: Create unified timeline
-- Combine all event types into a single chronologically ordered dataset
unioned AS (
  SELECT * FROM samsara_processed WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM reefer_modes WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM reefer_modes_backup WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM setpoints WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM setpoints_backup WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM discharge_airs WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM location_data WHERE time_axis IS NOT NULL
),
 
-- Step 6: Apply forward fill logic
-- Use window functions to propagate the most recent status values to subsequent temperature readings
forward_filled AS (
  SELECT
    * EXCEPT(
      dischargeAirTemp,
      dischargeAirTempTime,
      driverSetPoint,
      driverSetPointTime,
      driverSetPointBkp,
      driverSetPointTimeBkp,
      actualReeferMode,
      actualReeferModeTime,
      actualReeferModeBkp,
      actualReeferModeTimeBkp,
      locationName,
      latitude,
      longitude,
      speedMilesPerHour,
      locationTime
    ),
    LAST_VALUE(dischargeAirTemp IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS dischargeAirTemp,
    LAST_VALUE(dischargeAirTempTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS dischargeAirTempTime,
    LAST_VALUE(driverSetPoint IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPoint,
    LAST_VALUE(driverSetPointTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPointTime,
    LAST_VALUE(driverSetPointBkp IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPointBkp,
    LAST_VALUE(driverSetPointTimeBkp IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPointTimeBkp,
    LAST_VALUE(actualReeferMode IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferMode,
    LAST_VALUE(actualReeferModeTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferModeTime,
    LAST_VALUE(actualReeferModeBkp IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferModeBkp,
    LAST_VALUE(actualReeferModeTimeBkp IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferModeTimeBkp,
    LAST_VALUE(locationName IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS locationName,
    LAST_VALUE(latitude IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS latitude,
    LAST_VALUE(longitude IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS longitude,
    LAST_VALUE(speedMilesPerHour IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS speedMilesPerHour,
    LAST_VALUE(locationTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS locationTime
  FROM unioned
),
 
-- Step 7: Consolidate all sources
-- Prefer primary source over backup when available
-- Determine if the reefer remote is actually working
final AS (
  SELECT
    * EXCEPT(
      dischargeAirTemp,
      dischargeAirTempTime,
      driverSetPoint,
      driverSetPointTime,
      driverSetPointBkp,
      driverSetPointTimeBkp,
      actualReeferMode,
      actualReeferModeTime,
      actualReeferModeBkp,
      actualReeferModeTimeBkp,
      time_axis
    ),
    CASE
      WHEN (time_axis - dischargeAirTempTime) > INTERVAL 15 MINUTE AND (time_axis - driverSetPointTime) > INTERVAL 15 MINUTE THEN 'Dead'
      ELSE 'Working'
    END AS reeferRemoteMode,
    COALESCE(actualReeferMode, actualReeferModeBkp) AS actualReeferMode,
    COALESCE(actualReeferModeTime, actualReeferModeTimeBkp) AS actualReeferModeTime,
    COALESCE(driverSetPoint, driverSetPointBkp) AS driverSetPoint,
    CASE
      WHEN COALESCE(driverSetPoint, driverSetPointBkp) = 0 THEN 0
      ELSE ROUND(((COALESCE(driverSetPoint, driverSetPointBkp) / 1000))*(9/5) + 32, 0)
    END AS driverSetPointInF,
    COALESCE(driverSetPointTime, driverSetPointTimeBkp) AS driverSetPointTime
  FROM forward_filled
)
 
-- Final output: Return enriched temperature readings with forward-filled reefer status
SELECT DISTINCT *
FROM final
WHERE ambientTemperatureInF IS NOT NULL
ORDER BY ambientTemperatureTime DESC