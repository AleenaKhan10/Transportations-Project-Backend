from datetime import datetime, timezone
from fastapi import HTTPException
import pytz
import requests
import pandas_gbq as pd
from config import settings
from models.alert_filter import AlertFilter, AlertFilterCreate, AlertFilterUpdate
from sqlmodel import select, Session
from db.database import engine


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
  priority, 
  max_allowed_deviation, 
  required_temp, 
  samsara_driver_set_point, 
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
  AND ((leg_id = 1 AND status_id = 3) OR (leg_id != 1 AND status_id != 0))
ORDER BY samsara_temp_time DESC
"""

query_setpoint = f"""
{common_ranking_cte}
  WHERE 
    required_temp != 99
    AND required_temp IS NOT NULL
    AND ((leg_id = 1 AND status_id = 3) OR (leg_id != 1 AND status_id != 0))
    AND samsara_driver_set_point IS NOT NULL
    AND (required_temp - samsara_driver_set_point) != 0
    AND samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
)
SELECT 
  {common_fields}
FROM ranked
WHERE 
  rn = 1 
  AND reefer_mode_id != 0
ORDER BY samsara_temp_time DESC
"""

query_anomalies = f"""
{common_ranking_cte}
  WHERE
    samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
    AND ((leg_id = 1 AND status_id = 3) OR (leg_id != 1 AND status_id != 0))
    AND reefer_mode_id != 0
    AND required_temp = samsara_driver_set_point
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

query_dryload = f""" 
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY trailer_id ORDER BY  samsara_reefer_mode_time DESC) AS rn
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
  WHERE
    samsara_reefer_mode_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
    )
  SELECT 
    trailer_id,
    trip_id,
    truck_id,
    leg_id,
    status_id,
    status,
    required_reefer_mode,
    samsara_reefer_mode,
    samsara_reefer_mode_time,
    CASE 
    WHEN samsara_reefer_mode != 'Dry Load' THEN 'Please Note Reefer is ON'
    ELSE 'All good' 
    END AS Note
  FROM ranked 
  WHERE rn = 1 
  AND required_reefer_mode_id = 0
  """

query_dryload_anomalies = """ 
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY trailer_id ORDER BY  samsara_reefer_mode_time DESC) AS rn
  FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
  WHERE
    samsara_reefer_mode_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
    AND ((leg_id = 1 AND status_id = 3) OR (leg_id != 1 AND status_id != 0))
    )
  SELECT 
    trailer_id,
    trip_id,
    truck_id,
    leg_id,
    status_id,
    status,
    priority_id,
    priority,
    max_allowed_deviation,
    ABS(ROUND(required_temp - samsara_temp, 3)) AS temp_diff,
    required_reefer_mode_id,
    required_reefer_mode,
    samsara_reefer_mode,
    samsara_reefer_mode_time
  FROM ranked 
  WHERE rn = 1 
  AND required_reefer_mode_id != 0
  AND samsara_reefer_mode = 'Dry Load' 

"""
common_template = (
    "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}` | *Leg*: `{leg_id}` | *status:* `{status}`\n"
    "> *Required Temp:* `{required_temp}`\n"
    "> *Driver Set:* `{samsara_driver_set_point}`\n"
    "> *Samsara Temp:* `{samsara_temp}`\n"
    "> *Captured At* `{samsara_temp_time}`"
)


cfgs = [
    {
        "title": "⚠️ Driver Setpoint Mismatch",
        "query": query_setpoint,
        "template": common_template,
    },
    {
        "title": "🔥 99°F Required Temp",
        "query": query_99,
        "template": common_template,
    },
    {
        "title": "🚨 Temperature Out of Range",
        "query": query_anomalies,
        "template": (
            f"{common_template} \n"
            "> *Severity:* `{priority_id} ({priority})`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}`/`{max_allowed_deviation}`"
        )
    },
    
    {
        "title": "ℹ️ Dry Load",
        "query": query_dryload,
        "template": (
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}` | *Leg*: `{leg_id}` | *status:* `{status}`\n"
            "> *Required Reefer Mode:* `{required_reefer_mode}` | *Actual Samsara Reefer Mode:* `{samsara_reefer_mode}` \n"
            "> *Last Updated On:* `{samsara_reefer_mode_time}`  | *Note:* `{Note}`\n "
        )
    },
    {
        "title": "‼️ Attention / Dry Load Issue ‼️  ",
        "query": query_dryload_anomalies,
        "template": (
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}` | *Leg*: `{leg_id}` | *status:* `{status}`\n"
            "> *Reefer Mode:* `{required_reefer_mode}` | *Actual Samsara Reefer Mode:* `{samsara_reefer_mode}‼️ ` \n"
            "> *Last Updated On:* `{samsara_reefer_mode_time}` | *Status:* `{status}`"
            "> *Severity:* `{priority_id} ({priority})`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}`/`{max_allowed_deviation}`"
        )
    },
    # dry load alerts can be added here if needed
]

def get_alert_filters():
    filters = select(AlertFilter).where(AlertFilter.exclude == True)
    with Session(engine) as session:
        filters = session.exec(filters).all()
    return filters

def send_slack_temp_alerts():
    blocks = []

    chicago_tz = pytz.timezone("America/Chicago")
    dt_format_str = "%b %d, %Y at %I:%M %p %Z"
    
    filters = get_alert_filters()

    # Build a set of (trailer_id, trip_id) pairs to exclude
    exclude_pairs = set((f.trailer_id, f.trip_id) for f in filters)
    
    for cfg in cfgs:
        df = pd.read_gbq(cfg["query"], progress_bar_type=None, project_id='agy-intelligence-hub')
        
        if not df.empty:
            # Filter out excluded alerts
            df = df[~df.apply(lambda row: (row['trailer_id'], row['trip_id']) in exclude_pairs, axis=1)]

            # Format the datetime column to be more readable
            # The DATETIME from BigQuery is naive, so we make it timezone-aware before formatting.
            df['samsara_temp_time'] = df['samsara_temp_time'].dt.tz_localize(chicago_tz).dt.strftime(dt_format_str)
            
            blocks.append({"type": "header", "text": {"type": "plain_text", "text": cfg["title"], "emoji": True}})
            blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Total Alerts: {df.shape[0]}"}]})

            for _, row in df.iterrows():
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": cfg["template"].format(**row)}})

            blocks.append({"type": "divider"})

    if not blocks:
        return {"message": "No alerts to send today.", "slack_status": 200}

    # Add a human-readable timestamp to the message
    current_time = datetime.now(chicago_tz).strftime(dt_format_str)
    blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Alerts generated at: {current_time}"}]})
    print("blocks:", blocks)

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

def get_all_alert_filters():
    with Session(engine) as session:
        return session.exec(select(AlertFilter)).all()

def get_alert_filter_by_id(filter_id: int):
    with Session(engine) as session:
        return session.get(AlertFilter, filter_id)

def create_alert_filter_db(alert_filter: AlertFilterCreate):
    with Session(engine) as session:
        new_filter = AlertFilter(**alert_filter.model_dump())
        session.add(new_filter)
        session.commit()
        session.refresh(new_filter)
        return new_filter

def update_alert_filter_db(filter_id: int, alert_filter: AlertFilterUpdate):
    with Session(engine) as session:
        db_filter = session.get(AlertFilter, filter_id)
        if not db_filter:
            return None
        for key, value in alert_filter.model_dump(exclude_unset=True).items():
            setattr(db_filter, key, value)
        db_filter.updated_at = datetime.now(tz=timezone.utc)
        session.add(db_filter)
        session.commit()
        session.refresh(db_filter)
        return db_filter

def delete_alert_filter_db(filter_id: int):
    with Session(engine) as session:
        db_filter = session.get(AlertFilter, filter_id)
        if not db_filter:
            return None
        session.delete(db_filter)
        session.commit()
        return {"ok": True}