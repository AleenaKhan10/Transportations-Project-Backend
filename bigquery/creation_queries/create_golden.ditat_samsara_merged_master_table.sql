/**********************************************************************************************************************
*
*  Description:
*      This query creates a master table named `ditat_samsara_merged_master` by merging and enriching telematics data
*      from two distinct sources: Ditat and Samsara. The primary goal is to create a unified timeline of events
*      for each trailer, forward-filling missing data points to provide a complete and contextualized view of
*      each trip. This allows for comprehensive analysis of trailer conditions, such as temperature and reefer mode,
*      throughout a journey.
*
*  Input Tables:
*      - `agy-intelligence-hub.golden.ditat_grouped_subtrip_level`: This table contains trip and reefer data from the Ditat system,
*        including information about trips, legs, drivers, and temperature readings.
*      - `silver.samsara_cleaned_view`: This table contains telematics data from Samsara devices, including reefer mode,
*        set points, and ambient temperature readings.
*
*  Output Table:
*      - `agy-intelligence-hub.golden.ditat_samsara_merged_master`: A new table containing the merged and enriched
*        timeline of trailer events.
*
*  Methodology:
*      1. **Identify Trip Starts**: The query first identifies the start of new trips in the Ditat data by using the `LAG`
*         window function to detect changes in the `trip_id` for each trailer.
*      2. **Prepare Samsara Events**: It selects and renames relevant columns from the Samsara data to align with the
*         Ditat data structure.
*      3. **Unify Timelines**: The Ditat and Samsara event data are combined into a single chronological stream using a
*         `UNION ALL` operation. Placeholder `NULL` columns are added to each dataset to ensure a consistent schema.
*      4. **Forward Fill Data**: To create a complete picture, the query uses the `LAST_VALUE` window function with
*         `IGNORE NULLS` to forward-fill missing values for various attributes (e.g., `trip_id`, `driver_id`, `required_temp`).
*         This ensures that each event in the timeline has the most recent known context.
*      5. **Filter for In-Trip Events**: The final step filters the enriched timeline to include only Samsara events that
*         occurred within the start and end times of a Ditat-defined trip. This removes extraneous data and focuses the
*         analysis on relevant periods.
*
*  Key Columns in Output:
*      - `trailer_id`: The unique identifier for the trailer.
*      - `trip_id`: The unique identifier for a trip.
*      - `time_axis`: The master timestamp for the unified event timeline.
*      - `ditat_temp`: Temperature readings from the Ditat system.
*      - `samsara_temp`: Temperature readings from the Samsara system.
*      - `required_temp`: The required temperature for the cargo.
*      - `reefer_mode`: The operational mode of the refrigeration unit.
*
**********************************************************************************************************************/

CREATE TABLE IF NOT EXISTS `agy-intelligence-hub.golden.ditat_samsara_merged_master` AS
WITH ditat_events_with_trip_starts AS (
  -- Step 1: Identify Trip Starts in Ditat Data
  -- This CTE enhances the Ditat event data by adding a flag to identify the first event of each new trip for a trailer.
  SELECT
    *,
    -- The LAG function looks at the previous row for the same trailer (partitioned by trailer_id and ordered by time).
    -- If the trip_id of the current row is different from the previous one, it marks the current row as a new trip start.
    CASE
      WHEN trip_id != LAG(trip_id, 1, 'N/A') OVER (PARTITION BY trailer_id ORDER BY temp_updated_on)
      THEN 1
      ELSE 0
    END AS is_new_trip_start
  FROM `agy-intelligence-hub.golden.ditat_grouped_subtrip_level`
),

-- Step 2: Prepare Samsara Events
-- This CTE selects and renames columns from the Samsara data to prepare it for merging with the Ditat data.
samsara_events AS (
  SELECT
    trailerName AS trailer_id,
    actualReeferMode AS samsara_reefer_mode,
    actualReeferModeTime AS samsara_reefer_mode_time,
    driverSetPointInF AS samsara_driver_set_point,
    driverSetPointTime AS samsara_driver_set_point_time,
    ambientTemperatureInF AS samsara_temp,
    ambientTemperatureTime AS samsara_temp_time,
    ambientTemperatureTime AS time_axis -- This timestamp will be used to order events in the unified timeline.
  FROM `silver.samsara_cleaned_view`
),

-- Step 3: Create a Unified Timeline of All Events
-- This CTE combines the Ditat and Samsara event data into a single, chronologically ordered stream.
-- Placeholder NULL columns are used to ensure both datasets have the same structure before the union.
unioned_events AS (
  -- Select all Ditat events and create null placeholders for Samsara-specific columns.
  SELECT
    trailer_id,
    trip_id,
    leg_id,
    driver_id,
    truck_id,
    status_id,
    status,
    priority_id,
    priority,
    reefer_mode_id,
    reefer_mode,
    required_reefer_mode_id,
    required_reefer_mode,
    max_allowed_deviation,
    required_temp,
    driver_set_temp,
    actual_temp AS ditat_temp,
    temp_updated_on AS ditat_temp_time,
    is_new_trip_start,
    temp_updated_on AS time_axis, -- Use Ditat's timestamp for the master timeline.
    CAST(NULL AS STRING) AS samsara_reefer_mode,
    CAST(NULL AS TIMESTAMP) AS samsara_reefer_mode_time,
    CAST(NULL AS FLOAT64) AS samsara_driver_set_point,
    CAST(NULL AS TIMESTAMP) AS samsara_driver_set_point_time,
    CAST(NULL AS FLOAT64) AS samsara_temp,
    CAST(NULL AS TIMESTAMP) AS samsara_temp_time,
    trip_start_time,
    trip_end_time,
    leg_start_time,
    leg_end_time,
    sub_leg_start_time,
    sub_leg_end_time
  FROM ditat_events_with_trip_starts

  UNION ALL

  -- Select all Samsara events and create null placeholders for Ditat-specific columns.
  SELECT
    trailer_id,
    CAST(NULL AS STRING) AS trip_id,
    CAST(NULL AS INT64) AS leg_id,
    CAST(NULL AS STRING) AS driver_id,
    CAST(NULL AS STRING) AS truck_id,
    CAST(NULL AS INT64) AS status_id,
    CAST(NULL AS STRING) AS status,
    CAST(NULL AS INT64) AS priority_id,
    CAST(NULL AS STRING) AS priority,
    CAST(NULL AS INT64) AS reefer_mode_id,
    CAST(NULL AS STRING) AS reefer_mode,
    CAST(NULL AS INT64) AS required_reefer_mode_id,
    CAST(NULL AS STRING) AS required_reefer_mode,
    CAST(NULL AS INT64) AS max_allowed_deviation,
    CAST(NULL AS FLOAT64) AS required_temp,
    CAST(NULL AS FLOAT64) AS driver_set_temp,
    CAST(NULL AS FLOAT64) AS ditat_temp,
    CAST(NULL AS TIMESTAMP) AS ditat_temp_time,
    0 AS is_new_trip_start, -- A Samsara event cannot be the start of a trip as this information comes from Ditat.
    time_axis, -- Use Samsara's timestamp for the master timeline.
    samsara_reefer_mode,
    samsara_reefer_mode_time,
    samsara_driver_set_point,
    samsara_driver_set_point_time,
    samsara_temp,
    samsara_temp_time,
    CAST(NULL AS TIMESTAMP) AS trip_start_time,
    CAST(NULL AS TIMESTAMP) AS trip_end_time,
    CAST(NULL AS TIMESTAMP) AS leg_start_time,
    CAST(NULL AS TIMESTAMP) AS leg_end_time,
    CAST(NULL AS TIMESTAMP) AS sub_leg_start_time,
    CAST(NULL AS TIMESTAMP) AS sub_leg_end_time
  FROM samsara_events
),

-- Step 4: Forward Fill Data
-- This CTE fills in the NULL values in the unified timeline by carrying forward the last known non-null value for each attribute.
-- This is crucial for associating Samsara events with the correct Ditat trip context.
final_enriched_timeline AS (
  SELECT
    -- The LAST_VALUE function with IGNORE NULLS carries forward the last non-null value for each column,
    -- partitioned by trailer_id and ordered by the master time_axis.
    LAST_VALUE(trailer_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS trailer_id,
    LAST_VALUE(trip_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS trip_id,
    LAST_VALUE(leg_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS leg_id,
    LAST_VALUE(driver_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS driver_id,
    LAST_VALUE(truck_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS truck_id,
    LAST_VALUE(status_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS status_id,
    LAST_VALUE(status IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS status,
    LAST_VALUE(priority_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS priority_id,
    LAST_VALUE(priority IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS priority,
    LAST_VALUE(reefer_mode_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS reefer_mode_id,
    LAST_VALUE(reefer_mode IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS reefer_mode,
    LAST_VALUE(required_reefer_mode_id IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS required_reefer_mode_id,
    LAST_VALUE(required_reefer_mode IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS required_reefer_mode,
    LAST_VALUE(max_allowed_deviation IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS max_allowed_deviation,
    LAST_VALUE(required_temp IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS required_temp,
    LAST_VALUE(driver_set_temp IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS driver_set_temp,
    LAST_VALUE(ditat_temp IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS ditat_temp,
    LAST_VALUE(ditat_temp_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS ditat_temp_time,
    samsara_temp,
    samsara_temp_time,
    -- NOTE: These 4 fields can be turned on once the backward compatible conditions are no longer required
    -- samsara_reefer_mode,
    -- samsara_reefer_mode_time,
    -- samsara_driver_set_point,
    -- samsara_driver_set_point_time,
    -- NOTE: These 4 conditions are kept for backward compatibility. Once, the need is over, these can be removed.
    CASE 
      WHEN samsara_reefer_mode IS NULL THEN 'Dry Load'
      ELSE samsara_reefer_mode
      END AS samsara_reefer_mode,
    CASE 
      WHEN samsara_reefer_mode_time IS NULL THEN samsara_temp_time
      ELSE samsara_reefer_mode_time
      END AS samsara_reefer_mode_time,
    CASE 
      WHEN samsara_driver_set_point IS NULL THEN 99
      ELSE samsara_driver_set_point
      END AS samsara_driver_set_point,
    CASE 
      WHEN samsara_driver_set_point_time IS NULL THEN samsara_temp_time
      ELSE samsara_driver_set_point_time
      END AS samsara_driver_set_point_time,
    LAST_VALUE(trip_start_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS trip_start_time,
    LAST_VALUE(trip_end_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS trip_end_time,
    LAST_VALUE(leg_start_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS leg_start_time,
    LAST_VALUE(leg_end_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS leg_end_time,
    LAST_VALUE(sub_leg_start_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS sub_leg_start_time,
    LAST_VALUE(sub_leg_end_time IGNORE NULLS) OVER (PARTITION BY trailer_id ORDER BY time_axis) AS sub_leg_end_time,
    CASE 
      WHEN samsara_temp IS NULL THEN NULL
      -- If we have actual reefer mode from Samsara, use it
      -- NOTE: If we need to see how accurate the calculation is, we can comment out the next two lines
      WHEN samsara_reefer_mode IS NOT NULL 
        AND UPPER(samsara_reefer_mode) IN ('CONTINUOUS', 'START/STOP') THEN 'ON'
      -- Temperature is within acceptable range of target
      WHEN required_temp IS NOT NULL 
        AND ABS(samsara_temp - required_temp) <= COALESCE(max_allowed_deviation, 2) THEN 'ON'
      -- First row in partition, no prior temp to compare -> mark as 'UNKNOWN'
      WHEN LAG(samsara_temp, 1) OVER (
        PARTITION BY trailer_id, trip_id, leg_id, status_id 
        ORDER BY time_axis
      ) IS NULL THEN 'UNKNOWN'
      -- Current reading shows activity
      WHEN ABS(samsara_temp - LAG(samsara_temp, 1) OVER (
        PARTITION BY trailer_id, trip_id, leg_id, status_id 
        ORDER BY time_axis
      )) >= 0.5 THEN 'ON'
      -- No current activity, but check if 2 of last 4 readings showed activity
      WHEN (
        CASE WHEN ABS(
          LAG(samsara_temp, 1) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis) - 
          LAG(samsara_temp, 2) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis)
        ) >= 0.005 THEN 1 ELSE 0 END +
        CASE WHEN ABS(
          LAG(samsara_temp, 2) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis) - 
          LAG(samsara_temp, 3) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis)
        ) >= 0.005 THEN 1 ELSE 0 END +
        CASE WHEN ABS(
          LAG(samsara_temp, 3) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis) - 
          LAG(samsara_temp, 4) OVER (PARTITION BY trailer_id, trip_id, leg_id, status_id ORDER BY time_axis)
        ) >= 0.005 THEN 1 ELSE 0 END
      ) >= 2 THEN 'ON'
      ELSE 'OFF'
    END AS derived_reefer_status
  FROM unioned_events
)

-- Final Step: Present the Complete, Cleaned Timeline with Trip Level Information
-- This final SELECT statement filters the enriched timeline to only include Samsara temperature events
-- that fall within the start and end times of a trip. This ensures that the final table only contains relevant data.
SELECT 
  *  
FROM final_enriched_timeline
WHERE
  samsara_temp_time BETWEEN trip_start_time AND trip_end_time
