CREATE OR REPLACE VIEW `agy-intelligence-hub.golden.ditat_sub-trip_level_time_and_temp`
AS WITH ditat_by_trip AS (
  SELECT
    DISTINCT
    d.primaryTrailerId AS trailer_id,
    d.tripId AS trip_id,
    d.primaryDriverId AS driver_id,
    d.truckId AS truck_id,
    d.internalOrderedStatus AS status_id, -- internally assigned
    d.actualReeferUpdatedOn AS temp_updated_on,
    COALESCE(
      LEAD(d.actualReeferUpdatedOn, 1) OVER (
        PARTITION BY d.primaryTrailerId, d.tripId, d.primaryDriverId, d.truckId 
        ORDER BY d.actualReeferUpdatedOn
      ),
      DATETIME_ADD(d.actualReeferUpdatedOn, INTERVAL 1 MINUTE)
    ) AS next_temp_updated_on,
    MIN(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.primaryDriverId, d.truckId
      ORDER BY d.actualReeferUpdatedOn
      ROWS UNBOUNDED PRECEDING
    ) AS trip_start_time,
    MAX(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.primaryDriverId, d.truckId
      ORDER BY d.actualReeferUpdatedOn
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS trip_end_time,
    -- the sub_trip_[start|end]_time groups on the status level for a trip
    MIN(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.primaryDriverId, d.truckId, d.statusMessage
      ORDER BY d.actualReeferUpdatedOn
      ROWS UNBOUNDED PRECEDING
    ) AS sub_trip_start_time,
    MAX(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.primaryDriverId, d.truckId, d.statusMessage
      ORDER BY d.actualReeferUpdatedOn
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS sub_trip_end_time,
    d.statusMessage AS status,
    d.priorityMessage AS priority,
    d.priority AS priority_id,
    d.reeferMode AS reefer_mode_id,
    d.reeferModeMessage AS reefer_mode,
    d.MaxTempDeviationAllowedInF AS max_allowed_deviation,
    d.reeferTemperatureInF AS required_temp,
    d.actualReeferSetTemperatureInF AS driver_set_temp,
    d.actualReeferReturnTemperatureInF AS actual_temp,
    d.ingestedAt AS ingestion_time
  FROM
    `agy-intelligence-hub.silver.ditat_cleaned_view` d
  WHERE d.primaryTrailerId IS NOT NULL AND d.primaryTrailerId != ""
  ORDER BY 1, 2, 3, 4, 5, 6
)
SELECT 
  *
FROM 
  ditat_by_trip
WHERE 
  -- This ensures we only take those entries where there is a change in temperature
  ditat_by_trip.temp_updated_on != ditat_by_trip.next_temp_updated_on
