import datetime

import pandas as pd
from config import settings
from helpers.utils import dump_json
from providers.samsara import SamsaraAPI


TAG_IDS = [107382]

samsara_api = SamsaraAPI(settings.SAMSARA_TOKEN)


def ingest_trailer_temp_data():
    sensors_df = samsara_api.get_all_sensors()
    sensor_ids = sensors_df["id"].tolist()
    temperatures_df = samsara_api.get_temperatures_batched(sensor_ids)
    trailers_df = samsara_api.get_all_trailers(tag_ids=[107382])
    merged_df = (
        temperatures_df.merge(trailers_df, left_on="trailerId", right_on="id", how="inner")
        .drop(["trailerId"], axis=1)
        .rename(
            {
                "id_x": "sensorId",
                "id_y": "trailerId",
                "name_x": "sensorName",
                "name_y": "trailerName",
            },
            axis=1,
        )
    )
    merged_df['tags'] = merged_df['tags'].apply(dump_json)
    merged_df['installedGateway'] = merged_df['installedGateway'].apply(dump_json)
    merged_df['externalIds'] = merged_df['externalIds'].apply(dump_json)
    merged_df['ingestedAt'] = datetime.datetime.now(tz=datetime.timezone.utc)
    merged_df = merged_df[
        [
            "sensorId",
            "sensorName",
            "ambientTemperature",
            "ambientTemperatureTime",
            "vehicleId",
            "tags",
            "installedGateway",
            "trailerId",
            "trailerName",
            "externalIds",
            "enabledForMobile",
            "notes",
            "licensePlate",
            "trailerSerialNumber",
        ]
    ]
    merged_df.to_gbq(
        destination_table="bronze.samsara_full",
        project_id="agy-intelligence-hub",
        if_exists="append",
    )
    return {"status": "success"}


def ingest_trailer_stats_data():
    types = ["reeferRunMode", "reeferSetPointTemperatureMilliCZone1"]
    stats_df = samsara_api.get_all_stats(tag_ids=[107382], types=types)
    flattened_dfs = []
    cols_to_check_nan = []
    
    cols_to_flatten = types
    for col in cols_to_flatten:
        # Normalize the column
        flattened = pd.json_normalize(stats_df[col])
        # Add a prefix to the new columns
        flattened.columns = [f"{col}{sub_col.title()}" for sub_col in flattened.columns]
        cols_to_check_nan.extend(flattened.columns)
        flattened_dfs.append(flattened)

    # Concatenate the original DataFrame (without the nested columns) with the new flattened DataFrames
    stats_df = (
        pd.concat([stats_df.drop(columns=cols_to_flatten)] + flattened_dfs, axis=1)
        .dropna(subset=cols_to_check_nan)
        .reset_index(drop=True)
    )
    stats_df["ingestedAt"] = datetime.datetime.now(tz=datetime.timezone.utc)
    stats_df.to_gbq(
        destination_table="bronze.samsara_trailer_stats",
        project_id="agy-intelligence-hub",
        if_exists="append",
    )
    return {"status": "success"}
