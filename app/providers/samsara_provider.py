import datetime
from helpers.utils import dump_json
from helpers.samsara import SamsaraAPI
from config import Config

samsara_api = SamsaraAPI(Config.SAMSARA_TOKEN)

def ingest_samsara_data():
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