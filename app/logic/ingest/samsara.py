import datetime

import numpy as np
import pandas as pd
from config import settings
from helpers.utils import dump_json
from providers.samsara import SamsaraAPI


TAG_IDS = [107382]

samsara_api = SamsaraAPI(settings.SAMSARA_TOKEN)


def ingest_trailer_temp_data(ingested_at: datetime.datetime | None = None):
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
    merged_df['ingestedAt'] = ingested_at or datetime.datetime.now(tz=datetime.timezone.utc)
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


def ingest_trailer_stats_data(ingested_at: datetime.datetime | None = None):
    ingested_at = ingested_at or datetime.datetime.now(tz=datetime.timezone.utc)
    
    types = ["reeferRunMode", "reeferSetPointTemperatureMilliCZone1"]
    flattened_dfs = []
    time_cols = []
    
    stats_df = samsara_api.get_all_stats(tag_ids=[107382], types=types)
    
    cols_to_flatten = types
    for col in cols_to_flatten:
        # Normalize the column
        flattened = pd.json_normalize(stats_df[col])
        # Add a prefix to the new columns
        flattened.columns = [f"{col}{sub_col.title()}" for sub_col in flattened.columns]
        time_cols.extend([col for col in flattened.columns if 'Time' in col])
        flattened_dfs.append(flattened)

    # Concatenate the original DataFrame (without the nested columns) with the new flattened DataFrames
    stats_df = pd.concat([stats_df.drop(columns=cols_to_flatten)] + flattened_dfs, axis=1)
    
    # Fill missing timestamps with the current timestamp
    stats_df[time_cols] = stats_df[time_cols].fillna(ingested_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
    
    # Replace NaN values with None
    # NOTE: Do we actually need to keep the NaN values? As during the merging process in BQ the non-matching rows are anyway null!
    stats_df = stats_df.replace({np.nan: None}).reset_index(drop=True)

    stats_df["ingestedAt"] = ingested_at
    stats_df.to_gbq(
        destination_table="bronze.samsara_trailer_stats",
        project_id="agy-intelligence-hub",
        if_exists="append",
    )
    return {"status": "success"}
