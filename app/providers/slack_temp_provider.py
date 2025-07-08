import pandas as pd
import requests
from config import settings

SLACK_BOT_TOKEN = settings.SLACK_BOT_TOKEN
SLACK_CHANNEL = settings.SLACK_CHANNEL

def send_slack_temp_alerts():
    # ----------- 99°F Alert with latest per trip/trailer -----------
    query_99 = """
        WITH latest_99 AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY samsara_temp_time DESC) AS rn
            FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
            WHERE required_temp = 99
            AND DATE(samsara_temp_time) = CURRENT_DATE()
        )
        SELECT trailer_id, trip_id, truck_id, required_temp, samsara_temp, samsara_temp_time
        FROM latest_99
        WHERE rn = 1
        ORDER BY samsara_temp_time DESC
        LIMIT 10
    """
    df99 = pd.read_gbq(query_99, project_id="agy-intelligence-hub")
    message_99 = ""
    if not df99.empty:
        message_99 = "*⚠️ 99°F Required Temperature Alerts:*\n"
        for _, row in df99.iterrows():
            message_99 += (
                f"- Trip `{row.trip_id}` | Trailer `{row.trailer_id}` | Truck `{row.truck_id}` | "
                f"Required Temp: `{row.required_temp}` | Samsara Temp: `{row.samsara_temp}` at `{row.samsara_temp_time}`\n"
            )

    # ----------- Driver Set Point Fault Alert with latest per trip/trailer -----------
    query_setpoint = """
        WITH latest_setpoint AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY trailer_id, trip_id ORDER BY samsara_temp_time DESC) AS rn
            FROM `agy-intelligence-hub.golden.ditat_samsara_merged_master`
            WHERE required_temp != 99
            AND required_temp IS NOT NULL
            AND driver_set_temp IS NOT NULL
            AND ABS(required_temp - driver_set_temp) >= 1
            AND DATE(samsara_temp_time) = CURRENT_DATE()
        )
        SELECT trailer_id, trip_id, truck_id, required_temp, driver_set_temp, samsara_temp_time
        FROM latest_setpoint
        WHERE rn = 1
        ORDER BY samsara_temp_time DESC
        LIMIT 10
    """
    df_setpoint = pd.read_gbq(query_setpoint, project_id="agy-intelligence-hub")
    message_setpoint = ""
    if not df_setpoint.empty:
        message_setpoint = "*⚠️ Driver Set Point Fault Alerts:*\n"
        for _, row in df_setpoint.iterrows():
            message_setpoint += (
                f"- Trip `{row.trip_id}` | Trailer `{row.trailer_id}` | Truck `{row.truck_id}` | "
                f"Required Temp: `{row.required_temp}` | Driver Set: `{row.driver_set_temp}` at `{row.samsara_temp_time}`\n"
            )

    # Combine and post to Slack
    full_message = "\n".join([m for m in [message_99, message_setpoint] if m])
    if not full_message:
        return {"message": "No alerts to send today.", "slack_status": 200}

    payload = {
        "channel": SLACK_CHANNEL,
        "text": full_message
    }
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    slack_response = requests.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)

    return {"slack_status": slack_response.status_code}
