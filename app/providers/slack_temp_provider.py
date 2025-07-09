from datetime import datetime
import pytz
import requests
import pandas_gbq as pd
from config import settings

SLACK_BOT_TOKEN = settings.SLACK_BOT_TOKEN
SLACK_CHANNEL = settings.SLACK_CHANNEL


common_ranking_cte = """
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY samsara_temp_time DESC) AS rn
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
"""

common_fields = """
  trailer_id, 
  trip_id, 
  leg_id, 
  truck_id, 
  status, 
  priority_id, 
  max_allowed_deviation, 
  required_temp, 
  driver_set_temp, 
  samsara_temp, 
  DATETIME(samsara_temp_time, 'America/Chicago') AS samsara_temp_time"""

query_99 = f"""
{common_ranking_cte}
  WHERE required_temp = 99
)
SELECT 
  {common_fields}
FROM ranked
WHERE 
  rn = 1 
  AND reefer_mode_id != 0
  AND samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
  -- AND CONCAT(leg_id, status_id) NOT IN ("10", "11") -- this filter is not required
ORDER BY samsara_temp_time DESC
"""

query_setpoint = f"""
{common_ranking_cte}
  WHERE 
    required_temp != 99
    AND required_temp IS NOT NULL
    AND driver_set_temp IS NOT NULL
    AND (required_temp - driver_set_temp) != 0
    AND samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
)
SELECT 
  {common_fields}
FROM ranked
WHERE 
  rn = 1 
  AND reefer_mode_id != 0
  AND CONCAT(leg_id, status_id) NOT IN ("10", "11")
ORDER BY samsara_temp_time DESC
LIMIT 5
"""

query_anomalies = f"""
{common_ranking_cte}
  WHERE
    samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
    AND CONCAT(leg_id, status_id) NOT IN ("10", "11")
    AND reefer_mode_id != 0
    AND required_temp = driver_set_temp
)
SELECT 
  {common_fields},
  ABS(ROUND(required_temp - samsara_temp, 3)) AS temp_diff
FROM ranked 
WHERE 
  rn = 1
  AND abs(samsara_temp-required_temp) > max_allowed_deviation
  -- considering the status after unloading as we cannot determine the last leg.
ORDER BY samsara_temp_time DESC
"""



cfgs = [
    {
        "title": "⚠️ Driver Setpoint Mismatch",
        "query": query_setpoint,
        "template": (
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            "> *Required Temp:* `{required_temp}`\n"
            "> *Driver Set:* `{driver_set_temp}`\n"
            "> *Samsara Temp:* `{samsara_temp}`\n"
            "> *Captured At* `{samsara_temp_time}`"
        )
    },
    {
        "title": "🔥 99°F Required Temp",
        "query": query_99,
        "template": (
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            "> *Required Temp:* `{required_temp}`\n"
            "> *Driver Set:* `{driver_set_temp}`\n"
            "> *Samsara Temp:* `{samsara_temp}`\n"
            "> *Captured At* `{samsara_temp_time}`"
        )
    },
    {
        "title": "🚨 Temperature Out of Range",
        "query": query_anomalies,
        "template": (
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            "> *Required Temp:* `{required_temp}`\n"
            "> *Driver Set:* `{driver_set_temp}`\n"
            "> *Samsara Temp:* `{samsara_temp}`\n"
            "> *Captured At* `{samsara_temp_time}`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}`/`{max_allowed_deviation}`"
        )
    },
]


def send_slack_temp_alerts():
    blocks = []
    chicago_tz = pytz.timezone("America/Chicago")
    dt_format_str = "%b %d, %Y at %I:%M %p %Z"
    
    for cfg in cfgs:
        df = pd.read_gbq(cfg["query"], progress_bar_type=None)
        if not df.empty:
            # Format the datetime column to be more readable
            # The DATETIME from BigQuery is naive, so we make it timezone-aware before formatting.
            df['samsara_temp_time'] = df['samsara_temp_time'].dt.tz_localize(chicago_tz).dt.strftime(dt_format_str)
            
            blocks.append({"type": "header", "text": {"type": "plain_text", "text": cfg["title"], "emoji": True}})
            for _, row in df.iterrows():
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": cfg["template"].format(**row)}})
            blocks.append({"type": "divider"})

    if not blocks:
        return {"message": "No alerts to send today.", "slack_status": 200}

    # Add a human-readable timestamp to the message
    current_time = datetime.now(chicago_tz).strftime(dt_format_str)
    blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Alerts generated at: {current_time}"}]})


    payload = {
        "channel": SLACK_CHANNEL,
        "blocks": blocks,
        "text": "Temperature Alerts" # Fallback text for notifications
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    slack_response = requests.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)

    return {"message": slack_response.text, "slack_status": slack_response.status_code}