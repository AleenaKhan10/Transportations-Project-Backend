-- Ditat full
INSERT INTO `agy-intelligence-hub.archive.ditat_full`
SELECT *
FROM `agy-intelligence-hub.bronze.ditat_full`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);

-- Delete old data from active table
DELETE FROM `agy-intelligence-hub.bronze.ditat_full`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
 
 
-- Samsara Detailed Location Archive
INSERT INTO `agy-intelligence-hub.archive.samsara_detailed_locations`
SELECT *
FROM `agy-intelligence-hub.bronze.samsara_detailed_locations`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
-- Delete old data from active table
DELETE FROM `agy-intelligence-hub.bronze.samsara_detailed_locations`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
 
 
-- Samsara Detailed Trailer Stats Archive
INSERT INTO `agy-intelligence-hub.archive.samsara_detailed_trailer_stats`
SELECT *
FROM `agy-intelligence-hub.bronze.samsara_detailed_trailer_stats`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
-- Delete old data from active table
DELETE FROM `agy-intelligence-hub.bronze.samsara_detailed_trailer_stats`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
 
 
-- Samsara Full Archive
INSERT INTO `agy-intelligence-hub.archive.samsara_full`
SELECT *
FROM `agy-intelligence-hub.bronze.samsara_full`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
-- Delete old data from active table
DELETE FROM `agy-intelligence-hub.bronze.samsara_full`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
 
 
-- Samsara Trailer Stats Archive
INSERT INTO `agy-intelligence-hub.archive.samsara_trailer_stats`
SELECT *
FROM `agy-intelligence-hub.bronze.samsara_trailer_stats`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);
 
-- Delete old data from active table
DELETE FROM `agy-intelligence-hub.bronze.samsara_trailer_stats`
WHERE ingestedAt < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);