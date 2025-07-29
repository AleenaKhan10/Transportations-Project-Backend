from datetime import datetime, timezone

import pytz
import requests
import pandas as pd
import pandas_gbq as pdg
from sqlmodel import select, Session

from config import settings
from db.database import engine
from models.alert_filter import AlertFilter, AlertFilterCreate, AlertFilterUpdate


SLACK_BOT_TOKEN = settings.SLACK_BOT_TOKEN

INTERVAL = 1
INTERVAL_UNIT = "HOUR"


def process_message_generic(message: str):
    return message

def process_dry_load_message(message: str):
    return message.replace('\n> *Note:* `None`', '')

# A mapping of approach to slack channels
approach_to_channel = {
    "approach1": settings.ALERTS_APPROACH1_SLACK_CHANNEL,
    "approach2": settings.ALERTS_APPROACH2_SLACK_CHANNEL
}

# A dictionary of readable and visually appealing set of templates
alert_templates = {
    "approach1": {
        "⚠️ Driver Setpoint Mismatch": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Driver Set:* `{driver_set_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Captured At:* `{samsara_temp_time}`"
        ), process_message_generic),
        "🔥 99°F Required Temp": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Driver Set:* `{driver_set_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Captured At:* `{samsara_temp_time}`"
        ), process_message_generic),
        "🚨 Temperature Out of Range": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Severity:* `{priority_id} ({priority})`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Driver Set:* `{driver_set_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}° / {max_allowed_deviation}°`\n"
            "> *Captured At:* `{samsara_temp_time}`"
        ), process_message_generic),
        "ℹ️ Dry Load": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Required Reefer Mode:* `{required_reefer_mode}`\n"
            "> *Actual Reefer Mode:* `{reefer_mode}`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Last Updated On:* `{samsara_temp_time}`\n"
            "> *Note:* `{remarks}`"
        ), process_dry_load_message),
        "‼️ Attention / Issue ‼️": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Severity:* `{priority_id} ({priority})`\n"
            "> *Required Reefer Mode:* `{required_reefer_mode}`\n"
            "> *Actual Reefer Mode:* `{reefer_mode} ‼️`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}° / {max_allowed_deviation}°`\n"
            "> *Last Updated On:* `{samsara_temp_time}`"
        ), process_message_generic),
    },
    "approach2": {
        "🔥 99°F Required Temp": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Captured At:* `{samsara_temp_time}`"
        ), process_message_generic),
        "🚨 Temperature Out of Range": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Severity:* `{priority_id} ({priority})`\n"
            "> *Required Temp:* `{required_temp}°`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Deviation (Actual/Max):* `{temp_diff}° / {max_allowed_deviation}°`\n"
            "> *Captured At:* `{samsara_temp_time}`"
        ), process_message_generic),
        "ℹ️ Dry Load": ((
            "*Trip:* `{trip_id}` | *Trailer:* `{trailer_id}` | *Truck:* `{truck_id}`\n"
            ">*Leg:* `{leg_id}` | *Status:* `{status}`\n"
            "> *Required Reefer Mode:* `{required_reefer_mode}`\n"
            "> *Actual Reefer Mode:* `{reefer_mode}`\n"
            "> *Samsara Temp:* `{samsara_temp}°`\n"
            "> *Last Updated On:* `{samsara_temp_time}`\n"
            "> *Note:* `{remarks}`"
        ), process_dry_load_message),
    },
}


def get_alert_filters():
    filters = select(AlertFilter).where(AlertFilter.exclude is True)
    with Session(engine) as session:
        filters = session.exec(filters).all()
    return filters


def send_slack_temp_alerts():
    context_unit_part = INTERVAL_UNIT.lower() if INTERVAL == 1 else f"{INTERVAL} {INTERVAL_UNIT.lower()}s"

    chicago_tz = pytz.timezone("America/Chicago")
    dt_format_str = "%b %d, %Y at %I:%M %p %Z"
    
    filters = get_alert_filters()

    # Build a set of (trailer_id, trip_id) pairs to exclude
    exclude_pairs = set((f.trailer_id, f.trip_id) for f in filters)
    
    query = f"""
      SELECT * FROM `agy-intelligence-hub.diamond.get_master_with_alerts`(TRUE)
      WHERE 
        samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {INTERVAL} {INTERVAL_UNIT})
      AND 
        alert_type IS NOT NULL
    """

    alerts_df = pdg.read_gbq(query, progress_bar_type=None, project_id='agy-intelligence-hub')
    
    for approach, channel in approach_to_channel.items():
        print(f"Processing alerts for approach: {approach} and sending to channel: {channel}")
        # Keep track of how many alerts are actually processed
        alerts_processed = 0

        # Get unique alert types in a sorted order
        alerts_types: list[str] = alert_templates[approach].keys()
        
        # Create a list of blocks for the Slack message
        blocks = [
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"🔍 *Showing alerts from the last {context_unit_part}*"}]}
        ]
        
        for alert_type in alerts_types:
            template, message_processor = alert_templates[approach][alert_type]
            _df: pd.DataFrame = alerts_df[alerts_df['alert_type'] == alert_type]
            
            if not _df.empty:
                _df = _df[~_df.apply(lambda row: (row['trailer_id'], row['trip_id']) in exclude_pairs, axis=1)]
                
                # Continue only if there are alerts left after filtering
                if _df.empty:
                    continue

                alerts_processed += _df.shape[0]
                _df['samsara_temp_time'] = _df['samsara_temp_time'].dt.tz_convert(chicago_tz).dt.strftime(dt_format_str)
                
                blocks.append({"type": "header", "text": {"type": "plain_text", "text": alert_type, "emoji": True}})
                blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Total Alerts: {_df.shape[0]}"}]})

                alert_message = "\n".join(_df.apply(lambda x: message_processor(template.format(**x)), axis=1).to_list())
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": alert_message}})

                blocks.append({"type": "divider"})

        # If no alerts were processed after all filters, don't send a message
        if not alerts_processed:
            print(f"No new alerts to send for approach: {approach}.")
            continue 

        # Remove the last divider for a cleaner look
        if blocks[-1]["type"] == "divider":
            blocks.pop()

        # Add a human-readable timestamp to the message
        current_time = datetime.now(chicago_tz).strftime(dt_format_str)
        blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Alerts generated at: {current_time}"}]})
        print("blocks:", blocks)

        payload = {
            "channel": channel,
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