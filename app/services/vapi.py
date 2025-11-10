from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import httpx

from helpers import logger
from logic.auth.security import get_current_user
from models.drivers import Driver
from models.driver_reports import DriverReport, DriverMorningReport
from models.vapi import VAPICallRequest, DriverCallInsightsUpdate, VAPIData
from utils.vapi_client import vapi_client
from config import settings


router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
router_no_auth = APIRouter(prefix="/api")


@router.post("/vapi-call/{driver_id}")
async def make_vapi_call(driver_id: str, body: Optional[VAPIData] = None):
    """
    Initiates a VAPI AI-powered call to a specific driver
    """
    try:
        logger.info("VAPI CALL SINGLE")

        if not driver_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Driver ID is required",
                    "status": "validation_error",
                },
            )

        # Retrieve driver information
        driver = Driver.get_by_id(driver_id)

        if not driver:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Driver not found",
                    "status": "driver_not_found",
                },
            )

        # Validate driver has phone number
        if not driver.phoneNumber:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Driver phone number is required for VAPI call",
                    "status": "missing_phone_number",
                },
            )

        logger.info(
            f"📞 Initiating VAPI call to driver: {driver.firstName} {driver.lastName} ({driver_id})"
        )

        # Convert driver to dict for VAPI client
        driver_dict = driver.model_dump()

        # If body data is provided, add it to the driver dict
        if body:
            vapi_data = body.model_dump(exclude_none=True)
            driver_dict.update({"vapi_data": vapi_data})
            logger.info(f"📋 Using provided VAPI data: {vapi_data}")

        # Make VAPI API call with driver data
        vapi_result = await vapi_client.create_vapi_call(driver_dict)

        # Return success response
        return {
            "success": True,
            "callId": vapi_result["callId"],
            "driverId": driver.driverId,
            "phoneNumber": driver.phoneNumber,
            "driverName": f"{driver.firstName} {driver.lastName}",
            "status": vapi_result["status"],
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"❌ Error making VAPI call: {str(error)}")

        # Handle different error types
        if "VAPI API Error" in str(error):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": str(error),
                    "status": "vapi_api_error",
                },
            )
        elif "Network error" in str(error):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": str(error),
                    "status": "network_error",
                },
            )
        elif "environment variable" in str(error):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "VAPI configuration error",
                    "status": "configuration_error",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(error),
                    "status": "internal_error",
                },
            )


@router.post("/vapi-calls/batch")
async def make_vapi_calls_to_multiple_drivers(request: VAPICallRequest):
    """
    Initiates VAPI AI-powered calls to multiple drivers simultaneously
    """
    try:
        driver_ids = request.driverIds

        # Validate input
        if not driver_ids or len(driver_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "driverIds must be a non-empty array",
                    "status": "validation_error",
                },
            )

        logger.info(
            f"📞 Processing batch VAPI calls for {len(driver_ids)} driver(s): {', '.join(driver_ids)}"
        )

        # Get all drivers by IDs
        with Driver.get_session() as session:
            from sqlmodel import select

            statement = select(Driver).where(Driver.driverId.in_(driver_ids))
            drivers = session.exec(statement).all()

        # Filter out invalid driver IDs and log warnings
        valid_drivers = list(drivers)
        found_driver_ids = [d.driverId for d in valid_drivers]
        invalid_driver_ids = [id for id in driver_ids if id not in found_driver_ids]

        if invalid_driver_ids:
            logger.warning(f"⚠️ Invalid driver IDs: {', '.join(invalid_driver_ids)}")

        # Check if any valid drivers were found
        if not valid_drivers:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No valid drivers found",
                    "status": "no_valid_drivers",
                    "invalidDriverIds": invalid_driver_ids,
                },
            )

        # Validate all valid drivers have phone numbers
        drivers_without_phone = [
            driver for driver in valid_drivers if not driver.phoneNumber
        ]
        if drivers_without_phone:
            drivers_without_phone_ids = [d.driverId for d in drivers_without_phone]
            logger.warning(
                f"⚠️ Drivers without phone numbers: {', '.join(drivers_without_phone_ids)}"
            )

            # Filter out drivers without phone numbers
            drivers_with_phone = [
                driver for driver in valid_drivers if driver.phoneNumber
            ]

            if not drivers_with_phone:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "No drivers with valid phone numbers found",
                        "status": "no_valid_phone_numbers",
                        "invalidDriverIds": invalid_driver_ids
                        + drivers_without_phone_ids,
                    },
                )

            # Update arrays to reflect phone number filtering
            valid_drivers = drivers_with_phone
            invalid_driver_ids.extend(drivers_without_phone_ids)

        logger.info(f"✅ Found {len(valid_drivers)} valid driver(s) for VAPI campaign")
        for driver in valid_drivers:
            logger.info(
                f"   • {driver.firstName} {driver.lastName} ({driver.driverId}) - {driver.phoneNumber}"
            )

        # Convert drivers to dicts and add VAPI data if provided
        driver_dicts = []
        for driver in valid_drivers:
            driver_dict = driver.model_dump()

            # If vapiData is provided for this driver, add it
            if request.vapiData and driver.driverId in request.vapiData:
                vapi_data = request.vapiData[driver.driverId].model_dump(
                    exclude_none=True
                )
                driver_dict.update({"vapi_data": vapi_data})
                logger.info(
                    f"📋 Using provided VAPI data for driver {driver.driverId}: {vapi_data}"
                )

            driver_dicts.append(driver_dict)

        # Use VAPI client with multiple drivers (single campaign)
        vapi_response = await vapi_client.create_vapi_call(driver_dicts)

        # Return comprehensive response with driver details
        driver_details = []
        for driver in valid_drivers:
            driver_details.append(
                {
                    "driverId": driver.driverId,
                    "phoneNumber": driver.phoneNumber,
                    "driverName": f"{driver.firstName} {driver.lastName}",
                }
            )

        return {
            "success": True,
            "campaignId": vapi_response["campaignId"],
            "callId": vapi_response["callId"],  # For backward compatibility
            "totalDrivers": len(driver_ids),
            "validDrivers": len(valid_drivers),
            "invalidDrivers": len(invalid_driver_ids),
            "invalidDriverIds": invalid_driver_ids,
            "status": vapi_response["status"],
            "customers": vapi_response["customers"],
            "driverDetails": driver_details,  # Same info as single driver endpoint
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"❌ Error in batch VAPI calls: {str(error)}")

        # Handle different error types
        if "VAPI API Error" in str(error):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": str(error),
                    "status": "vapi_api_error",
                },
            )
        elif "Network error" in str(error):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": str(error),
                    "status": "network_error",
                },
            )
        elif "environment variable" in str(error):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "VAPI configuration error",
                    "status": "configuration_error",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(error),
                    "status": "batch_vapi_error",
                },
            )


@router_no_auth.get("/fetch-vapi-calls/driver/{driver_id}")
async def fetch_vapi_calls_by_driver_id(driver_id: str, save_to_db: bool = True):
    """
    Fetch calls from VAPI API for a driver and save complete data to database

    This endpoint:
    1. Gets driver phone number from driversdirectory table using driver_id
    2. Fetches all calls from VAPI API for that phone number
    3. Filters out calls with empty phone numbers
    4. Saves complete call data including transcript, duration, timestamps, pickup status
    5. Skips calls that already exist in database (checks by call_id)

    Query Parameters:
    - save_to_db: Whether to save calls to database (default: True)

    Returns:
    - Complete call data with transcript, summary, duration, timestamps
    - Stats: total calls found, new calls saved, existing calls skipped
    """
    try:
        # Get driver info to find phone number
        driver = Driver.get_by_id(driver_id)

        if not driver:
            raise HTTPException(
                status_code=404, detail=f"Driver not found with ID: {driver_id}"
            )

        if not driver.phoneNumber:
            raise HTTPException(
                status_code=400,
                detail=f"Driver {driver_id} has no phone number in database",
            )

        phone_number = driver.phoneNumber
        driver_name = (
            f"{driver.firstName or ''} {driver.lastName or ''}".strip()
            or "Unknown Driver"
        )

        # Use VAPI API key from environment
        vapi_api_key = settings.VAPI_V_API_KEY

        if not vapi_api_key:
            raise HTTPException(status_code=500, detail="VAPI API key not configured")

        logger.info(
            f"📞 Fetching VAPI calls for driver {driver_id} ({driver_name}) - Phone: {phone_number}"
        )

        # Normalize phone number
        normalized_phone = (
            phone_number.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        if not normalized_phone.startswith("+"):
            normalized_phone = f"+1{normalized_phone}"

        # Fetch all calls from VAPI API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vapi.ai/call",
                headers={
                    "Authorization": f"Bearer {vapi_api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code >= 400:
                logger.error(
                    f"❌ VAPI API Error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"VAPI API Error: {response.text}",
                )

            calls_data = response.json()

        logger.info(
            f"✅ Retrieved {len(calls_data) if isinstance(calls_data, list) else 'unknown'} total calls from VAPI"
        )

        # Import here to avoid circular imports
        from sqlmodel import Session, text
        from db import engine
        from datetime import datetime
        import uuid
        import json

        # Track stats
        new_calls_saved = 0
        existing_calls_skipped = 0
        empty_phone_skipped = 0
        formatted_calls = []

        if isinstance(calls_data, list):
            with Session(engine) as session:
                for call in calls_data:
                    call_phone = call.get("customer", {}).get("number", "")

                    # Skip calls with empty phone number
                    if not call_phone or call_phone.strip() == "":
                        empty_phone_skipped += 1
                        logger.debug(
                            f"⏭️ Skipping call with empty phone: {call.get('id')}"
                        )
                        continue

                    # Match phone number (with or without +1, spaces, etc.)
                    if (
                        normalized_phone in call_phone
                        or call_phone.replace(" ", "")
                        .replace("-", "")
                        .replace("(", "")
                        .replace(")", "")
                        in normalized_phone
                    ):
                        call_id = call.get("id")

                        # Determine if call was picked up
                        call_picked_up = False
                        transcript_messages = call.get("messages", [])
                        if transcript_messages:
                            # If there are user messages (not just system/bot), call was picked up
                            user_messages = [
                                m
                                for m in transcript_messages
                                if m.get("role") == "user"
                            ]
                            call_picked_up = len(user_messages) > 0

                        # Format call data with ALL available fields
                        formatted_call = {
                            "call_id": call_id,
                            "driver_id": driver_id,
                            "driver_name": driver_name,
                            "phone_number": call_phone,
                            "status": call.get(
                                "status"
                            ),  # ended, in-progress, queued, etc.
                            "call_picked_up": call_picked_up,
                            "transcript": transcript_messages,
                            "summary": call.get("summary"),
                            "recording_url": call.get("recordingUrl"),
                            "duration": call.get("duration"),  # in seconds
                            "started_at": call.get("startedAt"),
                            "ended_at": call.get("endedAt"),
                            "created_at": call.get("createdAt"),
                            "cost": call.get("cost"),
                            "ended_reason": call.get("endedReason"),
                        }
                        formatted_calls.append(formatted_call)

                        # Save to database if enabled
                        if save_to_db and call_id:
                            # Check if call already exists
                            result = session.execute(
                                text(
                                    "SELECT 1 FROM dev.driver_triggers_calls WHERE call_id = :call_id LIMIT 1"
                                ),
                                {"call_id": call_id},
                            ).fetchone()

                            if result:
                                existing_calls_skipped += 1
                                logger.debug(f"⏭️ Skipping existing call: {call_id}")
                            else:
                                # Insert new call with complete data
                                try:
                                    # Convert transcript to JSON string for storage
                                    transcript_json = (
                                        json.dumps(transcript_messages)
                                        if transcript_messages
                                        else "[]"
                                    )

                                    # Parse timestamps
                                    started_at_parsed = None
                                    ended_at_parsed = None

                                    if call.get("startedAt"):
                                        try:
                                            from dateutil import parser as date_parser

                                            started_at_parsed = date_parser.parse(
                                                call.get("startedAt")
                                            )
                                        except:
                                            started_at_parsed = None

                                    if call.get("endedAt"):
                                        try:
                                            from dateutil import parser as date_parser

                                            ended_at_parsed = date_parser.parse(
                                                call.get("endedAt")
                                            )
                                        except:
                                            ended_at_parsed = None

                                    logger.info(
                                        f"🔄 Inserting call {call_id} to database..."
                                    )

                                    session.execute(
                                        text(
                                            """
                                        INSERT INTO dev.driver_triggers_calls
                                        (id, driver_id, driver_name, call_summary, call_id, phone, call_duration,
                                         call_status, transcript, recording_url, started_at, ended_at,
                                         call_picked_up, ended_reason, created_at, updated_at)
                                        VALUES (:id, :driver_id, :driver_name, :call_summary, :call_id, :phone, :call_duration,
                                                :call_status, :transcript, :recording_url, :started_at, :ended_at,
                                                :call_picked_up, :ended_reason, :created_at, :updated_at)
                                        """
                                        ),
                                        {
                                            "id": str(uuid.uuid4()),
                                            "driver_id": driver_id,
                                            "driver_name": driver_name,
                                            "call_summary": call.get("summary"),
                                            "call_id": call_id,
                                            "phone": call_phone,
                                            "call_duration": call.get("duration"),
                                            "call_status": call.get("status"),
                                            "transcript": transcript_json,
                                            "recording_url": call.get("recordingUrl"),
                                            "started_at": started_at_parsed,
                                            "ended_at": ended_at_parsed,
                                            "call_picked_up": call_picked_up,
                                            "ended_reason": call.get("endedReason"),
                                            "created_at": datetime.utcnow(),
                                            "updated_at": datetime.utcnow(),
                                        },
                                    )
                                    new_calls_saved += 1
                                    logger.info(
                                        f"✅ Saved call to DB: {call_id} | Status: {call.get('status')} | Picked up: {call_picked_up}"
                                    )
                                except Exception as db_error:
                                    logger.error(
                                        f"❌ Error saving call {call_id}: {str(db_error)}"
                                    )
                                    import traceback

                                    logger.error(traceback.format_exc())
                                    # Continue with other calls even if one fails

                # Commit all inserts
                if save_to_db:
                    session.commit()
                    logger.info(
                        f"💾 Database save complete: {new_calls_saved} new, {existing_calls_skipped} skipped, {empty_phone_skipped} empty phones"
                    )

        return {
            "success": True,
            "driver_id": driver_id,
            "driver_name": driver_name,
            "phone_number": phone_number,
            "total_calls": len(formatted_calls),
            "new_calls_saved": new_calls_saved if save_to_db else 0,
            "existing_calls_skipped": existing_calls_skipped if save_to_db else 0,
            "empty_phone_skipped": empty_phone_skipped,
            "calls": formatted_calls,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching VAPI calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router_no_auth.post("/update-reports-insights")
async def update_driver_call_insights(update_data: DriverCallInsightsUpdate):
    """
    Update driver call insights from VAPI call results
    """
    logger.info("VAPI CALLING THIS CONTROLLER")

    try:
        logger.info(
            f"{update_data.driverId}, {update_data.tripId}, {update_data.currentLocation}, "
            f"{update_data.milesRemaining}, {update_data.eta}, {update_data.onTimeStatus}, "
            f"{update_data.delayReason}, {update_data.driverMood}, {update_data.preferredCallbackTime}, "
            f"{update_data.wantsTextInstead}, {update_data.recordingUrl}"
        )

        # Find driver morning report by tripId
        with DriverMorningReport.get_session() as session:
            from sqlmodel import select

            statement = select(DriverMorningReport).where(
                DriverMorningReport.tripId == update_data.tripId
            )
            driver_report = session.exec(statement).first()

            logger.info(f"REPORT => {driver_report}")

            if not driver_report:
                raise HTTPException(
                    status_code=400,
                    detail={"success": False, "message": "No Report Found"},
                )

            if update_data.eta is not None:
                driver_report.driverETAfeedback = update_data.eta
            if update_data.onTimeStatus is not None:
                driver_report.onTime = update_data.onTimeStatus
            if update_data.delayReason is not None:
                driver_report.delayReason = update_data.delayReason
            if update_data.driverMood is not None:
                driver_report.driverFeeling = update_data.driverMood
            if update_data.callSummary is not None:
                driver_report.ETA_Notes_1 = update_data.callSummary
            driver_report.callStatus = 1
            # Note: preferredCallbackTime, wantsTextInstead, recordingUrl fields
            # are not in the current DriverMorningReport model

            session.add(driver_report)
            session.commit()

        return {
            "success": True,
            "message": "Driver report updated successfully.",
            "data": {
                "driverId": update_data.driverId,
                "currentLocation": update_data.currentLocation,
                "milesRemaining": update_data.milesRemaining,
                "eta": update_data.eta,
                "onTimeStatus": update_data.onTimeStatus,
                "delayReason": update_data.delayReason,
                "driverMood": update_data.driverMood,
                "preferredCallbackTime": update_data.preferredCallbackTime,
                "wantsTextInstead": update_data.wantsTextInstead,
                "recordingUrl": update_data.recordingUrl,
                "callSummary": update_data.callSummary,
            },
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error updating driver call insights: {str(error)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "Internal server error.",
                "error": str(error),
            },
        )


# IBRAR CODE
