from datetime import datetime
from collections import defaultdict

import pytz
import requests
import pandas as pd
import pandas_gbq as pdg

from config import settings
from helpers.time_utils import BQTimeUnit
from logic.alerts.filters import get_excluded_alert_filters, filter_df_by_alert_filters


SLACK_BOT_TOKEN = settings.SLACK_BOT_TOKEN

INTERVAL = 1
INTERVAL_UNIT = BQTimeUnit.HOUR

CHICAGO_TZ = pytz.timezone("America/Chicago")


def get_mute_webhook_url(entity_id: str):
    return f"{settings.CLOUD_RUN_URL}/webhook/alerts/mute/{entity_id}?token={settings.WEBHOOK_TOKEN}"

def get_unmute_webhook_url(entity_id: str):
    return f"{settings.CLOUD_RUN_URL}/webhook/alerts/unmute/{entity_id}?token={settings.WEBHOOK_TOKEN}"


def create_mute_actions(trip_id: str, trailer_id: str):
    """Create action buttons for muting/unmuting alerts by trip or trailer"""
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔇 Mute Trip", "emoji": True},
                "style": "danger",
                "url": get_mute_webhook_url(trip_id),
                "action_id": f"mute_trip_{trip_id}"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔇 Mute Trailer", "emoji": True},
                "style": "danger",
                "url": get_mute_webhook_url(trailer_id),
                "action_id": f"mute_trailer_{trailer_id}"
            },
        ]
    }


def send_muted_entities(channel: str):
    channel = channel if channel.startswith("#") else f"#{channel}"
    muted_entities = get_excluded_alert_filters()
    if not muted_entities:
        # Send message indicating no muted entities
        payload = {
            "channel": channel,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "📋 Muted Alerts List", "emoji": True}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "✅ *No alerts are currently muted.*"}
                }
            ],
            "text": "No Muted Alerts"
        }
        headers = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        }
        slack_response = requests.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)
        return {
            "message": slack_response.text,
            "slack_status": slack_response.status_code,
        }
    
    # Create a map of idtype names to entity IDs
    idtype_values_map: dict[str, list[str]] = defaultdict(list)
    for filter in muted_entities:
        idtype_values_map[filter.id_type.value].append(filter.entity_id)

    # Create blocks for the Slack message
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 Muted Alerts List", "emoji": True}
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Total muted entities:* {len(muted_entities)}"}]
        }
    ]

    # Process each ID type and its entities
    for id_type, entity_ids in idtype_values_map.items():
        # Add section header for this ID type
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🔇 Muted {id_type.title()}s ({len(entity_ids)}):*"}
        })
        
        # Add each entity with its unmute button
        for entity_id in entity_ids:
            # Create a section with the entity ID and unmute button
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"• `{entity_id}`"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔊 Unmute", "emoji": True},
                    "style": "primary",
                    "url": get_unmute_webhook_url(entity_id),
                    "action_id": f"unmute_{id_type}_{entity_id}"
                }
            })
        
        # Add divider between different ID types
        blocks.append({"type": "divider"})
    
    # Remove the last divider for cleaner appearance
    if blocks[-1]["type"] == "divider":
        blocks.pop()
    
    # Add timestamp
    current_time = datetime.now(CHICAGO_TZ).strftime("%b %d, %Y at %I:%M %p %Z")
    blocks.append({
        "type": "context",
        "elements": [{"type": "plain_text", "text": f"Generated at: {current_time}"}]
    })

    payload = {
        "channel": channel,
        "blocks": blocks,
        "text": "Muted Alerts List"
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    slack_response = requests.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)

    return {
        "message": slack_response.text,
        "slack_status": slack_response.status_code,
    }


def process_message_generic(message: str):
    return (
        message
        .replace("> *Driver Set:* `nan°`", "> *Driver Set:* `unknown`")
        .replace('\n> *Note:* `None`', '')
        .replace('\n> *Note:* ``', '')
    )


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
        ), process_message_generic),
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
        ), process_message_generic),
    },
}


def send_slack_temp_alerts():
    interval_unit = INTERVAL_UNIT.value.lower()
    context_unit_part = interval_unit if INTERVAL == 1 else f"{INTERVAL} {interval_unit}s"

    dt_format_str = "%b %d, %Y at %I:%M %p %Z"
    
    filters = get_excluded_alert_filters()
    
    query = f"""
      SELECT * FROM `agy-intelligence-hub.diamond.get_master_with_alerts`(TRUE)
      WHERE 
        samsara_temp_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {INTERVAL} {INTERVAL_UNIT.value})
      AND 
        alert_type IS NOT NULL
    """

    alerts_df = pdg.read_gbq(query, progress_bar_type=None, project_id='agy-intelligence-hub')
    
    # Filter out alerts that match the filters
    alerts_df = filter_df_by_alert_filters(alerts_df, filters)
    
    response = {}
    
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
                # Continue only if there are alerts left after filtering
                if _df.empty:
                    continue

                alerts_processed += _df.shape[0]
                _df['samsara_temp_time'] = _df['samsara_temp_time'].dt.tz_convert(CHICAGO_TZ).dt.strftime(dt_format_str)
                
                blocks.append({"type": "header", "text": {"type": "plain_text", "text": alert_type, "emoji": True}})
                blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Total Alerts: {_df.shape[0]}"}]})

                # Process each alert individually to add mute buttons
                for _, row in _df.iterrows():
                    alert_message = message_processor(template.format(**row))
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": alert_message}})
                    
                    # Add mute/unmute buttons for each alert (using both trip_id and trailer_id)
                    blocks.append(create_mute_actions(row['trip_id'], row['trailer_id']))

                blocks.append({"type": "divider"})

        # If no alerts were processed after all filters, don't send a message
        if not alerts_processed:
            print(f"No new alerts to send for approach: {approach}.")
            response[approach] = {"message": "No new alerts to send", "slack_status": None}
            continue 

        # Remove the last divider for a cleaner look
        if blocks[-1]["type"] == "divider":
            blocks.pop()

        # Add a human-readable timestamp to the message
        current_time = datetime.now(CHICAGO_TZ).strftime(dt_format_str)
        blocks.append({"type": "context", "elements": [{"type": "plain_text", "text": f"Alerts generated at: {current_time}"}]})
        
        # Add management actions at the end
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📋 View Muted List", "emoji": True},
                    "style": "primary",
                    "url": f"{settings.CLOUD_RUN_URL}/webhook/alerts/slack/muted?channel={channel}&token={settings.WEBHOOK_TOKEN}",
                    "action_id": "view_muted_list"
                }
            ]
        })
        
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
        response[approach] = {"message": slack_response.text, "slack_status": slack_response.status_code}

    return response