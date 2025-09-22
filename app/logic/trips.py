import json
from typing import Any
from datetime import datetime, timedelta, timezone

import pandas as pd
import pandas_gbq as pdg
from fastapi import BackgroundTasks

from helpers.time_utils import BQTimeUnit
from helpers.agy_utils import is_trailer_id, is_trip_id
from utils.weather_api import get_weather_df, make_weather_info


def get_trailer_and_trips():
    df = pdg.read_gbq("""
        SELECT trailer_id, ARRAY_AGG(distinct trip_id) as trip_ids 
        FROM `agy-intelligence-hub.diamond.master_grouped_subtrip_level` 
        GROUP BY trailer_id
    """, project_id='agy-intelligence-hub')
    
    return json.loads(df.to_json(orient='records'))

def get_trip_data(trailer_id: str, trip_id: str):
    print(trailer_id, trip_id)
    if not is_trip_id(trip_id) or not is_trailer_id(trailer_id):
        return {"error": "Invalid trailer or trip id format"}
    df = pdg.read_gbq(f"""
        SELECT * FROM `agy-intelligence-hub.diamond.master_grouped_subtrip_level` 
        WHERE trailer_id = '{trailer_id}' AND trip_id = '{trip_id}'
    """)
    if df.empty:
        return {"error": "No data found for the provided trailer_id and trip_id"}
    return json.loads(df.rename(columns={'t': 'aggregated_data'}).to_json(orient='records'))


def add_weather_data_to_grouped_alerts(df: pd.DataFrame, bt: BackgroundTasks = None) -> pd.DataFrame:
    """
    This function takes in a DataFrame of grouped alerts and adds weather data to it.
    
    The function first explodes the 't' column into separate rows, then normalizes the JSON data in the 't' column.
    It then merges the two DataFrames together.
    
    The function then filters out the rows where the location is not available and the samsara temp time is older than 1 hour.
    It then maps the latitude and longitude columns to rounded values.
    
    The function then gets the unique latitude and longitude pairs and fetches the weather data for these locations.
    It then merges the weather data with the original DataFrame.
    
    Finally, the function defines the columns to group by, the columns to aggregate into the 't' array of structs, 
    sorts the DataFrame by samsara temp time DESC, groups and aggregates the DataFrame, and converts the 't' columns into a list of dictionaries.
    """
    
    df_exploded = df.explode("t")
    df_normalized = pd.json_normalize(df_exploded["t"])
    other_columns = df_exploded.drop("t", axis=1).reset_index(drop=True)
    result_df = pd.concat([other_columns, df_normalized], axis=1)
    del df_exploded
    del df_normalized

    # Filter out rows where location is not available and samsara temp time is older than 1 hour
    result_df = result_df[
        pd.isna(result_df["location"])
        & (
            result_df["samsara_temp_time"]
            > (datetime.now(tz=timezone.utc) - timedelta(hours=1))
        )
    ]

    # Map the latitude and longitude columns to rounded values
    result_df[["latitude", "longitude"]] = result_df[["latitude", "longitude"]].map(
        lambda x: round(x, 2)
    )

    # Get unique latitude and longitude pairs
    lat_lons = (
        result_df[
            pd.isna(result_df["location"])
            & (
                result_df["samsara_temp_time"]
                > (datetime.now(tz=timezone.utc) - timedelta(hours=1))
            )
        ][["latitude", "longitude"]]
        .map(lambda x: round(x, 2))
        .apply(tuple, axis=1)
        .unique()
    )

    if lat_lons:
        # Fetch weather data
        weather_df = get_weather_df(lat_lons, bt=bt, keep_raw_columns_in_df=False)

        # Merge weather data with original DataFrame
        result_df = result_df.merge(weather_df, how="left", on=["latitude", "longitude"])
    else:
        result_df["weather_info"] = None

    # Add a weather info column
    result_df["weather_info"] = result_df["weather_info"].fillna(
        result_df.apply(
            lambda x: None if x["location"] is None else make_weather_info(x), axis=1
        )
    )

    # Define columns to group by
    group_cols = ["trailer_id", "trip_id", "leg_id", "driver_id", "truck_id", "status_id", 
                "status", "priority", "trip_start_time", "trip_end_time", 
                "leg_start_time", "leg_end_time", "sub_leg_start_time", "sub_leg_end_time"]

    # Define columns to be aggregated into the 't' array of structs
    t_cols = ["reefer_mode_id", "reefer_mode", "required_temp", "driver_set_temp", 
            "samsara_temp", "samsara_temp_time", "alert_type", "remarks", "weather_info"]

    # Sort by samsara temp time DESC
    result_df = result_df.sort_values("samsara_temp_time", ascending=False)

    # Group and aggregate
    final_df = result_df.groupby(group_cols).agg({
        **{col: list for col in t_cols}  # Aggregate as lists for t columns
    }).reset_index()
    del result_df

    # Convert the t columns into list of dictionaries
    final_df['t'] = final_df[t_cols].apply(
        lambda row: [dict(zip(t_cols, values)) for values in zip(*row.values)], 
        axis=1
    )

    # Drop the individual t columns since they're now in the 't' column
    final_df = final_df.drop(columns=t_cols)

    return final_df

def fetch_latest_alerts(value: int, unit: BQTimeUnit, bt: BackgroundTasks = None) -> dict[str, Any]:  
    query = f"""
        SELECT *
        FROM `agy-intelligence-hub.diamond.get_master_grouped_subtrip_level`({value}, '{unit.value}', TRUE)
    """
    df = pdg.read_gbq(query, project_id='agy-intelligence-hub', progress_bar_type=None)
    if df.empty:
        return {"error": "No data found"}
    df = add_weather_data_to_grouped_alerts(df, bt)
    return json.loads(df.rename(columns={'t': 'aggregated_data'}).to_json(orient='records'))
