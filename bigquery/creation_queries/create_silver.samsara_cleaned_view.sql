CREATE VIEW `agy-intelligence-hub.silver.samsara_cleaned_view`
AS SELECT
  sensorId,
  sensorName,
  ambientTemperature, # This is in milli-degrees centigrade
  ROUND(((ambientTemperature / 1000))*(9/5) + 32, 2) AS ambientTemperatureInF,
  PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', ambientTemperatureTime) AS ambientTemperatureTime,
  vehicleId,
  SAFE.PARSE_JSON(tags) AS tags,
  SAFE.PARSE_JSON(installedGateway) AS installedGateway,
  trailerId,
  trailerName,
  PARSE_JSON(externalIds) AS externalIds,
  enabledForMobile,
  notes,
  licensePlate,
  ingestedAt,
  trailerSerialNumber
FROM `agy-intelligence-hub.bronze.samsara_full`
;