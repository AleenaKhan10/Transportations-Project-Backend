import re
from enum import Enum

from fastapi import HTTPException, Path


class IdType(str, Enum):
    TRAILER = "trailer"
    TRIP = "trip"
    TRUCK = "truck"


default_idtype_column_map = {
    IdType.TRAILER: "trailer_id",
    IdType.TRIP: "trip_id",
    IdType.TRUCK: "truck_id",
}

def is_trip_id(trip_id: str):
    return re.match(r"^TR\-\d{10}$", trip_id)

def is_truck_id(truck_id: str):
    return re.match(r"^\d+$", truck_id)

def is_trailer_id(trailer_id: str):
    return re.match(r"RX\d{5}E", trailer_id)


def get_id_type(entity_id: str):
    if is_trailer_id(entity_id):
        return IdType.TRAILER
    elif is_trip_id(entity_id):
        return IdType.TRIP
    elif is_truck_id(entity_id):
        return IdType.TRUCK

def is_entity_id(entity_id: str):
    return get_id_type(entity_id) is not None


def validate_entity_id_in_path(
    entity_id: str = Path(
        title="Entity ID", 
        description=f"Any ID for {IdType.TRIP.value}, {IdType.TRAILER.value} or {IdType.TRUCK.value}",
    ),
):
    if not is_entity_id(entity_id):
        raise HTTPException(status_code=400, detail="Invalid entity ID")
    return entity_id
