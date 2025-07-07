import re
import json

import pandas_gbq as pd
from flask import Request
import functions_framework


DUMMY_TOKEN = '0bcf49a90e765ca3d7ea8ba1ae25373142e374c556919aa3e5c41adf8b2ff220'

def is_trip_id(trip_id: str):
    return re.match(r"[A-Z]{2}-\d{10}-\d{2}", trip_id)

def is_trailer_id(trailer_id: str):
    return re.match(r"RX\d{5}E", trailer_id)

def authenticate(request: Request):
    API_KEY = request.headers.get('X-API-Key')
    if not API_KEY:
        error_response = {
            "status": "error",
            "message": "X-API-Key is missing."
        }
        return json.dumps(error_response), 400, {'Content-Type': 'application/json'}
    if API_KEY != DUMMY_TOKEN:
        error_response = {
            "status": "error",
            "message": "X-API-Key is invalid."
        }
        return json.dumps(error_response), 401, {'Content-Type': 'application/json'}
    return None  # Authentication successful


@functions_framework.http
def get_trailer_and_trips(request: Request):
    # Check authentication and return error if it fails
    auth_result = authenticate(request)
    if auth_result:
        return auth_result
    
    df = pd.read_gbq("""
        SELECT trailer_id, ARRAY_AGG(distinct trip_id) as trip_ids 
        FROM `agy-intelligence-hub.golden.master_grouped_sub-trip_level` 
        GROUP BY trailer_id
    """)
    return df.to_json(orient='records')


@functions_framework.http
def get_trip_data(request: Request):
    auth_result = authenticate(request)
    if auth_result:
        return auth_result
    
    trailer_id = request.args.get('trailer_id', None)
    if trailer_id is None:
        error_response = {
            "status": "error",
            "message": "Missing trailer id. Please provide the `trailer_id` as a query parameter"
        }
        return json.dumps(error_response), 400, {'Content-Type': 'application/json'}
    
    trip_id = request.args.get('trip_id', None)
    if trip_id is None:
        error_response = {
            "status": "error",
            "message": "Missing trip id. Please provide the `trip_id` as a query parameter"
        }
        return json.dumps(error_response), 400, {'Content-Type': 'application/json'}
    
    if not is_trip_id(trip_id) or not is_trailer_id(trailer_id):
        error_response = {
            "status": "error",
            "message": "Invalid trailer or trip id format"
        }
        return json.dumps(error_response), 400, {'Content-Type': 'application/json'}
    
    df = pd.read_gbq(f"""
        SELECT * FROM `agy-intelligence-hub.golden.master_grouped_sub-trip_level` 
        WHERE trailer_id = '{trailer_id}' AND trip_id = '{trip_id}'
    """)
     
    if df.empty:
        error_response = {
            "status": "error",
            "message": "No data found for the provided trailer_id and trip_id"
        }
        return json.dumps(error_response), 404, {'Content-Type': 'application/json'}
    
    return df.rename(columns={'t': 'aggregated_data'}).to_json(orient='records')
