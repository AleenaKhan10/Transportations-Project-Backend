from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.drivers import Driver
from models.driver_reports import DriverReport
from models.vapi import VAPICallRequest, DriverCallInsightsUpdate
from utils.vapi_client import vapi_client


router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])




@router.post("/vapi-call/{driver_id}")
async def make_vapi_call(driver_id: str):
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
                }
            )

        # Retrieve driver information
        driver = Driver.get_by_id(driver_id)

        if not driver:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Driver not found",
                    "status": "driver_not_found",
                }
            )

        # Validate driver has phone number
        if not driver.phoneNumber:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Driver phone number is required for VAPI call",
                    "status": "missing_phone_number",
                }
            )

        logger.info(f"📞 Initiating VAPI call to driver: {driver.firstName} {driver.lastName} ({driver_id})")

        # Convert driver to dict for VAPI client
        driver_dict = driver.model_dump()

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
                }
            )
        elif "Network error" in str(error):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": str(error),
                    "status": "network_error",
                }
            )
        elif "environment variable" in str(error):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "VAPI configuration error",
                    "status": "configuration_error",
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(error),
                    "status": "internal_error",
                }
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
                }
            )

        logger.info(f"📞 Processing batch VAPI calls for {len(driver_ids)} driver(s): {', '.join(driver_ids)}")

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
                }
            )

        # Validate all valid drivers have phone numbers
        drivers_without_phone = [driver for driver in valid_drivers if not driver.phoneNumber]
        if drivers_without_phone:
            drivers_without_phone_ids = [d.driverId for d in drivers_without_phone]
            logger.warning(f"⚠️ Drivers without phone numbers: {', '.join(drivers_without_phone_ids)}")

            # Filter out drivers without phone numbers
            drivers_with_phone = [driver for driver in valid_drivers if driver.phoneNumber]

            if not drivers_with_phone:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "No drivers with valid phone numbers found",
                        "status": "no_valid_phone_numbers",
                        "invalidDriverIds": invalid_driver_ids + drivers_without_phone_ids,
                    }
                )

            # Update arrays to reflect phone number filtering
            valid_drivers = drivers_with_phone
            invalid_driver_ids.extend(drivers_without_phone_ids)

        logger.info(f"✅ Found {len(valid_drivers)} valid driver(s) for VAPI campaign")
        for driver in valid_drivers:
            logger.info(f"   • {driver.firstName} {driver.lastName} ({driver.driverId}) - {driver.phoneNumber}")

        # Convert drivers to dicts for VAPI client
        driver_dicts = [driver.model_dump() for driver in valid_drivers]

        # Use VAPI client with multiple drivers (single campaign)
        vapi_response = await vapi_client.create_vapi_call(driver_dicts)

        # Return comprehensive response
        return {
            "success": True,
            "campaignId": vapi_response["campaignId"],
            "totalDrivers": len(driver_ids),
            "validDrivers": len(valid_drivers),
            "invalidDrivers": len(invalid_driver_ids),
            "invalidDriverIds": invalid_driver_ids,
            "status": vapi_response["status"],
            "customers": vapi_response["customers"],
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
                }
            )
        elif "Network error" in str(error):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": str(error),
                    "status": "network_error",
                }
            )
        elif "environment variable" in str(error):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "VAPI configuration error",
                    "status": "configuration_error",
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(error),
                    "status": "batch_vapi_error",
                }
            )


@router.post("/update-reports-insights")
async def update_driver_call_insights(update_data: DriverCallInsightsUpdate):
    """
    Update driver call insights from VAPI call results
    """
    try:
        driver_id = update_data.driverId
        
        logger.info(f"Updating call insights for driver: {driver_id}")

        # Find driver report
        with DriverReport.get_session() as session:
            from sqlmodel import select
            statement = select(DriverReport).where(DriverReport.driverIdPrimary == driver_id)
            driver_report = session.exec(statement).first()

            if not driver_report:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "message": "No Report Found"
                    }
                )

            # Update report fields
            if update_data.currentLocation is not None:
                driver_report.currentLocation = update_data.currentLocation
            if update_data.milesRemaining is not None:
                driver_report.milesRemaining = update_data.milesRemaining
            if update_data.eta is not None:
                driver_report.eta = update_data.eta
            if update_data.onTimeStatus is not None:
                driver_report.onTimeStatus = update_data.onTimeStatus
            if update_data.delayReason is not None:
                driver_report.delayReason = update_data.delayReason
            if update_data.driverMood is not None:
                driver_report.driverFeeling = update_data.driverMood
            if update_data.preferredCallbackTime is not None:
                # Note: this field might need to be added to the model
                pass
            if update_data.wantsTextInstead is not None:
                # Note: this field might need to be added to the model
                pass
            if update_data.issueReported is not None:
                # Note: this field might need to be added to the model
                pass

            session.add(driver_report)
            session.commit()

        return {
            "success": True,
            "message": "Driver report updated successfully.",
            "data": {
                "driverId": driver_id,
                "currentLocation": update_data.currentLocation,
                "milesRemaining": update_data.milesRemaining,
                "eta": update_data.eta,
                "onTimeStatus": update_data.onTimeStatus,
                "delayReason": update_data.delayReason,
                "driverMood": update_data.driverMood,
                "preferredCallbackTime": update_data.preferredCallbackTime,
                "wantsTextInstead": update_data.wantsTextInstead,
                "issueReported": update_data.issueReported,
                "recordingUrl": update_data.recordingUrl,
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
            }
        )