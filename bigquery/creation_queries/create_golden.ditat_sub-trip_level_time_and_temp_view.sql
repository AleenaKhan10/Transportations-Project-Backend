WITH ditat_by_trip AS (
  SELECT
    DISTINCT
    d.tripId AS trip_id,
    d.primaryTrailerId AS trailer_id,
    d.legId as leg_id,
    d.primaryDriverId AS driver_id,
    d.truckId AS truck_id,
    d.internalOrderedStatus AS status_id, -- internally assigned
    d.actualReeferUpdatedOn AS temp_updated_on,
    COALESCE(
      LEAD(d.actualReeferUpdatedOn, 1) OVER (
        PARTITION BY d.primaryTrailerId, d.tripId 
        ORDER BY d.actualReeferUpdatedOn
      ),
      DATETIME_ADD(d.actualReeferUpdatedOn, INTERVAL 1 MINUTE)
    ) AS next_temp_updated_on,
    MIN(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId
      ORDER BY d.actualReeferUpdatedOn
      ROWS UNBOUNDED PRECEDING
    ) AS trip_start_time,
    MAX(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId
      ORDER BY d.actualReeferUpdatedOn
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS trip_end_time,
    -- the leg_[start|end]_time groups on the leg level of a trip
    MIN(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.legId
      ORDER BY d.actualReeferUpdatedOn
      ROWS UNBOUNDED PRECEDING
    ) AS leg_start_time,
    MAX(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.legId
      ORDER BY d.actualReeferUpdatedOn
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS leg_end_time,
    -- the sub_leg_[start|end]_time groups on the status level for a leg of a trip
    MIN(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.legId, d.statusMessage
      ORDER BY d.actualReeferUpdatedOn
      ROWS UNBOUNDED PRECEDING
    ) AS sub_leg_start_time,
    MAX(d.actualReeferUpdatedOn) OVER (
      PARTITION BY d.primaryTrailerId, d.tripId, d.legId, d.statusMessage
      ORDER BY d.actualReeferUpdatedOn
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS sub_leg_end_time,
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
  ORDER BY 1, 2, 3, 4, 5, 6, 7
)
SELECT 
  *
FROM 
  ditat_by_trip
WHERE 
  ditat_by_trip.temp_updated_on != ditat_by_trip.next_temp_updated_on -- This ensures we only take those entries where there is a change
