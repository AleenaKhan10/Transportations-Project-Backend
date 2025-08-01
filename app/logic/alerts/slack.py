from enum import Enum
from datetime import datetime
from typing import NamedTuple
from collections import defaultdict

import pytz
import pandas as pd
import pandas_gbq as pdg

from config import settings
from models.slack import (
    Button,
    MDText,
    Payload,
    PlainText,
    ButtonStyle,
    HeaderBlock,
    ActionsBlock,
    ContextBlock,
    DividerBlock,
    SectionBlock,
)
from models.alert_filter import MuteEnum
from helpers.agy_utils import get_id_type
from helpers.time_utils import BQTimeUnit
from logic.alerts.filters import (
    toggle_entity_alert,
    get_excluded_alert_filters,
    filter_df_by_alert_filters,
)


INTERVAL = 1
INTERVAL_UNIT = BQTimeUnit.HOUR

CHICAGO_TZ = pytz.timezone("America/Chicago")
HUMAN_DATETIME_FORMAT = "%b %d, %Y at %I:%M %p %Z"


# ------ Alert Templates ------


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


# ------ Main Functions to send Slack messages ------


def send_slack_temp_alerts():
    interval_unit = INTERVAL_UNIT.value.lower()
    context_unit_part = interval_unit if INTERVAL == 1 else f"{INTERVAL} {interval_unit}s"    
    
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
            ContextBlock(elements=[MDText(text=f"🔍 *Showing alerts from the last {context_unit_part}*")]),
        ]
        
        for alert_type in alerts_types:
            template, message_processor = alert_templates[approach][alert_type]
            _df: pd.DataFrame = alerts_df[alerts_df['alert_type'] == alert_type]
            
            if not _df.empty:
                # Continue only if there are alerts left after filtering
                if _df.empty:
                    continue

                alerts_processed += _df.shape[0]
                _df['samsara_temp_time'] = _df['samsara_temp_time'].dt.tz_convert(CHICAGO_TZ).dt.strftime(HUMAN_DATETIME_FORMAT)
                
                blocks.append(HeaderBlock(text=PlainText(text=alert_type, emoji=True)))
                blocks.append(ContextBlock(elements=[PlainText(text=f"Total Alerts: {_df.shape[0]}", emoji=False)]))

                # Process each alert individually to add mute buttons
                for _, row in _df.iterrows():
                    alert_message = message_processor(template.format(**row))
                    blocks.append(SectionBlock(text=MDText(text=alert_message)))
                    
                    # Add mute/unmute buttons for each alert (using both trip_id and trailer_id)
                    blocks.append(create_mute_actions((row['trip_id'], row['trailer_id']), channel))

                blocks.append(DividerBlock())

        # If no alerts were processed after all filters, don't send a message
        if not alerts_processed:
            print(f"No new alerts to send for approach: {approach}.")
            response[approach] = {"message": "No new alerts to send", "slack_status": None}
            continue 

        # Remove the last divider for a cleaner look
        if isinstance(blocks[-1], DividerBlock):
            blocks.pop()

        # Add a human-readable timestamp to the message
        blocks.append(get_generated_at())
        
        # Add management actions at the end
        blocks.append(get_muted_list_section(channel))

        # Send the Slack message
        response[approach] = Payload(channel=channel, blocks=blocks, text="Temperature Alerts").post()

    return response


def send_muted_entities(channel: str, user_id: str = None):
    channel = channel if channel.startswith("#") else f"#{channel}"
    muted_entities = get_excluded_alert_filters()
    if not muted_entities:
        # Send message indicating no muted entities
        return send_empty_payload(
            "📋 Muted Alerts List",
            "✅ *No alerts are currently muted.*",
            "No Muted Alerts",
            channel,
        )

    # Create a map of idtype names to entity IDs
    idtype_values_map: dict[str, list[str]] = defaultdict(list)
    for filter in muted_entities:
        idtype_values_map[filter.id_type.value].append(filter.entity_id)

    # Create blocks for the Slack message
    blocks = [
        HeaderBlock(text=PlainText(text="📋 Muted Alerts List", emoji=True)),
        ContextBlock(elements=[MDText(text=f"*Total muted entities:* {len(muted_entities)}")]),
    ]

    # Process each ID type and its entities
    for id_type, entity_ids in idtype_values_map.items():
        # Add section header for this ID type
        blocks.append(
            SectionBlock(
                text=MDText(text=f"*🔇 Muted {id_type.title()}s ({len(entity_ids)}):*")
            )
        )
        
        # Add each entity with its unmute button
        for entity_id in entity_ids:
            # Create a section with the entity ID and unmute button
            blocks.append(get_unmute_section(entity_id, channel))
        
        # Add divider between different ID types
        blocks.append(DividerBlock())
    
    # Remove the last divider for cleaner appearance
    if isinstance(blocks[-1], DividerBlock):
        blocks.pop()
    
    # Add timestamp
    blocks.append(get_generated_at())

    return Payload(
        channel=channel,
        blocks=blocks,
        text="Muted Alerts List",
        user=user_id,
    ).post()


def toggle_entity_alert_and_notify(entity_id: str, mute_type: MuteEnum, channel: str, user_id: str = None):
    entity_type = get_id_type(entity_id)
    if entity_type is None:
        return None
    toggled = toggle_entity_alert(entity_id, mute_type == MuteEnum.MUTE)
    
    message = (
        f"{entity_type.value.title()} `{entity_id}` has been *{mute_type.value}d*"
        if toggled
        else f"{entity_type.value.title()} `{entity_id}` is already *{mute_type.value}d*"
    )
    
    # If a user ID is provided, add a mention
    if user_id:
        message = f"Hello <@{user_id}>, {message[0].lower()}{message[1:]}"
    
    # This is to suppress the message from being sent to the channel
    # Rather it gets sent as an ephemeral message
    if toggled:
        user_id = None

    return Payload(channel=channel, blocks=[SectionBlock(text=MDText(text=message))], text="Muted Alerts List", user=user_id).post()


# ------ Slack Message Helpers ------


class ActionValue(NamedTuple):
    id: str
    mute_type: MuteEnum
    channel: str

    @classmethod
    def from_value(cls, value):
        if not isinstance(value, str) or value.count("/") != 2:
            return None
        mute_type, _id, channel = value.split("/")
        return cls(_id, MuteEnum(mute_type), channel)
    
    def to_value(self):
        return f"{self.mute_type.value}/{self.id}/{self.channel}"

class ActionId(Enum):
    MUTE_ENTITY = "mute_entity"
    UNMUTE_ENTITY = "unmute_entity"
    MUTED_ENTITIES = "muted_entities"

    @classmethod
    def from_id(cls, value):
        if not isinstance(value, str):
            return None
        return cls(value.lower().split("|")[0])
    
    def to_id(self):
        return f"{self.value}|{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def get_action_button(
    entity_id: str, mute_type: MuteEnum, channel: str, btn_style=ButtonStyle.DANGER
):
    id_type = get_id_type(entity_id)
    if id_type is None:
        return None

    emoji = "🔇" if mute_type == MuteEnum.MUTE else "🔊"
    action_id = (
        ActionId.MUTE_ENTITY if mute_type == MuteEnum.MUTE 
        else ActionId.UNMUTE_ENTITY
    ).to_id()

    return Button(
        text=PlainText(text=f"{emoji} {mute_type.value.title()} {id_type.value.title()}", emoji=True),
        style=btn_style,
        action_id=action_id,
        value=ActionValue(entity_id, mute_type, channel).to_value(), 
    )

def create_mute_actions(entity_ids: list[str], channel: str):
    """Create action buttons for muting/unmuting alerts by trip or trailer"""
    return ActionsBlock(
        elements=[
            get_action_button(entity_id, MuteEnum.MUTE, channel, ButtonStyle.DANGER) 
            for entity_id in entity_ids
        ]
    )

def get_unmute_section(entity_id: str, channel: str):
    return SectionBlock(
        text=MDText(text=f"• `{entity_id}`"),
        accessory=get_action_button(entity_id, MuteEnum.UNMUTE, channel, ButtonStyle.PRIMARY),
    )

def get_muted_list_section(channel: str):
    return ActionsBlock(
        elements=[
            Button(
                text=PlainText(text="📋 View Muted List", emoji=True),
                action_id=ActionId.MUTED_ENTITIES.to_id(),
                value=ActionValue("listview", MuteEnum.UNMUTE, channel).to_value(),
                style=ButtonStyle.PRIMARY,
            )
        ]
    )

def get_generated_at():
    iso_dt = datetime.now(CHICAGO_TZ).strftime(HUMAN_DATETIME_FORMAT)
    return ContextBlock(elements=[MDText(text=f"Generated at: {iso_dt}")])

def send_empty_payload(header: str, desc: str, footer: str, channel: str):
    return Payload(
        channel=channel,
        blocks=[
            HeaderBlock(text=PlainText(text=header, emoji=True)),
            SectionBlock(text=MDText(text=desc)),
        ],
        text=footer,
    ).post()
