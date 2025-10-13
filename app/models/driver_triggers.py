from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# -------------------------------
# ActiveLoadTracking MODEL
# -------------------------------
class ActiveLoadTracking(SQLModel, table=True):
    __tablename__ = "active_load_tracking"
    __table_args__ = {"extend_existing": True}

    load_id: str = Field(primary_key=True, max_length=50)
    trip_id: Optional[str] = Field(default=None, max_length=50)
    miles_threshold: Optional[int] = Field(default=250)  # 200


# -------------------------------
# DriverTripData MODEL
# -------------------------------
class DriverTriggersData(SQLModel, table=True):
    __tablename__ = "trips"
    __table_args__ = {"extend_existing": True}

    tripId: str = Field(primary_key=True, max_length=50)
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    fuelPercent: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)  # 🟢 / 🔴
    tempC: Optional[float] = None  # set point
    tempF: Optional[float] = None  # current temp
    trlCheck: Optional[str] = Field(max_length=10, default=None)  # 🟢 / 🔴
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)  # 🟢 / 🔴

    # ---------------------------------------------------------------------
    # DB Session
    # ---------------------------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # Fetch trip by driver_id
    # ---------------------------------------------------------------------
    @classmethod
    def get_trip_by_driver_id(cls, driver_id: str) -> Optional["DriverTriggersData"]:
        with cls.get_session() as session:
            statement = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(statement).first()

    # ---------------------------------------------------------------------
    # Helper: fetch active load tracking for a trip
    # ---------------------------------------------------------------------
    @staticmethod
    def get_active_load_by_trip(trip_id: str) -> Optional[ActiveLoadTracking]:
        with Session(engine) as session:
            statement = (
                select(ActiveLoadTracking)
                .where(ActiveLoadTracking.trip_id == trip_id)
                .limit(1)
            )
            return session.exec(statement).first()

    # ---------------------------------------------------------------------
    # Core logic: compare violations & return messages
    # ---------------------------------------------------------------------
    @classmethod
    def get_driver_trigger(cls, payload: Dict) -> Dict[str, List[str]]:
        try:
            driver_id = payload["driver"]["driverId"]
            trip = cls.get_trip_by_driver_id(driver_id)

            if not trip:
                raise HTTPException(status_code=404, detail="Driver trip not found")

            selected_violations = payload.get("selectedViolations", [])
            messages = []

            # --- Violation ID Mappings ---
            # 1 = Temperature check
            # 2 = Stopping within 200 miles (not implemented — placeholder)
            # 4 = Out of route
            # 5 = Trailer check
            # 6 = Fuel check

            for v in selected_violations:
                v_id = v["id"]
                v_msg = v["message"]

                # 1️⃣ Temperature violation
                if v_id == 1:
                    if trip.tempC is not None and trip.tempF is not None:
                        if trip.tempF < trip.tempC:
                            messages.append(
                                f"Temperature is low — current {trip.tempF}°C, set point {trip.tempC}°C."
                            )
                        elif trip.tempF > trip.tempC:
                            messages.append(
                                f"Temperature is high — current {trip.tempF}°C, set point {trip.tempC}°C."
                            )
                        else:
                            messages.append("Temperature is equal to the set point.")
                    else:
                        messages.append("Temperature data not available for this trip.")

                # 2️⃣ Driver stopping early (uses ActiveLoadTracking)
                elif v_id == 2:
                    active_load = cls.get_active_load_by_trip(trip.tripId)
                    if active_load:
                        threshold = active_load.miles_threshold or 0
                        if threshold <= 200:
                            messages.append(
                                f"Driver stopped early — only {threshold} miles completed before stop (limit is 200 miles)."
                            )
                        # Skip if >200 (no violation)
                    else:
                        messages.append(
                            "Active load tracking data not found for this trip."
                        )

                # 4️⃣ Out-of-route
                elif v_id == 4:
                    if trip.outOfRoute == "🔴":
                        messages.append("Driver is out of route.")
                    # else:
                    #     messages.append("Driver is on the correct route.")

                # 5️⃣ Trailer check
                elif v_id == 5:
                    if trip.trlCheck == "🔴":
                        messages.append(
                            "Trailer check failed — please inspect trailer status."
                        )
                    # else:
                    #     messages.append("Trailer check passed successfully.")

                # 6️⃣ Fuel check
                elif v_id == 6:
                    SET_FUEL = 50
                    if trip.fuelPercent is not None:
                        if trip.fuelPercent < SET_FUEL:
                            messages.append(
                                f"Fuel is low — current {trip.fuelPercent}%, required at least {SET_FUEL}%."
                            )
                        # else:
                        #     messages.append(
                        #         f"Fuel is sufficient — current {trip.fuelPercent}%."
                        #     )
                    else:
                        messages.append("Fuel data not available for this trip.")

                else:
                    messages.append(f"Unknown violation: {v_msg}")

            # ✅ Default if no messages
            if not messages:
                messages.append("No active violations detected.")

            # -----------------------------------------------------------------
            # 🧠 Build Dynamic VAPI System Prompt
            # -----------------------------------------------------------------
            driver_name = payload["driver"].get("name", "Unknown Driver")

            VapiSystemPrompt = (
                f"You are a friendly fleet assistant calling {driver_name} to discuss their recent trip performance.\n"
                f"Use a polite, professional, and encouraging tone.\n\n"
                f"Here’s the summary of detected issues:\n"
                + "\n".join(f"- {msg}" for msg in messages)
                + "\n\nProvide brief feedback for each issue, help the driver understand what went wrong, "
                "and give suggestions to improve. End the conversation with a positive note."
            )

            return {
                "driverId": driver_id,
                "driverName": payload["driver"]["name"],
                "phoneNumber": payload["driver"]["phone"],
                "messages": messages,
                "VapiSystemPrompt": VapiSystemPrompt,
            }

        except KeyError as e:
            raise HTTPException(
                status_code=400, detail=f"Missing key in payload: {str(e)}"
            )
        except Exception as e:
            logger.exception("Error while processing driver trigger")
            raise HTTPException(status_code=500, detail=str(e))
