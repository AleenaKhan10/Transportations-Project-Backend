CREATE OR REPLACE VIEW `agy-intelligence-hub.silver.ditat_cleaned_view` AS
select 
  CONCAT(SPLIT(tripId, "-")[0], "-", SPLIT(tripId, "-")[1]) AS tripId,
  CAST(SPLIT(tripId, "-")[2] AS INT) AS legId,
  primaryDriverId,
  truckId,
  REGEXP_REPLACE(UPPER(primaryTrailerId), "[^A-Z0-9]+", "") AS primaryTrailerId,
  priority,
  CASE
    WHEN priority = 0 THEN "VeryLow"
    WHEN priority = 1 THEN "Low"
    WHEN priority = 2 THEN "Medium"
    WHEN priority = 3 THEN "High"
    WHEN priority = 4 THEN "Critical"
    ELSE "Unknown"
  END AS priorityMessage,
  status,
  subStatus,
  CASE
    WHEN status = 2 THEN 'LoadNotAssigned'
    WHEN status = 3 THEN
      CASE
        WHEN subStatus = 1 THEN 'EnrouteToPickUp'
        WHEN subStatus = 2 THEN 'Loading'
        WHEN subStatus in (3, 5) THEN 'EnrouteToDelivery' -- For now, we need to only use this status for temp alerts
        WHEN subStatus = 4 THEN 'Unloading'
        ELSE 'InTransit'
      END
    ELSE 'Unknown' -- Catch any other status values not explicitly handled
  END AS statusMessage,
  -- internalOrderedStatus is just a chronological sequence for the statuses of a trip
  CASE
    WHEN status = 2 THEN 0
    WHEN status = 3 THEN
      CASE
        WHEN subStatus = 1 THEN 1
        WHEN subStatus = 2 THEN 2
        WHEN subStatus in (3, 5) THEN 3 -- For now, we need to only use this status for temp alerts
        WHEN subStatus = 4 THEN 4
        ELSE 6
      END
    ELSE 9 -- Catch any other status values not explicitly handled
  END AS internalOrderedStatus,
  actualReeferMode,
  CASE
    WHEN actualReeferMode = 0 THEN "Off"
    WHEN actualReeferMode = 1 THEN "Stop&Run" -- Stopped & Will Turn On if absoulte difference between actualReeferTemp And Setpoint Greater Than 5F
    WHEN actualReeferMode = 2 THEN "On"
    ELSE "Unknown"
  END AS actualReeferModeMessage,
  reeferMode,
  CASE
    WHEN reeferMode = 0 THEN "Off"
    WHEN reeferMode = 1 THEN "Stop&Run" -- Stopped & Will Turn On if absoulte difference between ReeferTemp And Setpoint Greater Than 5F
    WHEN reeferMode = 2 THEN "On"
    ELSE "Unknown"
  END AS reeferModeMessage,
  reeferTemperature,
  actualReeferSetTemperature,
  actualReeferReturnTemperature,
  CASE
    WHEN priority = 0 THEN 10
    WHEN priority = 1 THEN 8
    WHEN priority = 2 THEN 6
    WHEN priority = 3 THEN 4
    WHEN priority = 4 THEN 2
  END AS MaxTempDeviationAllowedInF, -- This is the max absolute temp diff that is allowed beyond which alter will go
  reeferTemperature AS reeferTemperatureInF,
  actualReeferSetTemperature AS actualReeferSetTemperatureInF,
  actualReeferReturnTemperature AS actualReeferReturnTemperatureInF,
  PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', actualReeferUpdatedOn) AS actualReeferUpdatedOn,
  dispatchedByUserName,
  customerId,
  customerName,
  primaryShipmentId,
  emptyDrivingDistance,
  loadedDrivingDistance,
  extraStopCount,
  PARSE_JSON(fromAddress) AS fromAddress,
  PARSE_JSON(toAddress) AS toAddress,
  legDrivingDistance,
  PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', gpsPingOn) AS gpsPingOn,
  gpsPositionDescription,
  PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', etaLocalTime) AS etaLocalTime,
  etaRemainingLegDrivingDistanceFromGPS,
  etaRemainingLegAirDistanceFromGPS,
  etaRemainingLegDrivingDistance,
  gpsSpeed,
  unreadIncomingPrimaryDriverMessagesExists,
  fromLocationId,
  toLocationId,
  legToLocationId,
  truckIssues,
  primaryDriverIssues,
  primaryTrailerIssues,
  assignmentsStatus,
  assignmentsStatusInfo,
  isHazmat,
  isDeleted,
  ingestedAt
from `agy-intelligence-hub.bronze.ditat_full`
where 
  not isDeleted 
and 
  regexp_contains(primaryTrailerId, "[A-Z0-9]+")
