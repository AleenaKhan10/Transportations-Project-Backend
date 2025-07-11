import json
import pandas_gbq as pd
from helpers.utils import is_trailer_id, is_trip_id

def get_trailer_and_trips():
    df = pd.read_gbq("""
        SELECT trailer_id, ARRAY_AGG(distinct trip_id) as trip_ids 
        FROM `agy-intelligence-hub.diamond.master_grouped_sub-trip_level` 
        GROUP BY trailer_id
    """, project_id='agy-intelligence-hub')
    
    return json.loads(df.to_json(orient='records'))

def get_trip_data(trailer_id: str, trip_id: str):
    print(trailer_id, trip_id)
    if not is_trip_id(trip_id) or not is_trailer_id(trailer_id):
        return {"error": "Invalid trailer or trip id format"}
    df = pd.read_gbq(f"""
        SELECT * FROM `agy-intelligence-hub.diamond.master_grouped_sub-trip_level` 
        WHERE trailer_id = '{trailer_id}' AND trip_id = '{trip_id}'
    """)
    if df.empty:
        return {"error": "No data found for the provided trailer_id and trip_id"}
    return json.loads(df.rename(columns={'t': 'aggregated_data'}).to_json(orient='records')) 