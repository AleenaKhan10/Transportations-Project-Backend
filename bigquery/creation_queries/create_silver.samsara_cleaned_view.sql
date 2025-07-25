-- =================================================================================================
-- Samsara Merged Reefer Status View
-- Purpose: This view creates a clean, enriched dataset by combining Samsara temperature sensor
--          readings with their corresponding reefer status.
--
-- How it works: Instead of using slow, complex joins, this query takes a more elegant
--               "forward fill" approach. It gathers all events (temperature readings, reefer mode
--               changes, and setpoint changes) into a single, chronological timeline. Then, it
--               uses a window function to "fill forward" the last known reefer status onto each
--               temperature reading. The result is a fast, accurate, and scalable view.
-- =================================================================================================

CREATE OR REPLACE VIEW `agy-intelligence-hub.silver.samsara_cleaned_view` AS

-- Step 1: Get Clean, Unique Sensor Readings
-- We start with the raw sensor data. Since the source might have duplicates, we use QUALIFY to
-- grab only the most recently ingested version of each unique reading. This ensures our starting
-- point is clean and reliable.
WITH distinct_records AS (
  SELECT *
  FROM `agy-intelligence-hub.bronze.samsara_full`
  WHERE ambientTemperature IS NOT NULL -- We only care about records that actually have a temperature
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY trailerName, sensorId, sensorName, installedGateway, externalIds, enabledForMobile, notes, licensePlate, trailerSerialNumber, ambientTemperatureTime
    ORDER BY ingestedAt DESC
  ) = 1
),

-- Step 2: Process the Sensor Data
-- Here, we clean up the sensor data. We convert the temperature from milli-Celsius to Fahrenheit,
-- parse the text-based timestamp into a proper TIMESTAMP, and extract useful bits from JSON fields.
-- We also add empty placeholder columns (like driverSetPoint) that we'll fill in later.
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
    -- These are the columns we want to fill. We define them as NULLs for now.
    null AS driverSetPoint,
    null AS driverSetPointInF,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    CAST(null AS STRING) AS actualReeferRunMode,
    CAST(null AS TIMESTAMP) AS actualReeferRunModeTime,
    -- This is our master timestamp for ordering all events chronologically.
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', ambientTemperatureTime) AS time_axis
  FROM distinct_records
),

-- Step 3: Isolate Reefer Run Mode Events
-- Now, we create a separate, clean list of just the reefer run mode changes. We structure this
-- data to have the exact same columns as our processed sensor data above. This way, we can
-- easily stack them together in the next step.
reefer_modes AS (
  SELECT DISTINCT
    -- All columns that don't apply to this event type are set to NULL.
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
    null AS driverSetPoint,
    null AS driverSetPointInF,
    CAST(null AS TIMESTAMP) AS driverSetPointTime,
    -- This is the actual data point for this event.
    reeferRunModeValue AS actualReeferRunMode,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferRunModeTime) AS actualReeferRunModeTime,
    -- The event's own timestamp is used for the master time_axis.
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferRunModeTime) AS time_axis
  FROM `bronze.samsara_trailer_stats`
),

-- Step 4: Isolate Reefer Setpoint Events
-- We do the same thing for setpoint changes, creating another clean list of events that matches
-- the same column structure.
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
    -- This is the actual data point for this event.
    reeferSetPointTemperatureMilliCZone1Value AS driverSetPoint,
    ROUND(((reeferSetPointTemperatureMilliCZone1Value / 1000))*(9/5) + 32, 0) AS driverSetPointInF,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferSetPointTemperatureMilliCZone1Time) AS driverSetPointTime,
    CAST(null AS STRING) AS actualReeferRunMode,
    CAST(null AS TIMESTAMP) AS actualReeferRunModeTime,
    -- The event's own timestamp is used for the master time_axis.
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferSetPointTemperatureMilliCZone1Time) AS time_axis
  FROM `bronze.samsara_trailer_stats`
),

-- Step 5: Create a Single, Unified Timeline
-- This is where we combine everything. We stack the sensor readings, run mode changes, and
-- setpoint changes on top of each other. The result is one long list of every event that
-- happened, all ordered by our master `time_axis`.
unioned AS (
  SELECT * FROM samsara_processed
  WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM reefer_modes
  WHERE time_axis IS NOT NULL
  UNION ALL
  SELECT * FROM setpoints
  WHERE time_axis IS NOT NULL
),

-- Step 6: The Forward Fill
-- Here's the magic. We use the LAST_VALUE window function to fill in the NULLs we created earlier.
-- For each row, it looks backward in time (for that specific trailer) and finds the most recent
-- non-null value for the setpoint and run mode, effectively "carrying it forward."
final_merged AS (
  SELECT
    -- Select all columns except the temporary ones we used for filling.
    * EXCEPT(driverSetPoint, driverSetPointInF, driverSetPointTime, actualReeferRunMode, actualReeferRunModeTime, time_axis),
    -- The LAST_VALUE function does the heavy lifting of our forward fill.
    LAST_VALUE(driverSetPoint IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPoint,
    LAST_VALUE(driverSetPointInF IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPointInF,
    LAST_VALUE(driverSetPointTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS driverSetPointTime,
    LAST_VALUE(actualReeferRunMode IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferRunMode,
    LAST_VALUE(actualReeferRunModeTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY time_axis) AS actualReeferRunModeTime
  FROM unioned
)

-- Final Step: Return Only the Enriched Sensor Readings
-- Our work is done! The `final_merged` table contains the complete, filled timeline. All we
-- need to do now is filter it to return only the original sensor reading rows, which now
-- contain the correct, last-known reefer status.
SELECT * FROM final_merged
WHERE ambientTemperatureInF IS NOT NULL;