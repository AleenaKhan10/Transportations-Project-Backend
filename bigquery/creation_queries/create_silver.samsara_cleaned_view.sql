CREATE OR REPLACE VIEW `agy-intelligence-hub.silver.samsara_cleaned_view` AS 
-- =================================================================================================
-- Samsara Merged Reefer Status Query
-- Purpose: This query enriches Samsara sensor temperature readings with the most relevant reefer
--          (refrigerated trailer) status at that specific time. It produces a clean, denormalized
--          table where each temperature reading is paired with its corresponding reefer run mode
--          and temperature setpoint.
-- =================================================================================================

-- Step 1: Deduplicate Raw Sensor Data
-- We begin by ensuring data integrity. The source table might contain duplicate records for the
-- same event. This CTE uses the QUALIFY clause to efficiently select only the most recently
-- ingested version of each unique sensor reading, creating a clean, reliable starting point.
WITH distinct_records AS (
  SELECT *
  FROM `agy-intelligence-hub.bronze.samsara_full`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY trailerName, sensorId, sensorName, installedGateway, externalIds, enabledForMobile, notes, licensePlate, trailerSerialNumber, ambientTemperatureTime
    ORDER BY ingestedAt DESC
  ) = 1
),

-- Step 2: Process and Standardize Sensor Data
-- This CTE transforms the raw, deduplicated data into a more usable format. It handles key
-- data cleaning tasks: converting temperature to Fahrenheit, parsing string-based timestamps
-- into a proper TIMESTAMP type, and safely parsing embedded JSON strings into queryable objects.
samsara_processed AS (
  SELECT
    sensorId,
    sensorName,
    ambientTemperature, -- Original value in milli-degrees Celsius
    ROUND(((ambientTemperature / 1000))*(9/5) + 32, 2) AS ambientTemperatureInF,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', ambientTemperatureTime) AS ambientTemperatureTime,
    vehicleId,
    trailerId,
    trailerName,
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
    trailerSerialNumber
  FROM distinct_records
),

-- Step 3: Isolate Reefer Run Modes and Setpoints
-- To prepare for the join, we create two separate, clean lookup tables from the trailer stats data.
-- Using DISTINCT ensures we have a unique list of run modes and setpoint values along with their
-- exact timestamps, which is crucial for the time-based matching logic later.
reefer_modes AS (
  SELECT DISTINCT
    name,
    reeferRunModeValue AS reeferRunMode,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferRunModeTime) AS reeferRunModeTime
  FROM `bronze.samsara_trailer_stats`
),
setpoints AS (
  SELECT DISTINCT
    name,
    reeferSetPointTemperatureMilliCZone1Value AS reeferSetPoint,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', reeferSetPointTemperatureMilliCZone1Time) AS reeferSetPointTime
  FROM `bronze.samsara_trailer_stats`
),

-- Step 4: Join Sensor Data with the Closest Reefer Status
-- This is the core of the query. It joins the sensor readings with the reefer data and uses QUALIFY
-- to perform a "nearest neighbor" search in time.
--
-- How it works:
-- 1. LEFT JOIN: We join reefer data that falls within a +/- 30-minute window of each sensor reading.
--    The LEFT JOIN is critical because it keeps all sensor readings, even if no reefer data exists
--    in that window (in which case the reefer columns will be NULL).
-- 2. QUALIFY: This clause elegantly filters the joined results. It ranks all potential matches from
--    the time window by how close their timestamp is to the sensor's timestamp. By specifying `= 1`
--    for both the setpoint and run mode rankings, we select only the single, definitive row that
--    represents the absolute closest match for both, resulting in a perfectly unified record.
merged AS (
  SELECT
    sp.*,
    st.reeferSetPoint,
    ROUND(((st.reeferSetPoint / 1000))*(9/5) + 32, 2) AS reeferSetPointInF,
    st.reeferSetPointTime,
    rm.reeferRunMode,
    rm.reeferRunModeTime
  FROM samsara_processed sp
  LEFT JOIN setpoints st
    ON sp.trailerName = st.name
    AND st.reeferSetPointTime
      BETWEEN DATETIME_SUB(sp.ambientTemperatureTime, INTERVAL 30 MINUTE)
      AND DATETIME_ADD(sp.ambientTemperatureTime, INTERVAL 30 MINUTE)
  LEFT JOIN reefer_modes rm
    ON sp.trailerName = rm.name
    AND rm.reeferRunModeTime
      BETWEEN DATETIME_SUB(sp.ambientTemperatureTime, INTERVAL 30 MINUTE)
      AND DATETIME_ADD(sp.ambientTemperatureTime, INTERVAL 30 MINUTE)
  QUALIFY
    ROW_NUMBER() OVER (PARTITION BY sp.trailerName, sp.ambientTemperatureTime ORDER BY ABS(DATETIME_DIFF(st.reeferSetPointTime, sp.ambientTemperatureTime, SECOND))) = 1
    AND
    ROW_NUMBER() OVER (PARTITION BY sp.trailerName, sp.ambientTemperatureTime ORDER BY ABS(DATETIME_DIFF(rm.reeferRunModeTime, sp.ambientTemperatureTime, SECOND))) = 1
  ORDER BY trailerName, ambientTemperatureTime
),

-- Final Step: Forward Fill the Gaps
-- This is the new logic. We take the results from the initial merge (which includes NULLs)
-- and apply the LAST_VALUE window function to fill them.
-- How it works:
--   - LAST_VALUE(...): This function retrieves a value from a previous row.
--   - IGNORE NULLS: This crucial option tells the function to skip over any NULLs and find the most recent non-NULL value.
--   - OVER(...): This defines the "window" for the function.
--     - PARTITION BY trailerName: Ensures we only fill values from the same trailer.
--     - ORDER BY ambientTemperatureTime: Arranges the data chronologically, so we are always filling "forward".
--     - ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW: A standard frame for this operation, ensuring it looks at all previous rows.
final AS (
  SELECT
    * EXCEPT (reeferSetPoint, reeferSetPointInF, reeferSetPointTime, reeferRunMode, reeferRunModeTime),
    LAST_VALUE(reeferSetPoint IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY ambientTemperatureTime ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS driverSetPoint,
    LAST_VALUE(reeferSetPointInF IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY ambientTemperatureTime ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS driverSetPointInF,
    LAST_VALUE(reeferSetPointTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY ambientTemperatureTime ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS driverSetPointTime,
    LAST_VALUE(reeferRunMode IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY ambientTemperatureTime ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS actualReeferMode,
    LAST_VALUE(reeferRunModeTime IGNORE NULLS) OVER (PARTITION BY trailerName ORDER BY ambientTemperatureTime ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS actualReeferModeTime
  FROM merged
  WHERE ambientTemperatureInF is not null
)
SELECT
 *
FROM final
