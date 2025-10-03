from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from utils.vapi_client import vapi_client
from models.vapi import BatchCallRequest
from config import settings
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# -------------------------------
# DriverTripData MODEL
# -------------------------------
class DriverTripData(SQLModel, table=True):
    __tablename__ = "trips"
    __table_args__ = {"extend_existing": True}

    tripId: str = Field(primary_key=True, max_length=50)
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    fuelPercent: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["DriverTripData"]:
        """Fetch all trips"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_driver(cls, driver_id: str) -> Optional["DriverTripData"]:
        with cls.get_session() as session:
            stmt = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(stmt).first()

    @classmethod
    def get_by_trip(cls, trip_id: str) -> Optional["DriverTripData"]:
        with cls.get_session() as session:
            stmt = select(cls).where(cls.tripId == trip_id).limit(1)
            return session.exec(stmt).first()


# -------------------------------
# ActiveLoadTracking MODEL
# -------------------------------
class ActiveLoadTracking(SQLModel, table=True):
    __tablename__ = "active_load_tracking"
    __table_args__ = {"extend_existing": True}

    load_id: str = Field(primary_key=True, max_length=50)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    miles_threshold: Optional[int] = Field(default=250)
    driver_name: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default="EnRouteToDelivery", max_length=50)
    driver_phone_number: Optional[str] = Field(default=None, max_length=50)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["ActiveLoadTracking"]:
        """Fetch all active load tracking rows"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_trip(cls, trip_id: str) -> Optional["ActiveLoadTracking"]:
        """Fetch active load by tripId"""
        with cls.get_session() as session:
            return session.exec(select(cls).where(cls.trip_id == trip_id)).first()


# -------------------------------
# VIOLATION ALERTS MODEL
# -------------------------------
class ViolationAlertDriver(SQLModel, table=True):
    __tablename__ = "violation_alerts"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True, max_length=50)
    load_id: Optional[str] = Field(default=None, max_length=50)
    violation_time: Optional[str] = Field(default=250)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 5000) -> List["ViolationAlertDriver"]:
        """Fetch all vilation alerts"""
        with cls.get_session() as session:
            return session.exec(select(cls).limit(limit)).all()

    @classmethod
    def get_by_trip_id(cls, trip_id: str) -> Optional["ViolationAlertDriver"]:
        """Fetch violation by id"""
        with cls.get_session() as session:
            return session.exec(select(cls).where(cls.load_id == trip_id)).first()


# -----------------------------
# Combined logic
# -----------------------------
REQUIRED_FUEL = 50  # %


def get_driver_summary(driver_id: str) -> Dict:
    """
    Fetch trip + active load + violation alert data for a driver.
    Adds checks for fuel %, temperature, route status, miles_threshold, and violation_time.
    """
    try:
        driver_trip = DriverTripData.get_by_driver(driver_id)
        active_load = None
        violation_alert = None

        if driver_trip and driver_trip.tripId:
            active_load = ActiveLoadTracking.get_by_trip(driver_trip.tripId)
            violation_alert = ViolationAlertDriver.get_by_trip_id(driver_trip.tripId)

        # --- Fuel percent logic ---
        fuel_percent = (
            getattr(driver_trip, "fuelPercent", None) if driver_trip else None
        )
        if fuel_percent is not None:
            if fuel_percent < REQUIRED_FUEL:
                fuel_percent = f"{fuel_percent}% (Below required {REQUIRED_FUEL}%)"
            elif fuel_percent > REQUIRED_FUEL:
                fuel_percent = f"{fuel_percent}% (Above required {REQUIRED_FUEL}%)"
            else:
                fuel_percent = f"{fuel_percent}% (At required {REQUIRED_FUEL}%)"

        # --- Temperature logic ---
        driver_temp_message = None
        set_point = getattr(driver_trip, "ditatSetPoint", None) if driver_trip else None
        current_temp = getattr(driver_trip, "tempC", None) if driver_trip else None

        if set_point is not None and current_temp is not None:
            if current_temp > set_point:
                driver_temp_message = f"{current_temp}°C (Above required {set_point}°C)"
            elif current_temp < set_point:
                driver_temp_message = f"{current_temp}°C (Below required {set_point}°C)"
            else:
                driver_temp_message = f"{current_temp}°C (At required temperature)"
        elif current_temp is not None:
            driver_temp_message = f"{current_temp}°C (No set point available)"
        elif set_point is not None:
            driver_temp_message = f"Required {set_point}°C (No current temp available)"

        # --- Route Status Logic ---
        out_of_route = getattr(driver_trip, "outOfRoute", None) if driver_trip else None
        trl_check = getattr(driver_trip, "trlCheck", None) if driver_trip else None
        sub_status = (
            getattr(driver_trip, "subStatusLabel", None) if driver_trip else None
        )

        route_status = None
        if (
            out_of_route == "🟢"
            and trl_check == "🟢"
            and sub_status == "En Route to Delivery"
        ):
            route_status = "Driver is on route"
        else:
            route_status = "Driver is out of route"

        # --- Build response ---
        response_data = {
            "driverId": driver_id,
            "fuelPercent": fuel_percent,
            "driver_temp": driver_temp_message,
            "routeStatus": route_status,
            "tripId": getattr(driver_trip, "tripId", None) if driver_trip else None,
            "onTimeStatus": (
                getattr(driver_trip, "onTimeStatus", None) if driver_trip else None
            ),
            "trlCheck": getattr(driver_trip, "trlCheck", None) if driver_trip else None,
            "timeDifference": (
                getattr(driver_trip, "etaTimeDifference", None) if driver_trip else None
            ),
            "miles_threshold": (
                getattr(active_load, "miles_threshold", None) if active_load else None
            ),
            "driver_name": (
                getattr(active_load, "driver_name", None) if active_load else None
            ),
            "phoneNumber": (
                getattr(active_load, "driver_phone_number", None)
                if active_load
                else None
            ),
            "violation_time": (
                getattr(violation_alert, "violation_time", None)
                if violation_alert
                else None
            ),
        }

        return {
            "message": "Driver trip and active load data fetched successfully",
            "data": response_data,
        }

    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error fetching driver summary: {err}", exc_info=True)
        return {
            "message": "Error fetching driver summary",
            "error": str(err),
            "trace": error_details,  # ⚠️ remove this in production
        }


# -------------------------------
# MAKE VAPI MULTIPLE CALLS - BATCH CALL
# -------------------------------
async def make_drivers_violation_batch_call(request: BatchCallRequest):
    try:
        logger.info(f"📞 Processing batch VAPI calls for data : {request}")

        # Example: convert payload to VAPI batch call format
        vapi_payload = {
            "name": "Driver Violations Batch Call",  # ✅ required
            "assistantId": settings.VAPI_ASSISTANT_ID,
            "phoneNumberId": getattr(settings, "VAPI_PHONENUMBER_ID", ""),
            "customers": [],
        }

        # Transform Payload
        for driver in request.drivers:
            vapi_payload["customers"].append(
                {
                    "number": "+12025550100",  # TODO: normalize to +E.164 driver.phoneNumber
                    "name": driver.driverName,
                    "assistantOverrides": {
                        "context": {
                            "driverId": driver.driverId,
                            "driverName": driver.driverName,
                            "tripId": driver.violations.tripId,
                            "violations": [
                                {
                                    "type": v.type,
                                    "description": v.description,
                                    # "severity": v.severity,
                                }
                                for v in driver.violations.violationDetails
                            ],
                        }
                    },
                }
            )

        # Make API call to VAPI campaign endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.vapi.ai/campaign",
                json=vapi_payload,
                headers={
                    "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        if response.status_code != 200:
            logger.error(f"❌ VAPI API Error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"VAPI API Error: {response.text}",
            )
        logger.info("✅ Batch call sent successfully")
        return {
            "message": "Batch call payload generated successfully",
            "vapi_payload": vapi_payload,
            "vapi_response": response.json(),
        }
    except Exception as err:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"Error sending batch call: {err}", exc_info=True)
        return {
            "message": "Error sending batch call",
            "error": str(err),
            "trace": error_details,  # ⚠️ remove this in production
        }
