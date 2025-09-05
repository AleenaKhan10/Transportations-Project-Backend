import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import verify_static_token
from helpers.time_utils import get_datetime_range, get_pairs_from_range, TimeUnit
from helpers.utils import (
    run_functions_in_parallel,
    run_parallel_exec_but_return_in_order,
)
from logic.ingest import (
    ingest_ditat_data,
    ingest_trailer_temp_data,
    ingest_trailer_stats_data,
    ingest_detailed_trailer_stats_data,
    ingest_detailed_location_data,
)


router = APIRouter(prefix="/ingest", dependencies=[Depends(verify_static_token)])


@router.post("/ditat", dependencies=[Depends(verify_static_token)])
async def ingest_ditat():
    result = {"ditat_data": ingest_ditat_data()}
    return JSONResponse(content=result) 


@router.post("/samsara", dependencies=[Depends(verify_static_token)])
async def ingest_samsara_temp():
    ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)
    
    def trailer_temp():
        return ingest_trailer_temp_data(ingested_at)
    def trailer_stats():
        return ingest_trailer_stats_data(ingested_at)
    def detailed_trailer_stats():
        return ingest_detailed_trailer_stats_data(ingested_at)
    def detailed_location():
        return ingest_detailed_location_data(ingested_at)
    result = run_functions_in_parallel(
        [trailer_temp, trailer_stats, detailed_trailer_stats, detailed_location], max_workers=4
    )
    return JSONResponse(content=dict(result))


@router.post("/samsara/stats/backfill", dependencies=[Depends(verify_static_token)])
async def backfill_samsara_detailed_stats(
    start_ms: int, end_ms: int, unit: TimeUnit = TimeUnit.DAYS, granularity: int = 1
):
    """
    Backfills detailed trailer stats data for a given time range in the Samsara API.

    This endpoint is meant to be used for backfilling data that was missed due to any reason.
    It takes in the start and end time in milliseconds since epoch, and will ingest the data
    in parallel for multiple days. The `unit` parameter specifies the time granularity unit,
    and the `granularity` parameter specifies the number of units in the time granularity.

    Args:
        start_ms (int): Start time in milliseconds since epoch.
        end_ms (int): End time in milliseconds since epoch.
        unit (TimeUnit): Time granularity unit. Defaults to TimeUnit.DAYS.
        granularity (int): Number of units in the time granularity. Defaults to 1.

    Returns:
        JSONResponse: A JSON response containing the results of the backfill.
    """
    
    ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)
    start_time = datetime.datetime.fromtimestamp(
        start_ms / 1000, tz=datetime.timezone.utc
    )
    end_time = datetime.datetime.fromtimestamp(end_ms / 1000, tz=datetime.timezone.utc)
    
    # Since the data becomes huge, we run the ingestion in parallel for multiple days
    time_range_pairs = get_pairs_from_range(
        get_datetime_range(start_time, end_time, granularity=granularity, unit=unit)
    )
    logger.info(
        f"Backfilling {len(time_range_pairs)} time ranges between "
        f"{start_ms} and {end_ms} with granularity {granularity} {unit.value}"
    )
    
    def _get_key(time_pair: tuple[datetime.datetime, datetime.datetime]):
        start_time, end_time = time_pair
        return f"detailed_trailer_stats_{int(start_time.timestamp()*1000)}->{int(end_time.timestamp()*1000)}"
    
    def _ingest(time_pair: tuple[datetime.datetime, datetime.datetime]):
        start_time, end_time = time_pair
        return {
            _get_key(time_pair): ingest_detailed_trailer_stats_data(
                start_time=start_time, 
                end_time=end_time, 
                ingested_at=ingested_at, 
            )
        }
    
    results = run_parallel_exec_but_return_in_order(_ingest, time_range_pairs, max_workers=8)
    
    result = {}
    for time_pair, r in zip(time_range_pairs, results):
        if not isinstance(r, dict):
            r = { _get_key(time_pair): str(r) }
        result.update(r)
    
    return JSONResponse(content=result)
