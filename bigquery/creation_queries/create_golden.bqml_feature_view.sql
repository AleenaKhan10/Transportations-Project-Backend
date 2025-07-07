-- BQML Feature View
-- This view prepares all the necessary features for the BQML model.
CREATE OR REPLACE VIEW `agy-intelligence-hub.golden.bqml_feature_view` AS
WITH feature_engineered_data AS (
  SELECT
    -- ===== Key Identifiers and Timestamps =====
    s.trailer_id,
    s.trip_id,

    -- Timestamps (Critical for time-series)
    s.samsara_temp_time,

    -- Create a stable, unique ID for each potential alert event
    TO_HEX(SHA256(CONCAT(s.trailer_id, CAST(s.samsara_temp_time AS STRING)))) AS alert_id,
    
    -- ===== Core Data for the Model =====
    s.samsara_temp,      -- The time-series data column we are analyzing
    s.required_temp,     -- A key feature for context
    s.driver_set_temp,   -- A key feature as well

    -- ===== Contextual Features from Source =====
    s.status,
    s.reefer_mode,       -- Equipment operating mode context
    s.truck_id,          -- Vehicle identifier
    s.driver_id,         -- Driver identifier
    s.priority,          -- Trip priority level
    s.max_allowed_deviation,

    -- ===== Engineered Features for Model Context =====
    
    -- Feature 1: Temperature Deviations from Requirement
    ABS(s.samsara_temp - s.required_temp) AS temp_deviation,
    ABS(s.samsara_temp - s.driver_set_temp) AS temp_deviation_from_driver_set,
    ABS(s.driver_set_temp - s.required_temp) AS setpoint_deviation_from_required,
    
    -- Feature 2: Trip Status Context. Is the trip in an active, temperature-sensitive state?
    CASE
      WHEN s.status IN ('EnrouteToDelivery', 'Loading', 'Unloading') THEN 1
      ELSE 0
    END AS is_active_trip,

    -- Feature 3: Time-based Features
    EXTRACT(HOUR FROM s.samsara_temp_time) AS hour_of_day,
    EXTRACT(DAYOFWEEK FROM s.samsara_temp_time) AS day_of_week,

    -- Feature 4: Temperature Trends - Using Both Approaches for Robustness
    -- Approach 1: LAG-based (more precise, specific point-in-time comparison)
    LAG(s.samsara_temp, 5) OVER (
      PARTITION BY s.trailer_id 
      ORDER BY s.samsara_temp_time
    ) AS prev_temp_5readings,
    
    -- Approach 2: Time-window average (more robust to missing data)
    AVG(s.samsara_temp) OVER (
      PARTITION BY s.trailer_id 
      ORDER BY UNIX_SECONDS(s.samsara_temp_time) 
      RANGE BETWEEN 600 PRECEDING AND 1 PRECEDING
    ) AS avg_temp_10min_window,
  
    -- Feature 5: Additional Trend Analysis
    -- Standard deviation of temperature over the last 10 minutes (volatility indicator)
    STDDEV(s.samsara_temp) OVER (
      PARTITION BY s.trailer_id 
      ORDER BY UNIX_SECONDS(s.samsara_temp_time) 
      RANGE BETWEEN 600 PRECEDING AND 1 PRECEDING
    ) AS temp_volatility_10min
  FROM
    `agy-intelligence-hub.golden.ditat_samsara_merged_master` s
  WHERE
    s.samsara_temp IS NOT NULL
    AND s.required_temp IS NOT NULL
    AND s.required_temp != 0 -- Exclude records where temp control is not required
    AND s.required_temp != 99 -- -- Exclude records with 99F as these require manual inspection
),
final_data AS (
  SELECT
    -- All base fields
    *,
    
    -- ===== Calculated Temperature Change Features =====
    -- Primary trend indicator: LAG-based change (more precise for immediate changes)
    (samsara_temp - prev_temp_5readings) AS temp_change_5readings,
    
    -- Secondary trend indicator: Time-window based change (more robust)
    (samsara_temp - avg_temp_10min_window) AS temp_change_vs_10min_avg,
    
    -- ===== Composite Features =====
    -- Deviation rate: How fast is the temperature moving away from target?
    CASE 
      WHEN prev_temp_5readings IS NOT NULL AND prev_temp_5readings != 0 THEN
        ((samsara_temp - prev_temp_5readings) / NULLIF(ABS(samsara_temp - required_temp), 0)) * 100
      ELSE NULL
    END AS deviation_acceleration_pct
  FROM
    feature_engineered_data
)
SELECT 
  -- Take only the distinct records to prevent the model from seeing the same data point multiple times, 
  -- which can bias the training.
  DISTINCT *
FROM
 final_data
